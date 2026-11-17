from __future__ import annotations

import csv
import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT_DIRECTORY / "scripts" / "data_cleaning"))

import build_neon_free_dataset as builder


class NeonFreeDatasetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root_directory = Path(self.temporary_directory.name)
        self.processed_directory = self.root_directory / "processed"
        self.reference_directory = self.root_directory / "reference"
        self.output_directory = self.root_directory / "output"
        self.processed_directory.mkdir()
        self.reference_directory.mkdir()
        self.job_headers = [
            "record_id",
            "source_dataset",
            "source_file",
            "source_row_number",
            "country",
            "title",
        ]
        self.job_rows_by_file = {
            "jobs_historical_2023_sample.csv.gz": [
                self.job("arab-egypt", "international_jobs", "egypt-history.csv", "Egypt"),
                self.job("us-one", "international_jobs", "international.csv", "United States"),
                self.job("us-two", "international_jobs", "international.csv", "United States"),
                self.job("france-one", "international_jobs", "international.csv", "France"),
                self.job("country-blank", "international_jobs", "international.csv", ""),
            ],
            "jobs_latest_export_unverified.csv.gz": [
                self.job("arab-uae", "arab_tech_jobs", "arab.csv", "United Arab Emirates"),
                self.job("arab-ksa", "cybersecurity_jobs", "cyber.csv", "KSA"),
                self.job("remote-one", "startup_jobs", "startup.csv", "Remote (Anywhere)"),
                self.job("country-unknown", "startup_jobs", "startup.csv", "Other/Unknown"),
            ],
            "jobs_other_snapshots_unverified.csv.gz": [
                self.job("arab-comoros", "international_jobs", "international.csv", "Comoros"),
                self.job("arab-syria", "international_jobs", "international.csv", "Syrian Arab Republic"),
                self.job("worldwide-one", "jooble_careerjet_jobs", "jooble.csv", "Worldwide"),
            ],
        }
        for file_name, rows in self.job_rows_by_file.items():
            with gzip.open(self.processed_directory / file_name, "wt", encoding="utf-8", newline="") as output_file:
                writer = csv.DictWriter(output_file, fieldnames=self.job_headers, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)

        job_skill_headers = [
            "record_id",
            "source_dataset",
            "source_file",
            "skill_raw",
            "skill_normalized",
            "skill_id",
        ]
        with gzip.open(
            self.processed_directory / builder.JOB_SKILLS_INPUT_FILE_NAME,
            "wt",
            encoding="utf-8",
            newline="",
        ) as output_file:
            writer = csv.DictWriter(output_file, fieldnames=job_skill_headers, lineterminator="\n")
            writer.writeheader()
            for job_row in self.all_job_rows:
                writer.writerow(
                    {
                        "record_id": job_row["record_id"],
                        "source_dataset": job_row["source_dataset"],
                        "source_file": job_row["source_file"],
                        "skill_raw": "Python",
                        "skill_normalized": "python",
                        "skill_id": "skill:python",
                    }
                )

        self.write_reference_csv("skill_catalog.csv", ["skill_id"], [{"skill_id": "skill:python"}])
        self.write_reference_csv(
            "skill_aliases.csv",
            ["alias_normalized"],
            [{"alias_normalized": "python"}],
        )
        self.write_reference_csv("learning_resources.csv", ["resource_id"], [])

    @property
    def all_job_rows(self) -> list[dict[str, str]]:
        return [row for file_rows in self.job_rows_by_file.values() for row in file_rows]

    def job(self, record_identifier: str, source_dataset: str, source_file: str, country: str) -> dict[str, str]:
        return {
            "record_id": record_identifier,
            "source_dataset": source_dataset,
            "source_file": source_file,
            "source_row_number": "1",
            "country": country,
            "title": f"Engineer {record_identifier}",
        }

    def write_reference_csv(
        self,
        file_name: str,
        field_names: list[str],
        rows: list[dict[str, str]],
    ) -> None:
        with (self.reference_directory / file_name).open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=field_names, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def read_gzip_csv(self, file_name: str) -> list[dict[str, str]]:
        with gzip.open(
            self.output_directory / file_name,
            "rt",
            encoding="utf-8",
            newline="",
        ) as input_file:
            return list(csv.DictReader(input_file))

    def test_every_arab_country_record_and_relationship_is_retained(self) -> None:
        report = builder.build_neon_free_dataset(
            self.processed_directory,
            self.reference_directory,
            self.output_directory,
            maximum_non_arab_rows_per_source_country=1,
        )
        selected_jobs = self.read_gzip_csv(builder.JOB_OUTPUT_FILE_NAME)
        selected_job_skills = self.read_gzip_csv(builder.JOB_SKILLS_OUTPUT_FILE_NAME)
        arab_record_ids = {
            row["record_id"]
            for row in self.all_job_rows
            if builder.find_arab_country(row["country"])
        }
        selected_arab_record_ids = {
            row["record_id"]
            for row in selected_jobs
            if builder.find_arab_country(row["country"])
        }
        selected_arab_skill_ids = {
            row["record_id"]
            for row in selected_job_skills
            if row["record_id"] in arab_record_ids
        }

        self.assertEqual(selected_arab_record_ids, arab_record_ids)
        self.assertEqual(selected_arab_skill_ids, arab_record_ids)
        self.assertEqual(len(selected_jobs), report["selection_policy"]["retained_job_rows"])
        self.assertEqual(len(selected_job_skills), report["skill_relationship_policy"]["job_skill_rows"])
        self.assertEqual(
            report["skill_relationship_policy"]["arab_job_skill_rows"],
            sum(1 for row in selected_job_skills if row["record_id"] in arab_record_ids),
        )
        self.assertEqual(report["selection_policy"]["arab_job_rows_dropped"], 0)
        self.assertEqual(report["selection_policy"]["retained_arab_job_rows"], len(arab_record_ids))
        self.assertLess(
            report["database_storage_estimate"]["estimated_database_size_bytes"],
            builder.DEFAULT_DATABASE_SIZE_GUARD_BYTES,
        )

    def test_non_arab_sample_is_capped_per_source_and_country(self) -> None:
        report = builder.build_neon_free_dataset(
            self.processed_directory,
            self.reference_directory,
            self.output_directory,
            maximum_non_arab_rows_per_source_country=1,
        )
        strata = report["selection_policy"]["non_arab_strata"]
        self.assertTrue(strata)
        self.assertTrue(all(stratum["retained_rows"] <= 1 for stratum in strata))
        self.assertEqual(len(strata), report["selection_policy"]["non_arab_strata_count"])
        self.assertEqual(
            report["selection_policy"]["retained_non_arab_job_rows"],
            sum(stratum["retained_rows"] for stratum in strata),
        )

    def test_unclassified_geography_rows_are_retained_in_full(self) -> None:
        report = builder.build_neon_free_dataset(
            self.processed_directory,
            self.reference_directory,
            self.output_directory,
            maximum_non_arab_rows_per_source_country=1,
        )
        selected_record_ids = {
            row["record_id"]
            for row in self.read_gzip_csv(builder.JOB_OUTPUT_FILE_NAME)
        }
        expected_unclassified_ids = {
            "country-blank",
            "country-unknown",
            "remote-one",
            "worldwide-one",
        }
        self.assertTrue(expected_unclassified_ids.issubset(selected_record_ids))
        self.assertEqual(
            report["selection_policy"]["retained_unclassified_geography_rows"],
            len(expected_unclassified_ids),
        )

    def test_selected_job_skills_regenerate_subset_observations(self) -> None:
        builder.build_neon_free_dataset(
            self.processed_directory,
            self.reference_directory,
            self.output_directory,
            maximum_non_arab_rows_per_source_country=1,
        )
        observations = self.read_gzip_csv(builder.SKILL_OBSERVATIONS_OUTPUT_FILE_NAME)
        jobs = self.read_gzip_csv(builder.JOB_OUTPUT_FILE_NAME)
        self.assertEqual(sum(int(row["occurrence_count"]) for row in observations), len(jobs))
        self.assertTrue(all(row["skill_normalized"] == "python" for row in observations))

    def test_sampling_is_deterministic_and_does_not_modify_input_exports(self) -> None:
        initial_input_bytes = {
            path.name: path.read_bytes()
            for path in self.processed_directory.iterdir()
        }
        builder.build_neon_free_dataset(
            self.processed_directory,
            self.reference_directory,
            self.output_directory,
            maximum_non_arab_rows_per_source_country=1,
        )
        initial_output_bytes = {
            path.name: path.read_bytes()
            for path in self.output_directory.iterdir()
            if path.is_file()
        }
        builder.build_neon_free_dataset(
            self.processed_directory,
            self.reference_directory,
            self.output_directory,
            maximum_non_arab_rows_per_source_country=1,
        )
        repeated_output_bytes = {
            path.name: path.read_bytes()
            for path in self.output_directory.iterdir()
            if path.is_file()
        }
        self.assertEqual(initial_output_bytes, repeated_output_bytes)
        self.assertEqual(
            initial_input_bytes,
            {path.name: path.read_bytes() for path in self.processed_directory.iterdir()},
        )

    def test_country_aliases_cover_all_arab_league_members(self) -> None:
        for country_name in builder.ARAB_COUNTRY_CANONICAL_NAMES:
            with self.subTest(country=country_name):
                self.assertEqual(builder.find_arab_country(country_name), country_name)
        self.assertEqual(builder.find_arab_country("U.A.E."), "United Arab Emirates")
        self.assertEqual(builder.find_arab_country("Egypt / United States"), "Egypt")

    def test_quality_report_is_valid_json_and_names_its_outputs(self) -> None:
        report = builder.build_neon_free_dataset(
            self.processed_directory,
            self.reference_directory,
            self.output_directory,
            maximum_non_arab_rows_per_source_country=1,
        )
        report_path = self.output_directory / builder.QUALITY_REPORT_FILE_NAME
        stored_report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(stored_report, report)
        self.assertEqual(
            set(stored_report["outputs"]),
            {"jobs", "job_skills", "skill_observations"},
        )

    def test_non_positive_sample_cap_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive integer"):
            builder.build_neon_free_dataset(
                self.processed_directory,
                self.reference_directory,
                self.output_directory,
                maximum_non_arab_rows_per_source_country=0,
            )


if __name__ == "__main__":
    unittest.main()
