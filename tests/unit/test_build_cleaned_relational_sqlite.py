import csv
import gzip
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.database import PROJECT_ROOT_DIRECTORY, connect_to_database
from scripts.database_loading import sqlite_database
from scripts.database_loading.build_cleaned_relational_sqlite import (
    build_database,
    skill_label_for_id,
)


class SkillLabelResolutionTests(unittest.TestCase):
    def test_mismatched_arrays_do_not_use_positional_skill_label(self):
        catalog = {
            "skill:python": {"canonical_name": "Python"},
            "skill:sql": {"canonical_name": "SQL"},
        }
        aliases = {
            "wrong first label": {"skill:sql"},
            "python": {"skill:python"},
        }

        label, normalized, used_fallback = skill_label_for_id(
            "skill:python",
            ["Wrong first label", "Python"],
            0,
            1,
            aliases,
            catalog,
        )

        self.assertEqual((label, normalized, used_fallback), ("Python", "python", False))

    def test_multiple_matching_labels_fall_back_to_canonical_name(self):
        catalog = {"skill:python": {"canonical_name": "Python"}}
        aliases = {
            "py": {"skill:python"},
            "python": {"skill:python"},
        }

        label, normalized, used_fallback = skill_label_for_id(
            "skill:python",
            ["Py", "Python"],
            0,
            1,
            aliases,
            catalog,
        )

        self.assertEqual((label, normalized, used_fallback), ("Python", "python", True))

    def test_label_shared_by_multiple_skills_is_not_assigned_ambiguously(self):
        catalog = {
            "skill:python": {"canonical_name": "Python"},
            "skill:other": {"canonical_name": "Other"},
        }
        aliases = {"shared label": {"skill:python", "skill:other"}}

        label, normalized, used_fallback = skill_label_for_id(
            "skill:python",
            ["Shared label"],
            0,
            1,
            aliases,
            catalog,
        )

        self.assertEqual((label, normalized, used_fallback), ("Python", "python", True))


class CleanedRelationalImportTests(unittest.TestCase):
    def test_import_preserves_full_audit_row_and_enforces_audit_foreign_key(self):
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT_DIRECTORY, prefix=".cleaned-import-test-") as directory:
            temporary_path = Path(directory)
            schema = sqlite3.connect(":memory:")
            schema.row_factory = sqlite3.Row
            schema.execute("PRAGMA foreign_keys = ON")
            sqlite_database.apply_migrations(schema)
            fieldnames = [
                row["name"]
                for row in schema.execute("PRAGMA table_info(job_cleaning_audit)")
            ]
            schema.close()
            self.assertEqual(len(fieldnames), 123)

            dataset_path = temporary_path / "jobs_cleaned_audited.csv.gz"
            row = {field: "" for field in fieldnames}
            row.update(
                {
                    "record_id": "cleaned-import-test-record",
                    "source_dataset": "international_jobs",
                    "source_file": "International_Tech_Jobs_Filtered.csv",
                    "source_row_number": "1",
                    "title_raw": "Python Data Engineer",
                    "title_clean": "Python Data Engineer",
                    "company_clean": "Example Company",
                    "country_standardized": "Egypt",
                    "snapshot_type": "historical_2023_sample",
                    "skills_raw": "Python",
                    "skills_tokens_json": json.dumps(["Python"]),
                    "skill_ids_json": json.dumps(["skill:python"]),
                    "source_row_json": json.dumps({"original": "source, value"}),
                }
            )
            with gzip.open(dataset_path, "wt", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(row)

            summary_path = temporary_path / "cleaning_summary.json"
            summary = {
                "cleaned_dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
                "input_rows": 1,
                "output_rows": 1,
                "rows_dropped": 0,
                "audit_date": "2026-10-28",
                "source_ref": "unit-test",
                "available_job_source_count": 1,
                "file_reports": {
                    "International_Tech_Jobs_Filtered.csv": {
                        "source_dataset": "international_jobs",
                        "status": "processed",
                        "rows": 1,
                    }
                },
            }
            summary_path.write_text(json.dumps(summary), encoding="utf-8")

            source_manifest_path = temporary_path / "source_manifest.csv"
            with source_manifest_path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(
                    output,
                    fieldnames=["file", "role", "size_bytes", "sha256", "status"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "file": "International_Tech_Jobs_Filtered.csv",
                        "role": "selected_job_source",
                        "size_bytes": "1",
                        "sha256": "unit-test-source-hash",
                        "status": "available",
                    }
                )

            database_path = temporary_path / "jobs.sqlite3"
            result = build_database(
                dataset_path,
                database_path,
                summary_path=summary_path,
                source_manifest_path=source_manifest_path,
                progress=False,
            )

            self.assertEqual(result["rows"], 1)
            self.assertEqual(result["cleaned_columns"], 123)
            self.assertEqual(result["job_skill_links"], 1)
            self.assertEqual(result["integrity_check"], "ok")
            self.assertEqual(result["foreign_key_violations"], 0)

            connection = connect_to_database(database_path)
            try:
                stored = connection.execute(
                    "SELECT * FROM job_cleaning_audit WHERE record_id = ?",
                    (row["record_id"],),
                ).fetchone()
                self.assertIsNotNone(stored)
                self.assertEqual(stored["title_clean"], row["title_clean"])
                self.assertEqual(stored["source_row_json"], row["source_row_json"])
                self.assertEqual(
                    [column["name"] for column in connection.execute("PRAGMA table_info(job_cleaning_audit)")],
                    fieldnames,
                )
                self.assertEqual(
                    tuple(
                        connection.execute(
                            "SELECT skill_id, skill_raw FROM job_skills WHERE record_id = ?",
                            (row["record_id"],),
                        ).fetchone()
                    ),
                    ("skill:python", "Python"),
                )
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "INSERT INTO job_cleaning_audit "
                        "(record_id, source_dataset, source_file, source_row_number) "
                        "VALUES (?, ?, ?, ?)",
                        (
                            "orphan-audit-row",
                            "international_jobs",
                            "International_Tech_Jobs_Filtered.csv",
                            2,
                        ),
                    )
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
