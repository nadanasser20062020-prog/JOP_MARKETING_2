import csv
import gzip
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.database import DEFAULT_DATABASE_PATH, PROJECT_ROOT_DIRECTORY, connect_to_database, resolve_database_path
from scripts.database_loading import sqlite_database


class SQLiteDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory(dir=PROJECT_ROOT_DIRECTORY, prefix=".unit-test-")
        self.temporary_path = Path(self.temporary_directory.name)
        self.database_path = self.temporary_path / "local_test.sqlite3"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_migrations_create_all_domain_tables_and_are_repeatable(self):
        sqlite_database.initialize_database(self.database_path)
        connection = connect_to_database(self.database_path)
        try:
            sqlite_database.apply_migrations(connection)
            table_names = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                )
            }
            expected_table_names = {
                "schema_migrations",
                "data_sources",
                "source_files",
                "import_runs",
                "import_run_files",
                "skills",
                "skill_aliases",
                "jobs",
                "job_cleaning_audit",
                "job_skills",
                "skill_observations",
                "learning_resources",
                "learning_resource_skills",
                "learning_resource_languages",
                "api_scope_rollups",
                "api_scope_skill_rollups",
                "api_role_scope_rollups",
                "api_role_skill_rollups",
                "api_source_field_coverage",
                "api_historical_month_rollups",
            }
            self.assertEqual(table_names, expected_table_names)
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            index_names = {
                row["name"]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
            }
            self.assertIn("idx_api_role_skill_by_role", index_names)
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0],
                6,
            )
            source_file_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(source_files)")
            }
            self.assertIn("source_file_id", source_file_columns)
            self.assertIn("sha256", source_file_columns)
            audit_columns = [
                row["name"] for row in connection.execute("PRAGMA table_info(job_cleaning_audit)")
            ]
            self.assertEqual(len(audit_columns), 123)
            self.assertEqual(audit_columns[:4], ["record_id", "source_dataset", "source_file", "source_row_number"])
            self.assertIn("source_row_json", audit_columns)
            self.assertEqual(
                connection.execute("SELECT type FROM sqlite_master WHERE name = 'cleaned_jobs'").fetchone()[0],
                "view",
            )
        finally:
            connection.close()

    def test_auto_source_never_falls_back_when_full_inputs_are_missing(self):
        processed_directory = self.temporary_path / "processed"
        archive_directory = self.temporary_path / "archive"
        processed_directory.mkdir()
        archive_directory.mkdir()
        with self.assertRaisesRegex(FileNotFoundError, "No full local archive"):
            sqlite_database.select_import_source(
                "auto",
                processed_directory,
                archive_directory,
            )

    def test_auto_source_prefers_a_verified_full_archive(self):
        processed_directory = self.temporary_path / "processed"
        archive_directory = self.temporary_path / "archive"
        processed_directory.mkdir()
        archive_directory.mkdir()
        table_checksums = {}
        table_manifest = {}
        for table_name in sqlite_database.ARCHIVE_TABLE_NAMES:
            table_content = f"archive table {table_name}".encode("utf-8")
            (archive_directory / f"{table_name}.parquet").write_bytes(table_content)
            checksum = hashlib.sha256(table_content).hexdigest()
            table_checksums[f"{table_name}.parquet"] = checksum
            table_manifest[table_name] = {
                "file": f"{table_name}.parquet",
                "row_count": 0,
                "sha256": checksum,
            }
        manifest = {
            "package_name": "full_archive_parquet_v1",
            "import_run_id": "unit-test-archive",
            "totals": {"jobs": 0, "job_skills": 0},
            "tables": table_manifest,
        }
        manifest_content = json.dumps(manifest, sort_keys=True)
        (archive_directory / "manifest.json").write_text(manifest_content, encoding="utf-8")
        table_checksums["manifest.json"] = hashlib.sha256(
            manifest_content.encode("utf-8")
        ).hexdigest()
        checksum_text = "".join(
            f"{checksum}  {file_name}\n"
            for file_name, checksum in sorted(table_checksums.items())
        )
        (archive_directory / "checksums.sha256").write_text(checksum_text, encoding="utf-8")

        selected_source, selected_paths = sqlite_database.select_import_source(
            "auto",
            processed_directory,
            archive_directory,
        )
        self.assertEqual(selected_source, "archive")
        self.assertIn(archive_directory / "jobs.parquet", selected_paths)
        self.assertIn(sqlite_database.LEARNING_RESOURCES_CSV_FILE_PATH, selected_paths)

    def test_auto_source_uses_complete_normalized_files_when_archive_is_absent(self):
        processed_directory = self.temporary_path / "processed"
        archive_directory = self.temporary_path / "archive"
        processed_directory.mkdir()
        archive_directory.mkdir()
        self.create_processed_fixture(processed_directory)

        selected_source, selected_paths = sqlite_database.select_import_source(
            "auto",
            processed_directory,
            archive_directory,
        )
        self.assertEqual(selected_source, "processed")
        self.assertIn(processed_directory / "job_skills.csv.gz", selected_paths)

    def test_learning_resource_json_and_language_csv_load_all_labels(self):
        sqlite_database.initialize_database(self.database_path)
        connection = connect_to_database(self.database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            skill_count = sqlite_database.load_skill_catalog(connection)
            resource_counts = sqlite_database.load_learning_resources(connection)
            sqlite_database.validate_database(connection)
            connection.commit()
        finally:
            connection.close()

        self.assertEqual(skill_count, 1498)
        self.assertEqual(
            resource_counts,
            {
                "learning_resources": 32,
                "learning_resource_skills": 48,
                "learning_resource_languages": 37,
            },
        )
        connection = connect_to_database(self.database_path)
        try:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM learning_resource_languages WHERE instr(language_label, ';') > 0"
                ).fetchone()[0],
                0,
            )
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
        finally:
            connection.close()

    def test_repeating_the_same_processed_import_is_idempotent(self):
        processed_directory = self.temporary_path / "processed"
        self.create_processed_fixture(processed_directory)
        first_result = sqlite_database.load_database(
            self.database_path,
            source_mode="processed",
            processed_directory=processed_directory,
        )
        second_result = sqlite_database.load_database(
            self.database_path,
            source_mode="processed",
            processed_directory=processed_directory,
        )
        self.assertFalse(first_result["skipped"])
        self.assertTrue(second_result["skipped"])
        self.assertEqual(second_result["row_counts"]["jobs"], 1)
        self.assertEqual(second_result["row_counts"]["import_runs"], 1)

    def test_different_input_requires_explicit_replacement(self):
        processed_directory = self.temporary_path / "processed"
        job_record = self.create_processed_fixture(processed_directory)
        sqlite_database.load_database(
            self.database_path,
            source_mode="processed",
            processed_directory=processed_directory,
        )
        job_record["title"] = "Senior Python Data Engineer"
        self.write_gzip_csv(
            processed_directory / "jobs_unit_test.csv.gz",
            sqlite_database.JOB_FIELD_NAMES,
            [job_record],
        )

        with self.assertRaises(sqlite_database.DatasetAlreadyLoadedError):
            sqlite_database.load_database(
                self.database_path,
                source_mode="processed",
                processed_directory=processed_directory,
            )

    def test_explicit_replacement_rebuilds_the_local_snapshot(self):
        processed_directory = self.temporary_path / "processed"
        self.create_processed_fixture(processed_directory)
        sqlite_database.load_database(
            self.database_path,
            source_mode="processed",
            processed_directory=processed_directory,
        )
        rebuilt_result = sqlite_database.load_database(
            self.database_path,
            source_mode="processed",
            processed_directory=processed_directory,
            replace_existing=True,
        )
        self.assertFalse(rebuilt_result["skipped"])
        self.assertEqual(rebuilt_result["row_counts"]["jobs"], 1)
        self.assertEqual(rebuilt_result["row_counts"]["import_runs"], 1)

    def test_database_connection_rejects_connection_urls_and_paths_outside_project_root(self):
        self.assertEqual(resolve_database_path(), DEFAULT_DATABASE_PATH.resolve())
        with self.assertRaises(ValueError):
            resolve_database_path("sqlite:///remote/database.sqlite3")
        with self.assertRaisesRegex(ValueError, "inside the project root"):
            resolve_database_path(PROJECT_ROOT_DIRECTORY.parent / "outside.sqlite3")

    def test_processed_staging_files_load_into_sqlite(self):
        processed_directory = self.temporary_path / "processed"
        job_record = self.create_processed_fixture(processed_directory)
        result = sqlite_database.load_database(
            self.database_path,
            source_mode="processed",
            processed_directory=processed_directory,
        )
        self.assertEqual(result["source_mode"], "processed")
        self.assertEqual(result["row_counts"]["jobs"], 1)
        self.assertEqual(result["row_counts"]["job_skills"], 1)
        self.assertEqual(result["row_counts"]["skill_observations"], 1)
        self.assertEqual(result["job_rows_by_source"], {"unit_test_jobs": 1})

        connection = connect_to_database(self.database_path)
        try:
            job_row = connection.execute(
                "SELECT title, country, source_file FROM jobs WHERE record_id = ?",
                (job_record["record_id"],),
            ).fetchone()
            self.assertEqual(tuple(job_row), ("Python Data Engineer", "Egypt", "unit_test_jobs.csv"))
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
        finally:
            connection.close()

    def test_foreign_keys_reject_orphaned_job_skill_links(self):
        processed_directory = self.temporary_path / "processed"
        self.create_processed_fixture(processed_directory)
        sqlite_database.load_database(
            self.database_path,
            source_mode="processed",
            processed_directory=processed_directory,
        )
        connection = connect_to_database(self.database_path)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO job_skills "
                    "(record_id, source_dataset, source_file, skill_raw, skill_normalized, "
                    "skill_id, skill_category, skill_match_policy, skill_review_status) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        "missing-job",
                        "unit_test_jobs",
                        "unit_test_jobs.csv",
                        "Python",
                        "python",
                        "skill:python",
                        "programming_language",
                        "approved_aliases",
                        "curated",
                    ),
                )
        finally:
            connection.close()

    def create_processed_fixture(self, processed_directory):
        processed_directory.mkdir(parents=True, exist_ok=True)
        job_record = {field_name: "" for field_name in sqlite_database.JOB_FIELD_NAMES}
        job_record.update(
            {
                "record_id": "unit_test_jobs:row-1:fixture",
                "source_dataset": "unit_test_jobs",
                "source_file": "unit_test_jobs.csv",
                "source_row_number": "1",
                "title": "Python Data Engineer",
                "country": "Egypt",
                "skills": "Python",
                "source_date_field": "not_available",
                "listing_status": "unknown_not_verified",
                "snapshot_type": "unit_test_snapshot",
            }
        )
        job_skill_record = {
            "record_id": job_record["record_id"],
            "source_dataset": job_record["source_dataset"],
            "source_file": job_record["source_file"],
            "skill_raw": "Python",
            "skill_normalized": "python",
            "skill_id": "skill:python",
            "skill_category": "programming_language",
            "skill_match_policy": "approved_aliases",
            "skill_review_status": "curated",
            "skill_provenance": "unit test fixture",
            "skill_status": "present_in_base_export",
        }
        skill_observation_record = {
            "source_dataset": "unit_test_jobs",
            "skill_raw": "Python",
            "skill_normalized": "python",
            "occurrence_count": "1",
        }
        self.write_gzip_csv(
            processed_directory / "jobs_unit_test.csv.gz",
            sqlite_database.JOB_FIELD_NAMES,
            [job_record],
        )
        self.write_gzip_csv(
            processed_directory / "job_skills.csv.gz",
            sqlite_database.JOB_SKILL_FIELD_NAMES,
            [job_skill_record],
        )
        self.write_gzip_csv(
            processed_directory / "skill_observations.csv.gz",
            sqlite_database.SKILL_OBSERVATION_FIELD_NAMES,
            [skill_observation_record],
        )
        return job_record

    def write_gzip_csv(self, file_path, field_names, rows):
        with gzip.open(file_path, "wt", encoding="utf-8", newline="") as destination_file:
            writer = csv.DictWriter(destination_file, fieldnames=field_names)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
