from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT_DIRECTORY / "scripts" / "database_loading"))

import load_to_database as loader


class LoadPlanTests(unittest.TestCase):
    def test_neon_free_profile_is_the_default_and_uses_the_reduced_files(self) -> None:
        processed_data_directory = PROJECT_ROOT_DIRECTORY / "data" / "processed"
        reference_data_directory = PROJECT_ROOT_DIRECTORY / "data" / "reference"
        file_plan = loader.build_load_file_plan(
            processed_data_directory,
            reference_data_directory,
        )
        job_files = [
            file_specification.file_path.name
            for file_specification in file_plan
            if file_specification.table_name == "jobs"
        ]
        self.assertEqual(job_files, ["jobs_neon_free.csv.gz"])
        self.assertIn("job_skills_neon_free.csv.gz", [item.file_path.name for item in file_plan])
        self.assertIn("skill_observations_neon_free.csv.gz", [item.file_path.name for item in file_plan])
        self.assertEqual(len(file_plan), 6)

    def test_full_profile_keeps_the_original_snapshot_files_separate(self) -> None:
        file_plan = loader.build_load_file_plan(
            PROJECT_ROOT_DIRECTORY / "data" / "processed",
            PROJECT_ROOT_DIRECTORY / "data" / "reference",
            "full",
        )
        job_files = [
            file_specification.file_path.name
            for file_specification in file_plan
            if file_specification.table_name == "jobs"
        ]
        self.assertEqual(
            job_files,
            [
                "jobs_historical_2023_sample.csv.gz",
                "jobs_latest_export_unverified.csv.gz",
                "jobs_other_snapshots_unverified.csv.gz",
            ],
        )
        self.assertNotIn("jobs_archive.csv.gz", job_files)
        self.assertEqual(len(file_plan), 8)

    def test_repository_inputs_pass_local_preflight(self) -> None:
        processed_data_directory = PROJECT_ROOT_DIRECTORY / "data" / "processed"
        reference_data_directory = PROJECT_ROOT_DIRECTORY / "data" / "reference"
        file_plan = loader.build_load_file_plan(
            processed_data_directory,
            reference_data_directory,
        )
        quality_report_path = (
            processed_data_directory / loader.QUALITY_REPORT_FILE_NAMES[loader.DEFAULT_DATASET_PROFILE]
        )
        quality_report = loader.validate_local_files(file_plan, quality_report_path)
        self.assertIsInstance(quality_report, dict)
        self.assertEqual(quality_report["profile"], "neon_free_arab_complete_non_arab_stratified_v1")


class StorageReportTests(unittest.TestCase):
    def test_storage_report_includes_heap_indexes_toast_and_database_size(self) -> None:
        class StorageCursor:
            def __init__(self) -> None:
                self.result = None

            def execute(self, statement, parameters=None) -> None:
                if "pg_database_size" in statement:
                    self.result = (1000,)
                else:
                    self.result = (10, 20, 35)

            def fetchone(self):
                return self.result

        storage_report = loader.get_database_storage_report(StorageCursor())
        self.assertEqual(storage_report["current_database_bytes"], 1000)
        self.assertEqual(storage_report["managed_tables_total_bytes"], len(loader.MANAGED_TABLE_NAMES) * 35)
        self.assertEqual(
            storage_report["managed_tables"]["jobs"],
            {
                "heap_bytes": 10,
                "index_bytes": 20,
                "total_bytes_including_toast": 35,
            },
        )
        self.assertIn("not the entire Neon project", storage_report["measurement_scope"])


class LocalValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.temporary_path = Path(self.temporary_directory.name)
        self.quality_report_path = self.temporary_path / "data_quality_report.json"
        self.quality_report_path.write_text(json.dumps({"status": "passed"}), encoding="utf-8")

    def test_missing_input_file_is_rejected(self) -> None:
        missing_file = self.temporary_path / "missing.csv"
        file_plan = (loader.LoadFileSpecification("skills", missing_file),)
        with self.assertRaisesRegex(FileNotFoundError, "missing.csv"):
            loader.validate_local_files(file_plan, self.quality_report_path)

    def test_missing_primary_key_column_is_rejected(self) -> None:
        input_file = self.temporary_path / "skills.csv"
        input_file.write_text("canonical_name\nPython\n", encoding="utf-8")
        file_plan = (loader.LoadFileSpecification("skills", input_file),)
        with self.assertRaisesRegex(ValueError, "skill_id"):
            loader.validate_local_files(file_plan, self.quality_report_path)

    def test_duplicate_header_column_is_rejected(self) -> None:
        input_file = self.temporary_path / "skills.csv"
        input_file.write_text("skill_id,skill_id\npython,python\n", encoding="utf-8")
        file_plan = (loader.LoadFileSpecification("skills", input_file),)
        with self.assertRaisesRegex(ValueError, "duplicate column names"):
            loader.validate_local_files(file_plan, self.quality_report_path)

    def test_quality_report_must_be_a_json_object(self) -> None:
        input_file = self.temporary_path / "skills.csv"
        input_file.write_text("skill_id\npython\n", encoding="utf-8")
        self.quality_report_path.write_text("[]", encoding="utf-8")
        file_plan = (loader.LoadFileSpecification("skills", input_file),)
        with self.assertRaisesRegex(ValueError, "JSON object"):
            loader.validate_local_files(file_plan, self.quality_report_path)


if __name__ == "__main__":
    unittest.main()
