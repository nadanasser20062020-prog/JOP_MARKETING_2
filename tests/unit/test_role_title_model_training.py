import json
import tempfile
import unittest
from pathlib import Path

from backend.database import PROJECT_ROOT_DIRECTORY, connect_to_database
from ml.skill_matching.train_role_title_nb import score_class, train_model
from scripts.database_loading.sqlite_database import initialize_database


class RoleTitleModelTrainingTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory(
            dir=PROJECT_ROOT_DIRECTORY,
            prefix=".role-model-test-",
        )
        self.temporary_path = Path(self.temporary_directory.name)
        self.database_path = self.temporary_path / "fixture.sqlite3"
        initialize_database(self.database_path)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def create_fixture(self):
        connection = connect_to_database(self.database_path)
        try:
            connection.execute(
                "INSERT INTO data_sources (source_dataset, display_name) VALUES (?, ?)",
                ("fixture_jobs", "Fixture Jobs"),
            )
            connection.execute(
                "INSERT INTO source_files (source_dataset, source_file) VALUES (?, ?)",
                ("fixture_jobs", "fixture.csv"),
            )
            connection.executemany(
                "INSERT INTO skills (skill_id, canonical_name, category, match_policy, review_status) "
                "VALUES (?, ?, ?, 'approved_aliases', 'curated')",
                [
                    ("skill:python", "Python", "Programming"),
                    ("skill:sql", "SQL", "Data"),
                    ("skill:aws", "AWS", "Cloud"),
                ],
            )
            connection.execute(
                "INSERT INTO import_runs (run_status, started_at, pipeline_version, "
                "source_archive_run_id, archive_generated_on_utc) "
                "VALUES ('succeeded', '2026-10-28T00:00:00Z', 'fixture', 'fixture_archive', '2026-10-28')"
            )

            for index in range(32):
                title = "Data Engineer" if index < 16 else "Data Scientist"
                record_id = f"fixture:{index:03d}"
                duplicate_flag = "yes" if index == 0 else "no"
                connection.execute(
                    "INSERT INTO jobs (record_id, source_dataset, source_file, source_row_number, title, "
                    "exact_duplicate_within_source) VALUES (?, 'fixture_jobs', 'fixture.csv', ?, ?, ?)",
                    (record_id, index + 1, title, duplicate_flag),
                )
                skill_ids = ["skill:python", "skill:sql"]
                if title == "Data Engineer" and index % 2 == 0:
                    skill_ids.append("skill:aws")
                for skill_id in skill_ids:
                    connection.execute(
                        "INSERT INTO job_skills (record_id, source_dataset, source_file, skill_raw, "
                        "skill_normalized, skill_id, skill_category, skill_match_policy, "
                        "skill_review_status, skill_provenance, skill_status) "
                        "SELECT ?, 'fixture_jobs', 'fixture.csv', canonical_name, lower(canonical_name), "
                        "skill_id, category, 'approved_aliases', 'curated', 'fixture', 'present_in_base_export' "
                        "FROM skills WHERE skill_id = ?",
                        (record_id, skill_id),
                    )
            connection.commit()
        finally:
            connection.close()

    def test_training_builds_a_small_artifact_and_excludes_flagged_duplicates(self):
        self.create_fixture()
        output_path = self.temporary_path / "model.json"
        summary = train_model(
            self.database_path,
            output_path,
            minimum_training_records=2,
            alpha=1.0,
            holdout_modulus=4,
            validation_sample_modulus=1,
        )
        artifact = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["modelId"], "positive_skill_naive_bayes_observed_title_v1")
        self.assertEqual(artifact["inferenceRuntime"], "Node.js")
        self.assertEqual(artifact["sourceArchiveRunId"], "fixture_archive")
        self.assertEqual(artifact["coverage"]["trainedTitleClasses"], 2)
        self.assertEqual(artifact["split"]["trainingRecords"] + artifact["split"]["validationRecords"] + artifact["split"]["testRecords"], 31)
        self.assertEqual(artifact["split"]["duplicateLeakageControl"].startswith("Rows flagged"), True)
        self.assertIn("heldOutTest", artifact["evaluation"])
        self.assertEqual(len(artifact["vocabulary"]), 3)

    def test_naive_bayes_score_rewards_class_specific_skill_evidence(self):
        common = {"trainingRecordCount": 20, "skillDocumentCounts": [[0, 4]]}
        specific = {"trainingRecordCount": 20, "skillDocumentCounts": [[0, 18]]}
        self.assertGreater(
            score_class(specific, [0], alpha=1.0, total_training_records=40),
            score_class(common, [0], alpha=1.0, total_training_records=40),
        )

    def test_model_output_must_remain_inside_project_root(self):
        with self.assertRaisesRegex(ValueError, "inside the project root"):
            train_model(
                self.database_path,
                PROJECT_ROOT_DIRECTORY.parent / "outside-model.json",
                minimum_training_records=2,
            )


if __name__ == "__main__":
    unittest.main()
