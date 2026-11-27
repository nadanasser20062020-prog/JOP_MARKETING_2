"""Train and evaluate a small, reproducible skill-to-observed-title model.

This is an offline preparation tool. Online scoring is implemented separately in
Node.js and reads the compact JSON artifact; the backend never runs Python.
"""

import argparse
import hashlib
import json
import math
import os
import sqlite3
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from backend.database import DEFAULT_DATABASE_PATH, PROJECT_ROOT_DIRECTORY, resolve_database_path


MODEL_ID = "positive_skill_naive_bayes_observed_title_v1"
MODEL_VERSION = 1
DEFAULT_OUTPUT_PATH = PROJECT_ROOT_DIRECTORY / "ml" / "models" / "role_title_nb_v1.json"
ELIGIBLE_POLICY_SQL = """
(
  (js.skill_match_policy = 'approved_aliases' AND js.skill_review_status = 'curated'
    AND s.match_policy = 'approved_aliases' AND s.review_status = 'curated')
  OR
  (js.skill_match_policy = 'exact_only' AND js.skill_review_status = 'curated_exact_only'
    AND s.match_policy = 'exact_only' AND s.review_status = 'curated_exact_only')
)
"""


def stable_split_bucket(record_id, salt):
    digest = hashlib.sha256(f"{salt}:{record_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def score_class(class_model, skill_indices, alpha, total_training_records, prior_weight=1.0):
    class_record_count = class_model["trainingRecordCount"]
    skill_counts = dict(class_model["skillDocumentCounts"])
    log_score = prior_weight * math.log(class_record_count / total_training_records)
    for skill_index in skill_indices:
        present_count = skill_counts.get(skill_index, 0)
        probability = (present_count + alpha) / (class_record_count + 2 * alpha)
        log_score += math.log(probability)
    return log_score


def evaluate_holdout(class_models, evaluation_rows, prior_order, alpha, total_training_records, prior_weight):
    if not evaluation_rows:
        return {
            "evaluatedRecords": 0,
            "top1Accuracy": None,
            "top5Accuracy": None,
            "priorOnlyTop1Accuracy": None,
            "priorOnlyTop5Accuracy": None,
        }

    scoring_models = []
    for model in class_models:
        class_record_count = model["trainingRecordCount"]
        denominator = class_record_count + 2 * alpha
        skill_counts = dict(model["skillDocumentCounts"])
        scoring_models.append((
            model["roleId"],
            prior_weight * math.log(class_record_count / total_training_records),
            math.log(alpha / denominator),
            {skill_id: math.log((count + alpha) / denominator) for skill_id, count in skill_counts.items()},
        ))
    top1_correct = 0
    top5_correct = 0
    prior_top1_correct = 0
    prior_top5 = {role_id for role_id in prior_order[:5]}
    prior_top1 = prior_order[0] if prior_order else None

    for true_role_id, skill_indices in evaluation_rows:
        scores = [
            (log_prior + sum(skill_log_probabilities.get(skill, default_log_probability) for skill in skill_indices), role_id)
            for role_id, log_prior, default_log_probability, skill_log_probabilities in scoring_models
        ]
        scores.sort(key=lambda item: (-item[0], item[1]))
        ranked_ids = [role_id for _, role_id in scores[:5]]
        if ranked_ids and ranked_ids[0] == true_role_id:
            top1_correct += 1
        if true_role_id in ranked_ids:
            top5_correct += 1
        if prior_top1 == true_role_id:
            prior_top1_correct += 1

    count = len(evaluation_rows)
    return {
        "evaluatedRecords": count,
        "top1Accuracy": round(top1_correct / count, 6),
        "top5Accuracy": round(top5_correct / count, 6),
        "priorOnlyTop1Accuracy": round(prior_top1_correct / count, 6),
        "priorOnlyTop5Accuracy": round(sum(role_id in prior_top5 for role_id, _ in evaluation_rows) / count, 6),
    }


def read_only_connection(database_path):
    uri = f"{database_path.as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def train_model(database_path, output_path, minimum_training_records=30, alpha=1.0, holdout_modulus=10, validation_sample_modulus=25):
    if minimum_training_records < 2:
        raise ValueError("minimum_training_records must be at least 2")
    if alpha <= 0:
        raise ValueError("alpha must be greater than zero")
    if holdout_modulus < 3 or validation_sample_modulus < 1:
        raise ValueError("Invalid deterministic split configuration")

    resolved_database = resolve_database_path(database_path)
    output_path = Path(output_path).expanduser()
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT_DIRECTORY / output_path
    output_path = output_path.resolve()
    try:
        output_path.relative_to(PROJECT_ROOT_DIRECTORY)
    except ValueError as error:
        raise ValueError("Model artifact output must stay inside the project root.") from error

    connection = read_only_connection(resolved_database)
    try:
        import_snapshot = connection.execute("""
            SELECT source_archive_run_id, archive_generated_on_utc
            FROM import_runs
            WHERE run_status = 'succeeded'
            ORDER BY import_run_id DESC
            LIMIT 1
        """).fetchone()
        if import_snapshot is None:
            raise ValueError("A successful local dataset import is required before model training.")

        vocabulary_rows = connection.execute(f"""
            SELECT DISTINCT s.skill_id, s.canonical_name
            FROM job_skills AS js
            JOIN skills AS s ON s.skill_id = js.skill_id
              AND js.skill_match_policy = s.match_policy
              AND js.skill_review_status = s.review_status
              AND {ELIGIBLE_POLICY_SQL}
            ORDER BY s.skill_id
        """).fetchall()
        vocabulary = [
            {"skillId": row["skill_id"], "name": row["canonical_name"]}
            for row in vocabulary_rows
        ]
        skill_index = {item["skillId"]: index for index, item in enumerate(vocabulary)}
        if not vocabulary:
            raise ValueError("No eligible, reviewed skill features are available.")

        training_record_counts = Counter()
        training_skill_counts = defaultdict(Counter)
        display_titles = {}
        validation_record_counts = Counter()
        holdout_record_counts = Counter()
        validation_rows = []
        holdout_rows = []
        total_training_records = 0
        total_validation_records = 0
        total_holdout_records = 0
        sampled_validation_records = 0
        sampled_holdout_records = 0

        rows = connection.execute(f"""
            SELECT js.record_id,
                   lower(trim(j.title)) AS role_id,
                   trim(j.title) AS display_title,
                   js.skill_id
            FROM job_skills AS js
            JOIN jobs AS j ON j.record_id = js.record_id
            JOIN skills AS s ON s.skill_id = js.skill_id
              AND js.skill_match_policy = s.match_policy
              AND js.skill_review_status = s.review_status
              AND {ELIGIBLE_POLICY_SQL}
            WHERE j.title IS NOT NULL AND trim(j.title) <> ''
              AND COALESCE(j.exact_duplicate_within_source, '') <> 'yes'
            GROUP BY js.record_id, lower(trim(j.title)), trim(j.title), js.skill_id
            ORDER BY js.record_id, js.skill_id
        """)

        current_record_id = None
        current_role_id = None
        current_display_title = None
        current_skill_indices = []

        def finish_record():
            nonlocal total_training_records, total_validation_records, total_holdout_records
            nonlocal sampled_validation_records, sampled_holdout_records
            if current_record_id is None or not current_skill_indices:
                return
            split_bucket = stable_split_bucket(current_record_id, "holdout-v1") % holdout_modulus
            if split_bucket == 0:
                total_validation_records += 1
                validation_record_counts[current_role_id] += 1
                sample_bucket = stable_split_bucket(current_record_id, "validation-sample-v1")
                if sample_bucket % validation_sample_modulus == 0:
                    validation_rows.append((current_role_id, tuple(current_skill_indices)))
                    sampled_validation_records += 1
            elif split_bucket == 1:
                total_holdout_records += 1
                holdout_record_counts[current_role_id] += 1
                sample_bucket = stable_split_bucket(current_record_id, "test-sample-v1")
                if sample_bucket % validation_sample_modulus == 0:
                    holdout_rows.append((current_role_id, tuple(current_skill_indices)))
                    sampled_holdout_records += 1
            else:
                total_training_records += 1
                training_record_counts[current_role_id] += 1
                existing_title = display_titles.get(current_role_id)
                if existing_title is None or current_display_title < existing_title:
                    display_titles[current_role_id] = current_display_title
                training_skill_counts[current_role_id].update(current_skill_indices)

        for row in rows:
            if row["record_id"] != current_record_id:
                finish_record()
                current_record_id = row["record_id"]
                current_role_id = row["role_id"]
                current_display_title = row["display_title"]
                current_skill_indices = []
            current_skill_indices.append(skill_index[row["skill_id"]])
        finish_record()

        class_models = []
        for role_id, record_count in training_record_counts.items():
            if record_count < minimum_training_records:
                continue
            skill_documents = training_skill_counts[role_id]
            class_models.append({
                "roleId": role_id,
                "displayTitle": display_titles[role_id],
                "trainingRecordCount": record_count,
                "skillDocumentCounts": [
                    [skill_id, document_count]
                    for skill_id, document_count in sorted(skill_documents.items())
                ],
            })
        class_models.sort(key=lambda item: item["roleId"])
        if not class_models:
            raise ValueError("No title classes meet the minimum training-record threshold.")

        model_training_records = sum(item["trainingRecordCount"] for item in class_models)
        supported_role_ids = {item["roleId"] for item in class_models}
        supported_validation_records = sum(
            count for role_id, count in validation_record_counts.items()
            if role_id in supported_role_ids
        )
        supported_holdout_records = sum(
            count for role_id, count in holdout_record_counts.items()
            if role_id in supported_role_ids
        )
        supported_validation_rows = [row for row in validation_rows if row[0] in supported_role_ids]
        supported_holdout_rows = [row for row in holdout_rows if row[0] in supported_role_ids]
        prior_order = [
            item["roleId"] for item in sorted(
                class_models,
                key=lambda item: (-item["trainingRecordCount"], item["roleId"]),
            )
        ]
        prior_weight_candidates = [
            0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0,
            2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 4.0, 5.0,
        ]
        validation_metrics = {
            str(weight): evaluate_holdout(
                class_models,
                supported_validation_rows,
                prior_order,
                alpha,
                model_training_records,
                weight,
            )
            for weight in prior_weight_candidates
        }
        if supported_validation_rows:
            selected_prior_weight = max(
                prior_weight_candidates,
                key=lambda weight: (
                    validation_metrics[str(weight)]["top5Accuracy"],
                    validation_metrics[str(weight)]["top1Accuracy"],
                    -weight,
                ),
            )
        else:
            selected_prior_weight = 1.0
        test_evaluation = evaluate_holdout(
            class_models,
            supported_holdout_rows,
            prior_order,
            alpha,
            model_training_records,
            selected_prior_weight,
        )

        background_skill_counts = [0] * len(vocabulary)
        for item in class_models:
            for skill_id, count in item["skillDocumentCounts"]:
                background_skill_counts[skill_id] += count

        compact_classes = []
        for item in class_models:
            compact_classes.append({
                "roleId": item["roleId"],
                "displayTitle": item["displayTitle"],
                "trainingRecordCount": item["trainingRecordCount"],
                "skillDocumentCounts": item["skillDocumentCounts"],
            })

        artifact = {
            "modelId": MODEL_ID,
            "modelVersion": MODEL_VERSION,
            "task": "Rank normalized observed title strings from positive evidence in a set of reviewed skills.",
            "modelFamily": "positive-evidence Bernoulli Naive Bayes",
            "trainedModel": True,
            "inferenceRuntime": "Node.js",
            "trainingRuntime": "Python offline only",
            "sourceArchiveRunId": import_snapshot["source_archive_run_id"],
            "sourceArchiveGeneratedOnUtc": import_snapshot["archive_generated_on_utc"],
            "recordDefinition": "One retained source job row with a non-empty title and at least one eligible reviewed skill link.",
            "excludedRows": ["records marked exact_duplicate_within_source=yes", "records without a non-empty title", "records without eligible reviewed skills"],
            "labelDefinition": "lower(trim(jobs.title)); exact observed title strings only, not a curated occupation taxonomy.",
            "featureDefinition": "Binary document presence of a reviewed skill ID; a missing input skill is not treated as a negative feature.",
            "split": {
                "method": "Stable SHA-256 record-ID buckets; eight of ten buckets train, one validates, and one is held out for test.",
                "splitModulus": holdout_modulus,
                "trainingRecords": total_training_records,
                "validationRecords": total_validation_records,
                "testRecords": total_holdout_records,
                "validationSampleModulus": validation_sample_modulus,
                "sampledValidationRecords": sampled_validation_records,
                "sampledTestRecords": sampled_holdout_records,
                "duplicateLeakageControl": "Rows flagged exact_duplicate_within_source=yes are excluded from train, validation, and test.",
            },
            "hyperparameters": {
                "alpha": alpha,
                "priorWeight": selected_prior_weight,
                "minimumTrainingRecordsPerTitle": minimum_training_records,
            },
            "coverage": {
                "eligibleVocabularySkills": len(vocabulary),
                "trainedTitleClasses": len(class_models),
                "totalRecordsWithTitleAndEligibleSkills": total_training_records + total_validation_records + total_holdout_records,
                "trainingRecordsWithTitleAndEligibleSkills": total_training_records,
                "validationRecordsWithTitleAndEligibleSkills": total_validation_records,
                "testRecordsWithTitleAndEligibleSkills": total_holdout_records,
                "trainingRecordsInSupportedClasses": model_training_records,
                "trainingCoveragePercent": round(100 * model_training_records / total_training_records, 4) if total_training_records else 0,
                "validationRecordsInSupportedClasses": supported_validation_records,
                "validationCoveragePercent": round(100 * supported_validation_records / total_validation_records, 4) if total_validation_records else 0,
                "testRecordsInSupportedClasses": supported_holdout_records,
                "testCoveragePercent": round(100 * supported_holdout_records / total_holdout_records, 4) if total_holdout_records else 0,
            },
            "evaluation": {
                "selectionCriterion": "Highest validation top-5 accuracy; break ties by top-1 accuracy, then lower prior weight.",
                "candidatePriorWeights": prior_weight_candidates,
                "validationByPriorWeight": validation_metrics,
                "selectedPriorWeight": selected_prior_weight,
                "heldOutTest": test_evaluation,
            },
            "vocabulary": vocabulary,
            "backgroundSkillDocumentCounts": background_skill_counts,
            "trainingRecordCount": model_training_records,
            "classes": compact_classes,
            "scoreDefinition": "priorWeight * log P(title) + sum over submitted skills of log P(skill present | title); missing input skills contribute no evidence; normalized across trained title classes with softmax for a relative score.",
            "limitations": [
                "The model predicts exact normalized title strings found in this collected sample; it does not assign a stable occupation or job-family category.",
                "Scores are model-relative and uncalibrated; they are not hiring probabilities, job availability, qualification judgments, or market estimates.",
                "Only classes meeting the documented training-support threshold are represented; uncommon title labels are out of model scope.",
                "The independence assumption ignores skill interactions, source-specific collection bias, time, geography, and user experience.",
                "Missing user-entered skills are not evidence that the person lacks those skills.",
            ],
        }
    finally:
        connection.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(prefix=".role-title-model-", suffix=".json", dir=output_path.parent)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as target:
            json.dump(artifact, target, ensure_ascii=False, indent=2, sort_keys=True)
            target.write("\n")
        os.replace(temporary_name, output_path)
        os.chmod(output_path, 0o644)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise

    summary = {
        "artifact": str(output_path.relative_to(PROJECT_ROOT_DIRECTORY)),
        "modelId": artifact["modelId"],
        "modelVersion": artifact["modelVersion"],
        "trainingRecords": total_training_records,
        "supportedTrainingRecords": model_training_records,
        "trainedTitleClasses": len(class_models),
        "trainingCoveragePercent": artifact["coverage"]["trainingCoveragePercent"],
        "validationRecords": total_validation_records,
        "supportedValidationRecords": supported_validation_records,
        "testRecords": total_holdout_records,
        "supportedTestRecords": supported_holdout_records,
        "selectedPriorWeight": selected_prior_weight,
        "validationTuning": validation_metrics,
        "heldOutTest": test_evaluation,
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description="Train a reviewed-skill to observed-title Naive Bayes model.")
    parser.add_argument("--database", default=DEFAULT_DATABASE_PATH, help="Local SQLite path inside the project root")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Model JSON artifact path inside the project root")
    parser.add_argument("--minimum-training-records", type=int, default=30)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--holdout-modulus", type=int, default=10)
    parser.add_argument("--validation-sample-modulus", type=int, default=25)
    arguments = parser.parse_args()
    summary = train_model(
        arguments.database,
        arguments.output,
        minimum_training_records=arguments.minimum_training_records,
        alpha=arguments.alpha,
        holdout_modulus=arguments.holdout_modulus,
        validation_sample_modulus=arguments.validation_sample_modulus,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
