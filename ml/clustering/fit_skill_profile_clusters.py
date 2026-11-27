from __future__ import annotations

import argparse
import json
import random
import sqlite3
from pathlib import Path

import numpy as numerical
import scipy
import sklearn
from scipy.sparse import csr_matrix
from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = PROJECT_ROOT_DIRECTORY / "data" / "processed" / "job_market.sqlite3"
DEFAULT_OUTPUT_DIRECTORY = PROJECT_ROOT_DIRECTORY / "ml" / "evaluation" / "results"
EXPECTED_ARCHIVE_RUN_ID = "full_archive_parquet_v1_20261028"
RANDOM_SEED = 20261028
SAMPLE_SIZE = 12000
HOLDOUT_FRACTION = 0.2
SILHOUETTE_SAMPLE_SIZE = 1000
CLUSTER_CANDIDATES = (4, 6, 8, 10)


def open_read_only_database(database_path: Path) -> sqlite3.Connection:
    database_uri = f"{database_path.resolve().as_uri()}?mode=ro"
    return sqlite3.connect(database_uri, uri=True)


def select_reservoir_sampled_job_ids(
    database_connection: sqlite3.Connection,
    sample_size: int,
    random_seed: int,
) -> tuple[list[str], int]:
    job_identifier_query = """
        SELECT DISTINCT job_skills.record_id
        FROM job_skills
        JOIN jobs ON jobs.record_id = job_skills.record_id
        JOIN skills ON skills.skill_id = job_skills.skill_id
        WHERE jobs.source_dataset = 'international_jobs'
          AND jobs.exact_duplicate_within_source = 'no'
          AND job_skills.skill_match_policy = skills.match_policy
          AND job_skills.skill_review_status = skills.review_status
          AND (
              (job_skills.skill_match_policy = 'approved_aliases' AND job_skills.skill_review_status = 'curated')
              OR (job_skills.skill_match_policy = 'exact_only' AND job_skills.skill_review_status = 'curated_exact_only')
          )
        ORDER BY job_skills.record_id
    """
    random_generator = random.Random(random_seed)
    sampled_job_identifiers = []
    eligible_job_count = 0
    for eligible_job_count, row in enumerate(database_connection.execute(job_identifier_query), start=1):
        job_identifier = row[0]
        if len(sampled_job_identifiers) < sample_size:
            sampled_job_identifiers.append(job_identifier)
        else:
            replacement_index = random_generator.randrange(eligible_job_count)
            if replacement_index < sample_size:
                sampled_job_identifiers[replacement_index] = job_identifier
    if eligible_job_count < sample_size:
        raise ValueError(
            f"Requested {sample_size:,} jobs but only {eligible_job_count:,} eligible records were found."
        )
    return sampled_job_identifiers, eligible_job_count


def load_sampled_job_skills(
    database_connection: sqlite3.Connection,
    sampled_job_identifiers: list[str],
) -> tuple[list[str], csr_matrix, dict[str, str]]:
    sampled_skill_sets = {job_identifier: set() for job_identifier in sampled_job_identifiers}
    for batch_start in range(0, len(sampled_job_identifiers), 400):
        job_identifier_batch = sampled_job_identifiers[batch_start : batch_start + 400]
        placeholders = ",".join("?" for _ in job_identifier_batch)
        skill_link_query = f"""
            SELECT job_skills.record_id, job_skills.skill_id
            FROM job_skills
            JOIN skills ON skills.skill_id = job_skills.skill_id
            WHERE job_skills.record_id IN ({placeholders})
              AND job_skills.skill_match_policy = skills.match_policy
              AND job_skills.skill_review_status = skills.review_status
              AND (
                  (job_skills.skill_match_policy = 'approved_aliases' AND job_skills.skill_review_status = 'curated')
                  OR (job_skills.skill_match_policy = 'exact_only' AND job_skills.skill_review_status = 'curated_exact_only')
              )
            ORDER BY job_skills.record_id, job_skills.skill_id
        """
        for job_identifier, skill_identifier in database_connection.execute(
            skill_link_query,
            job_identifier_batch,
        ):
            sampled_skill_sets[job_identifier].add(skill_identifier)

    skill_identifiers = sorted(
        {
            skill_identifier
            for job_skill_set in sampled_skill_sets.values()
            for skill_identifier in job_skill_set
        }
    )
    skill_identifier_positions = {
        skill_identifier: column_index
        for column_index, skill_identifier in enumerate(skill_identifiers)
    }
    sampled_job_positions = {
        job_identifier: row_index
        for row_index, job_identifier in enumerate(sampled_job_identifiers)
    }
    matrix_row_indices = []
    matrix_column_indices = []
    for job_identifier, job_skill_set in sampled_skill_sets.items():
        for skill_identifier in sorted(job_skill_set):
            matrix_row_indices.append(sampled_job_positions[job_identifier])
            matrix_column_indices.append(skill_identifier_positions[skill_identifier])
    job_skill_matrix = csr_matrix(
        (
            numerical.ones(len(matrix_row_indices), dtype=numerical.float32),
            (matrix_row_indices, matrix_column_indices),
        ),
        shape=(len(sampled_job_identifiers), len(skill_identifiers)),
        dtype=numerical.float32,
    )
    skill_name_rows = database_connection.execute(
        "SELECT skill_id, canonical_name FROM skills"
    ).fetchall()
    skill_names_by_identifier = {
        skill_identifier: canonical_name
        for skill_identifier, canonical_name in skill_name_rows
    }
    return skill_identifiers, job_skill_matrix, skill_names_by_identifier


def measure_cluster_silhouette(
    feature_matrix: csr_matrix,
    cluster_labels: numerical.ndarray,
    random_seed: int,
) -> float | None:
    distinct_cluster_count = len(numerical.unique(cluster_labels))
    if distinct_cluster_count < 2 or distinct_cluster_count >= feature_matrix.shape[0]:
        return None
    return float(
        silhouette_score(
            feature_matrix,
            cluster_labels,
            metric="cosine",
            sample_size=min(SILHOUETTE_SAMPLE_SIZE, feature_matrix.shape[0]),
            random_state=random_seed,
        )
    )


def evaluate_cluster_candidates(
    training_features: csr_matrix,
    holdout_features: csr_matrix,
    random_seed: int,
) -> list[dict[str, object]]:
    candidate_results = []
    random_generator = numerical.random.default_rng(random_seed)
    for cluster_count in CLUSTER_CANDIDATES:
        cluster_model = MiniBatchKMeans(
            n_clusters=cluster_count,
            random_state=random_seed,
            batch_size=512,
            n_init=5,
            max_iter=100,
            reassignment_ratio=0.01,
        )
        cluster_model.fit(training_features)
        holdout_cluster_labels = cluster_model.predict(holdout_features)
        silhouette = measure_cluster_silhouette(
            holdout_features,
            holdout_cluster_labels,
            random_seed,
        )
        randomized_cluster_labels = random_generator.permutation(holdout_cluster_labels)
        random_silhouette = measure_cluster_silhouette(
            holdout_features,
            randomized_cluster_labels,
            random_seed,
        )
        holdout_cluster_sizes = numerical.bincount(
            holdout_cluster_labels,
            minlength=cluster_count,
        )
        candidate_results.append(
            {
                "cluster_count": cluster_count,
                "training_inertia": float(cluster_model.inertia_),
                "holdout_silhouette_cosine": silhouette,
                "random_label_baseline_silhouette_cosine": random_silhouette,
                "holdout_cluster_sizes": [int(size) for size in holdout_cluster_sizes],
                "holdout_cluster_size_percentages": [
                    round(100.0 * float(size) / len(holdout_cluster_labels), 2)
                    for size in holdout_cluster_sizes
                ],
            }
        )
    return candidate_results


def build_cluster_profiles(
    holdout_features: csr_matrix,
    holdout_cluster_labels: numerical.ndarray,
    skill_identifiers: list[str],
    skill_names_by_identifier: dict[str, str],
) -> list[dict[str, object]]:
    cluster_profiles = []
    for cluster_identifier in sorted(int(value) for value in numerical.unique(holdout_cluster_labels)):
        cluster_mask = holdout_cluster_labels == cluster_identifier
        cluster_size = int(cluster_mask.sum())
        cluster_skill_counts = numerical.asarray(
            holdout_features[cluster_mask].sum(axis=0)
        ).ravel()
        top_skill_positions = numerical.argsort(cluster_skill_counts)[::-1][:8]
        top_skills = []
        for skill_position in top_skill_positions:
            job_count = int(cluster_skill_counts[skill_position])
            if job_count == 0:
                continue
            skill_identifier = skill_identifiers[int(skill_position)]
            top_skills.append(
                {
                    "skill_id": skill_identifier,
                    "skill_name": skill_names_by_identifier.get(skill_identifier, skill_identifier),
                    "job_count": job_count,
                    "within_cluster_share_percent": round(100.0 * job_count / cluster_size, 2),
                }
            )
        cluster_profiles.append(
            {
                "cluster_id": cluster_identifier,
                "holdout_job_count": cluster_size,
                "holdout_job_share_percent": round(
                    100.0 * cluster_size / len(holdout_cluster_labels),
                    2,
                ),
                "top_skills": top_skills,
            }
        )
    return cluster_profiles


def render_evaluation_report(evaluation: dict[str, object]) -> str:
    model_rows = evaluation["candidate_models"]
    report_lines = [
        "# Skill-Profile Clustering Evaluation",
        "",
        f"**Archive:** `{evaluation['source_archive_run_id']}`  ",
        f"**Source cohort:** `{evaluation['source_dataset']}`; historical 2023 International-source records  ",
        f"**Feature representation:** binary presence of each reviewed canonical skill ID; include only `(approved_aliases, curated)` and `(exact_only, curated_exact_only)` pairs; exact-duplicate rows omitted  ",
        f"**Sample:** {evaluation['sample']['eligible_population']:,} eligible source records; simple random reservoir sample of {evaluation['sample']['sample_size']:,}; {evaluation['sample']['training_size']:,} train and {evaluation['sample']['holdout_size']:,} holdout rows  ",
        f"**Random seed:** {evaluation['sample']['random_seed']}  ",
        "**Serving decision:** report-only experiment; no serialized model and no user-facing occupational labels.",
        "",
        "## Evaluation method",
        "",
        "The experiment compares MiniBatchKMeans solutions with 4, 6, 8, and 10 clusters. It fits the binary skill matrix on 80% of a deterministic random sample and predicts labels for the held-out 20%. Intrinsic separation is measured using cosine silhouette on a fixed-size holdout subsample; a shuffled-label result is shown as a weak random baseline. A second fit of the selected cluster count is compared using adjusted Rand index. These metrics do not establish that clusters are real job families, useful recommendations, or representative of a labor market.",
        "",
        "## Candidate results",
        "",
        "| Clusters | Train inertia | Holdout cosine silhouette | Shuffled-label silhouette | Holdout cluster sizes |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for model_result in model_rows:
        report_lines.append(
            "| {cluster_count} | {training_inertia:.2f} | {holdout_silhouette_cosine:.4f} | {random_label_baseline_silhouette_cosine:.4f} | {holdout_cluster_sizes} |".format(
                cluster_count=model_result["cluster_count"],
                training_inertia=model_result["training_inertia"],
                holdout_silhouette_cosine=model_result["holdout_silhouette_cosine"],
                random_label_baseline_silhouette_cosine=model_result["random_label_baseline_silhouette_cosine"],
                holdout_cluster_sizes=model_result["holdout_cluster_sizes"],
            )
        )
    best_model = evaluation["selected_candidate"]
    report_lines.extend(
        [
            "",
            f"Best candidate by the measured holdout silhouette is **k = {best_model['cluster_count']}** with cosine silhouette **{best_model['holdout_silhouette_cosine']:.4f}**. The two-seed adjusted Rand stability score for that solution is **{evaluation['stability_adjusted_rand_index']:.4f}**.",
            "",
            "## Holdout cluster profiles",
            "",
            "Cluster IDs are arbitrary. The skill lists are descriptive terms with the highest within-cluster frequency; they are not curated titles or hiring requirements.",
            "",
        ]
    )
    for cluster_profile in evaluation["selected_cluster_profiles"]:
        top_skill_summary = ", ".join(
            f"{skill['skill_name']} ({skill['within_cluster_share_percent']:.1f}%)"
            for skill in cluster_profile["top_skills"]
        )
        report_lines.extend(
            [
                f"### Cluster {cluster_profile['cluster_id']}",
                "",
                f"Holdout records: {cluster_profile['holdout_job_count']:,} ({cluster_profile['holdout_job_share_percent']:.1f}%). Most frequent eligible skills: {top_skill_summary}.",
                "",
            ]
        )
    report_lines.extend(
        [
            "## Limitations and decision",
            "",
            "This is an unsupervised, intrinsic evaluation on sampled International-source 2023 job records. Skill extraction and enrichment provenance are imperfect, duplicated advertisements may remain across sources, and the chosen source has no descriptions. A high silhouette does not validate an occupation taxonomy. Human review, source-balanced robustness checks, cluster stability, and a clear product use case are required before considering any cluster output for an application. Salary prediction and supervised classification remain no-go under the current data profile.",
            "",
        ]
    )
    return "\n".join(report_lines)


def main() -> int:
    argument_parser = argparse.ArgumentParser(
        description="Evaluate exploratory clusters of job-ad skill profiles from local SQLite."
    )
    argument_parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    argument_parser.add_argument("--output-directory", type=Path, default=DEFAULT_OUTPUT_DIRECTORY)
    parsed_arguments = argument_parser.parse_args()
    database_path = parsed_arguments.database.resolve()
    output_directory = parsed_arguments.output_directory.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    random_generator = numerical.random.default_rng(RANDOM_SEED)

    with open_read_only_database(database_path) as database_connection:
        successful_imports = database_connection.execute(
            "SELECT source_archive_run_id FROM import_runs WHERE run_status = 'succeeded' ORDER BY import_run_id DESC LIMIT 1"
        ).fetchone()
        if successful_imports is None or successful_imports[0] != EXPECTED_ARCHIVE_RUN_ID:
            raise RuntimeError("The local SQLite database does not contain the expected full archive.")
        sampled_job_identifiers, eligible_population_size = select_reservoir_sampled_job_ids(
            database_connection,
            SAMPLE_SIZE,
            RANDOM_SEED,
        )
        skill_identifiers, all_job_features, skill_names_by_identifier = load_sampled_job_skills(
            database_connection,
            sampled_job_identifiers,
        )

    randomized_row_order = random_generator.permutation(all_job_features.shape[0])
    holdout_size = int(round(all_job_features.shape[0] * HOLDOUT_FRACTION))
    training_row_indices = randomized_row_order[holdout_size:]
    holdout_row_indices = randomized_row_order[:holdout_size]
    training_features = all_job_features[training_row_indices]
    holdout_features = all_job_features[holdout_row_indices]
    candidate_results = evaluate_cluster_candidates(
        training_features,
        holdout_features,
        RANDOM_SEED,
    )
    selected_candidate = max(
        candidate_results,
        key=lambda model_result: model_result["holdout_silhouette_cosine"],
    )
    selected_cluster_count = int(selected_candidate["cluster_count"])
    selected_model = MiniBatchKMeans(
        n_clusters=selected_cluster_count,
        random_state=RANDOM_SEED,
        batch_size=512,
        n_init=5,
        max_iter=100,
        reassignment_ratio=0.01,
    )
    selected_model.fit(training_features)
    holdout_cluster_labels = selected_model.predict(holdout_features)
    repeated_seed_model = MiniBatchKMeans(
        n_clusters=selected_cluster_count,
        random_state=RANDOM_SEED + 1,
        batch_size=512,
        n_init=5,
        max_iter=100,
        reassignment_ratio=0.01,
    )
    repeated_seed_model.fit(training_features)
    repeated_seed_holdout_labels = repeated_seed_model.predict(holdout_features)
    stability_adjusted_rand_index = float(
        adjusted_rand_score(holdout_cluster_labels, repeated_seed_holdout_labels)
    )
    selected_cluster_profiles = build_cluster_profiles(
        holdout_features,
        holdout_cluster_labels,
        skill_identifiers,
        skill_names_by_identifier,
    )
    evaluation = {
        "source_archive_run_id": EXPECTED_ARCHIVE_RUN_ID,
        "source_dataset": "international_jobs",
        "feature_representation": "binary_presence_of_skill_id",
        "included_skill_policies": ["approved_aliases", "exact_only"],
        "included_skill_policy_status_pairs": [
            ["approved_aliases", "curated"],
            ["exact_only", "curated_exact_only"],
        ],
        "excluded_unreviewed_exact_only_terms": True,
        "excluded_exact_duplicates": True,
        "candidate_cluster_counts": list(CLUSTER_CANDIDATES),
        "candidate_models": candidate_results,
        "selected_candidate": selected_candidate,
        "stability_adjusted_rand_index": stability_adjusted_rand_index,
        "selected_cluster_profiles": selected_cluster_profiles,
        "sample": {
            "eligible_population": eligible_population_size,
            "sample_size": all_job_features.shape[0],
            "feature_count": len(skill_identifiers),
            "feature_nonzero_count": int(all_job_features.nnz),
            "training_size": training_features.shape[0],
            "holdout_size": holdout_features.shape[0],
            "holdout_silhouette_subsample_size": min(
                SILHOUETTE_SAMPLE_SIZE,
                holdout_features.shape[0],
            ),
            "random_seed": RANDOM_SEED,
            "training_fraction": round(training_features.shape[0] / all_job_features.shape[0], 2),
            "holdout_fraction": round(holdout_features.shape[0] / all_job_features.shape[0], 2),
        },
        "versions": {
            "numpy": numerical.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "release_status": "exploratory_report_only",
        "model_artifact_saved": False,
    }
    evaluation_json_path = output_directory / "skill_profile_clustering_evaluation.json"
    evaluation_markdown_path = output_directory / "SKILL_PROFILE_CLUSTERING_EVALUATION.md"
    evaluation_json_path.write_text(
        json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    evaluation_markdown_path.write_text(
        render_evaluation_report(evaluation),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "evaluation_path": str(evaluation_json_path),
                "report_path": str(evaluation_markdown_path),
                "source_archive_run_id": EXPECTED_ARCHIVE_RUN_ID,
                "sample_size": all_job_features.shape[0],
                "holdout_silhouette_scores": {
                    str(model_result["cluster_count"]): model_result["holdout_silhouette_cosine"]
                    for model_result in candidate_results
                },
                "selected_cluster_count": selected_cluster_count,
                "stability_adjusted_rand_index": stability_adjusted_rand_index,
                "release_status": evaluation["release_status"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
