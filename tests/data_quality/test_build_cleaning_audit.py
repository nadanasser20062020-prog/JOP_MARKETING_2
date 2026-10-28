from __future__ import annotations

import csv
import gzip
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "data_cleaning"))

import build_cleaning_audit as cleaner


class CountryAndDateNormalizationTests(unittest.TestCase):
    def test_country_aliases_are_explicit_and_unknown_values_are_preserved(self) -> None:
        self.assertEqual(cleaner.country_standardized(" U.S.A. "), "United States")
        self.assertEqual(cleaner.country_standardized("UAE"), "United Arab Emirates")
        self.assertEqual(cleaner.country_standardized("Remote (Anywhere)"), "Remote (Anywhere)")
        self.assertEqual(cleaner.country_standardized("Freedonia"), "Freedonia")
        self.assertEqual(cleaner.country_location_scope("Worldwide"), "geographic_scope_not_country")

    def test_epoch_iso_excel_and_rfc_dates_parse_without_promoting_updated(self) -> None:
        self.assertEqual(cleaner.parse_source_datetime("1792009953").date().isoformat(), "2026-10-14")
        self.assertEqual(cleaner.parse_source_datetime("1970-01-21").date().isoformat(), "1970-01-21")
        self.assertEqual(cleaner.parse_source_datetime("2026-10-15T00:00:00.0000000").date().isoformat(), "2026-10-15")
        self.assertEqual(cleaner.parse_source_datetime("Tue, 22 Sep 2026 22:52:13 GMT").date().isoformat(), "2026-09-22")
        fields = cleaner._date_fields({"updated": "2026-10-15"}, date(2026, 10, 28))
        self.assertEqual(fields["posted_at_iso"], "")
        self.assertIn("updated_not_used_as_posting_date", fields["date_quality_flags"])

    def test_experience_years_are_parsed_only_when_explicit(self) -> None:
        self.assertEqual(cleaner.parse_experience_years("3-5 Yrs of Exp"), ("3", "5", "explicit_range"))
        self.assertEqual(cleaner.parse_experience_years("8+ Years"), ("8", "", "explicit_lower_bound_only"))
        self.assertEqual(cleaner.parse_experience_years("Experienced"), ("", "", "not_parseable_as_years"))


class SalaryParsingTests(unittest.TestCase):
    def test_european_thousands_and_annual_period_parse(self) -> None:
        parsed = cleaner.parse_salary_text("€70.000 – €85.000 per year")
        self.assertEqual(parsed["amounts"], [70000.0, 85000.0])
        self.assertEqual(cleaner.detect_currency("", "€70.000 – €85.000 per year"), ("EUR", "explicit_text"))
        self.assertEqual(cleaner.detect_period("€70.000 – €85.000 per year", [], ""), ("YEAR", "explicit_in_salary_text"))

    def test_k_shorthand_and_ambiguous_dollar_are_not_overinterpreted(self) -> None:
        parsed = cleaner.parse_salary_text("$90k - $130k")
        self.assertEqual(parsed["amounts"], [90000.0, 130000.0])
        self.assertEqual(cleaner.detect_currency("", "$90k - $130k"), ("", "ambiguous_currency_symbol"))
        self.assertEqual(cleaner.detect_period("$90k - $130k", [], ""), ("UNKNOWN", "period_not_stated"))

    def test_space_grouped_thousands_are_not_misread_as_a_salary_range(self) -> None:
        text = "68 880 zł per year"
        parsed = cleaner.parse_salary_text(text)
        self.assertEqual(parsed["amounts"], [68880.0])
        self.assertEqual(parsed["range_kind"], "point")
        self.assertEqual(cleaner.detect_currency("", text), ("PLN", "explicit_text"))
        fields = cleaner._build_salary_fields(
            {"salary": text},
            "startup_jobs",
            cleaner.STARTUP_ENRICHED,
            cleaner._load_salary_policy(None),
        )
        self.assertEqual(fields["salary_amount_1_original_currency"], "68880")
        self.assertEqual(fields["salary_currency_code"], "PLN")
        self.assertEqual(fields["salary_period_code"], "YEAR")
        self.assertEqual(fields["salary_statistics_eligible"], "yes")

    def test_arabic_month_marker_and_explicit_currency_column(self) -> None:
        parsed = cleaner.parse_salary_text("4,000/شهرياً")
        self.assertEqual(parsed["amounts"], [4000.0])
        self.assertEqual(cleaner.detect_currency("EGP", "4,000/شهرياً"), ("EGP", "explicit_source_column"))
        self.assertEqual(cleaner.detect_period("4,000/شهرياً", [], ""), ("MONTH", "explicit_in_salary_text"))

    def test_conflicting_currency_column_and_text_is_flagged(self) -> None:
        self.assertEqual(
            cleaner.detect_currency("EGP", "2,500 - 3,000 ريال سعودي / month"),
            ("", "conflict_between_source_column_and_salary_text"),
        )

    def test_non_disclosure_is_not_a_numeric_salary(self) -> None:
        parsed = cleaner.parse_salary_text("Salary compensation in EUR (amount not disclosed)")
        self.assertEqual(parsed["amounts"], [])
        self.assertTrue(cleaner._disclosure_only("Not disclosed"))
        self.assertFalse(cleaner._disclosure_only("14,000 SAR per month"))

    def test_ranges_with_more_than_two_amounts_require_review(self) -> None:
        parsed = cleaner.parse_salary_text("10000 - 15000 plus 2000 bonus")
        self.assertEqual(parsed["status"], "multiple_numeric_tokens_review")
        self.assertEqual(parsed["amounts"], [])

    def test_extreme_annual_value_is_flagged_for_review_not_removed(self) -> None:
        fields = cleaner._build_salary_fields(
            {"salary": "30 - 36 USD per year"},
            "remote_tech_jobs",
            cleaner.REMOTE_ENRICHED,
            cleaner._load_salary_policy(None),
        )
        self.assertIn("salary_below_broad_period_screening_floor_review_only", fields["salary_integrity_flags"])
        self.assertEqual(fields["salary_value_type"], "actual_reported")
        self.assertEqual(fields["salary_statistics_eligible"], "no")

    def test_annualization_requires_explicit_period_policy(self) -> None:
        self.assertEqual(cleaner.parse_salary_text("12,000 EGP per month")["amounts"], [12000.0])
        empty_policy = cleaner._load_salary_policy(None)
        record = cleaner._build_salary_fields(
            {"salary": "12,000 EGP per month"},
            "remote_tech_jobs",
            cleaner.REMOTE_ENRICHED,
            empty_policy,
        )
        self.assertEqual(record["salary_annualized_min_native"], "")
        self.assertEqual(record["salary_annualized_min_reporting_currency"], "")

    def test_legacy_estimate_is_not_classed_as_actual(self) -> None:
        category, _ = cleaner._salary_value_class(
            "arab_tech_jobs",
            "salary_range_est",
            "10,000-24,000 EGP/month",
            "",
            "sourced",
            "Paylab salary guide",
            "",
            "benchmark from web search",
            [10000.0, 24000.0],
        )
        self.assertEqual(category, "estimated_legacy_unverified")


class LossPreservingPipelineTests(unittest.TestCase):
    def test_duplicate_rows_are_retained_and_raw_values_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            raw_dir = root / "raw"
            output_dir = root / "processed"
            report_dir = root / "reports"
            raw_dir.mkdir()
            enriched_name = cleaner.REMOTE_ENRICHED
            base_name = cleaner.BASE_EXPORTS[enriched_name]
            rows = [
                {
                    "id": "job-1",
                    "title": "  Software Engineer  ",
                    "company": "Example Co",
                    "country": "USA",
                    "salary": "USD 100,000 - 120,000 per year",
                    "skills": "Python, SQL, Python",
                    "source": "Test board",
                    "updated": "2026-10-15",
                    "link": "https://example.test/jobs/1",
                },
                {
                    "id": "job-2",
                    "title": "Data Engineer",
                    "company": "Example Co",
                    "country": "Canada",
                    "salary": "$90k - $110k",
                    "skills": "Python, SQL",
                    "source": "Test board",
                    "updated": "2026-10-15",
                    "link": "https://example.test/jobs/2",
                },
            ]
            with (raw_dir / enriched_name).open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows + [rows[0]])
            with (raw_dir / base_name).open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["id", "skills"])
                writer.writeheader()
                writer.writerows([{"id": row["id"], "skills": row["skills"]} for row in rows])

            dataset_path = output_dir / "jobs.csv.gz"
            summary = cleaner.run_pipeline(
                raw_dir,
                dataset_path,
                report_dir,
                source_ref="unit-test",
                as_of_date=date(2026, 10, 28),
                notebook_path=report_dir / "cleaning_data_audit.ipynb",
            )

            self.assertEqual(summary["input_rows"], 3)
            self.assertEqual(summary["output_rows"], 3)
            self.assertEqual(summary["rows_dropped"], 0)
            self.assertEqual(summary["exact_duplicate_occurrences_retained"], 1)
            self.assertTrue(summary["source_integrity"]["all_unchanged_during_run"])
            self.assertIn(cleaner.INTERNATIONAL_SOURCE, summary["missing_required_sources"])
            with gzip.open(dataset_path, "rt", encoding="utf-8", newline="") as handle:
                cleaned = list(csv.DictReader(handle))
            self.assertEqual(len(cleaned), 3)
            self.assertEqual(cleaned[0]["title_raw"], "  Software Engineer  ")
            self.assertEqual(cleaned[0]["title_clean"], "Software Engineer")
            self.assertEqual(cleaned[0]["country_standardized"], "United States")
            self.assertEqual(cleaned[0]["salary_raw"], rows[0]["salary"])
            self.assertEqual(cleaned[0]["skills_base_raw"], rows[0]["skills"])
            self.assertEqual(cleaned[0]["skills_enrichment_status"], "matches_base_export")
            self.assertEqual(json.loads(cleaned[0]["source_row_json"]), rows[0])
            self.assertEqual(cleaned[2]["exact_duplicate_within_source"], "yes")
            self.assertEqual(cleaned[2]["salary_iqr_outlier_flag"], "group_below_minimum_8_records")
            self.assertEqual(cleaned[1]["salary_currency_code"], "")
            self.assertEqual(cleaned[1]["salary_currency_detection_status"], "ambiguous_currency_symbol")
            self.assertEqual(cleaned[1]["salary_statistics_eligible"], "no")
            self.assertEqual(summary["sqlite_round_trip"]["status"], "passed")
            self.assertEqual(summary["salary"]["estimates_added_by_this_run"], 0)


if __name__ == "__main__":
    unittest.main()
