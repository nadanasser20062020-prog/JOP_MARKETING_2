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
import finalize_full_cleaning_audit as finalizer


class FxPolicyTests(unittest.TestCase):
    def test_frozen_fx_policy_has_date_matched_provenance_and_consistent_targets(self) -> None:
        policy = finalizer._load_fx_policy(PROJECT_ROOT / "data" / "reference" / "fx_rates_2026-10-28.json")
        self.assertEqual(policy["fx_rate_date"], "2026-10-28")
        self.assertEqual(policy["reporting_currency"], "USD")
        self.assertEqual(policy["target_currency_rates_from_usd"], {"EGP": 56.129, "SAR": 3.75})
        self.assertIn("CHF", policy["fx_rates_to_reporting_currency"])
        self.assertAlmostEqual(policy["fx_rates_to_reporting_currency"]["KWD"], 1000 / 308.350)
        self.assertIn("Fils", policy["currency_rate_details"]["KWD"]["source_note"])
        self.assertEqual(
            set(policy["fx_rates_to_reporting_currency"]),
            set(policy["currency_rate_details"]),
        )

    def test_policy_rejects_a_target_rate_without_matching_provenance(self) -> None:
        payload = json.loads((PROJECT_ROOT / "data" / "reference" / "fx_rates_2026-10-28.json").read_text(encoding="utf-8"))
        payload["target_currency_rates_from_usd"]["EGP"] = 55.0
        with tempfile.TemporaryDirectory() as temp_name:
            path = Path(temp_name) / "fx.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inverse source-currency rate"):
                finalizer._load_fx_policy(path)


class SalaryNormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fx_policy = finalizer._load_fx_policy(PROJECT_ROOT / "data" / "reference" / "fx_rates_2026-10-28.json")

    def test_monthly_eur_salary_is_annualized_then_converted_to_usd_egp_and_sar(self) -> None:
        record = {
            "salary_parse_status": "parsed_range",
            "salary_currency_code": "EUR",
            "salary_period_code": "MONTH",
            "salary_min_original_currency": "6000",
            "salary_max_original_currency": "7000",
        }
        values = finalizer._salary_values_for_output(record, self.fx_policy)
        self.assertEqual(values["salary_annualized_min_native"], "72000")
        self.assertEqual(values["salary_annualized_max_native"], "84000")
        self.assertEqual(values["salary_annualized_midpoint_native"], "78000")
        self.assertAlmostEqual(float(values["salary_annual_salary_usd"]), 78000 * 1.1133)
        self.assertAlmostEqual(float(values["salary_annual_salary_egp"]), 78000 * 1.1133 * 56.129)
        self.assertAlmostEqual(float(values["salary_annual_salary_sar"]), 78000 * 1.1133 * 3.75)
        self.assertEqual(values["salary_fx_rate_date"], "2026-10-28")

    def test_reversed_range_is_sorted_only_in_derived_annual_bounds(self) -> None:
        record = {
            "salary_parse_status": "range_order_reversed",
            "salary_currency_code": "USD",
            "salary_period_code": "YEAR",
            "salary_amount_1_original_currency": "120000",
            "salary_amount_2_original_currency": "90000",
            "salary_min_original_currency": "120000",
            "salary_max_original_currency": "90000",
        }
        values = finalizer._salary_values_for_output(record, self.fx_policy)
        self.assertEqual(record["salary_min_original_currency"], "120000")
        self.assertEqual(record["salary_max_original_currency"], "90000")
        self.assertEqual(values["salary_annual_min_usd"], "90000")
        self.assertEqual(values["salary_annual_salary_usd"], "105000")
        self.assertEqual(values["salary_annual_max_usd"], "120000")

    def test_unknown_period_does_not_get_annualized(self) -> None:
        record = {
            "salary_parse_status": "parsed_single_amount",
            "salary_currency_code": "USD",
            "salary_period_code": "UNKNOWN",
            "salary_min_original_currency": "5000",
            "salary_max_original_currency": "5000",
        }
        values = finalizer._salary_values_for_output(record, self.fx_policy)
        self.assertEqual(values["salary_annualized_min_native"], "")
        self.assertEqual(values["salary_annual_salary_usd"], "")
        self.assertEqual(values["salary_fx_rate_to_reporting_currency"], "1")

    def test_actual_benchmark_uses_annualized_usd_actuals_only(self) -> None:
        rows = []
        for value in (100000, 120000, 140000, 160000, 180000):
            rows.append({
                "salary_value_type": "actual_reported",
                "salary_statistics_eligible": "yes",
                "salary_currency_code": "USD",
                "salary_period_code": "YEAR",
                "salary_parse_status": "parsed_single_amount",
                "salary_min_original_currency": str(value),
                "salary_max_original_currency": str(value),
                "title_clean": "Software Engineer",
                "title_key": "software engineer",
                "country_standardized": "United States",
                "location_scope": "country_label_unverified",
                "source_dataset": "fixture",
            })
        rows.append({
            "salary_value_type": "actual_reported",
            "salary_statistics_eligible": "no",
            "salary_currency_code": "USD",
            "salary_period_code": "YEAR",
            "salary_parse_status": "parsed_single_amount",
            "salary_min_original_currency": "99999999",
            "salary_max_original_currency": "99999999",
            "title_clean": "Software Engineer",
            "title_key": "software engineer",
            "country_standardized": "United States",
            "location_scope": "country_label_unverified",
            "source_dataset": "fixture",
        })
        rows.append({
            "salary_value_type": "estimated_legacy_unverified",
            "salary_currency_code": "USD",
            "salary_period_code": "YEAR",
            "salary_parse_status": "parsed_single_amount",
            "salary_min_original_currency": "9999999",
            "salary_max_original_currency": "9999999",
            "title_clean": "Software Engineer",
            "title_key": "software engineer",
            "country_standardized": "United States",
            "location_scope": "country_label_unverified",
            "source_dataset": "fixture",
        })
        with tempfile.TemporaryDirectory() as temp_name:
            path = Path(temp_name) / "jobs.csv.gz"
            fields = list(dict.fromkeys(key for row in rows for key in row))
            with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            models, summary = finalizer._build_benchmarks(path, self.fx_policy)
        target = rows[0]
        benchmark = finalizer._benchmark_for_record(target, models)
        self.assertEqual(summary["benchmark_actual_record_count"], 5)
        self.assertEqual(summary["benchmark_count_by_currency"], {"USD": 5})
        self.assertIsNotNone(benchmark)
        assert benchmark is not None
        self.assertEqual(benchmark["method"], "synthetic_exact_country_title_median")
        self.assertEqual(benchmark["reference_count"], 5)
        self.assertEqual(benchmark["median_usd"], 140000)


class FinalizationIntegrationTests(unittest.TestCase):
    def test_full_finalize_annualizes_estimates_and_keeps_raw_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            raw_dir = root / "raw"
            report_dir = root / "reports"
            raw_dir.mkdir()
            source_file = cleaner.REMOTE_ENRICHED
            base_file = cleaner.BASE_EXPORTS[source_file]
            rows = [
                {
                    "id": f"job-{index}",
                    "title": "Software Engineer",
                    "company": "Example Co",
                    "country": "United States",
                    "salary": f"USD {100000 + (index - 1) * 20000:,} per year" if index <= 5 else "",
                    "skills": "Python, SQL",
                    "source": "Test board",
                    "collected_at": "2026-10-20",
                    "link": f"https://example.test/jobs/{index}",
                }
                for index in range(1, 7)
            ]
            for filename, fieldnames, data_rows in (
                (source_file, list(rows[0]), rows),
                (base_file, ["id", "skills"], [{"id": row["id"], "skills": row["skills"]} for row in rows]),
            ):
                with (raw_dir / filename).open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data_rows)

            dataset_path = root / "processed" / "jobs.csv.gz"
            notebook_path = root / "reports" / "audit.ipynb"
            cleaner.run_pipeline(
                raw_dir,
                dataset_path,
                report_dir,
                source_ref="unit-test",
                as_of_date=date(2026, 10, 28),
                notebook_path=notebook_path,
            )
            summary = finalizer.finalize_full_audit(
                raw_dir,
                dataset_path,
                report_dir,
                source_ref="unit-test",
                as_of_date=date(2026, 10, 28),
                fx_policy_path=PROJECT_ROOT / "data" / "reference" / "fx_rates_2026-10-28.json",
                notebook_path=notebook_path,
            )

            with gzip.open(dataset_path, "rt", encoding="utf-8", newline="") as handle:
                cleaned = list(csv.DictReader(handle))
            self.assertEqual(len(cleaned), 6)
            self.assertEqual(summary["rows_dropped"], 0)
            synthetic = [row for row in cleaned if row["salary_value_type"] == "estimated_synthetic"]
            self.assertEqual(len(synthetic), 1)
            self.assertEqual(synthetic[0]["salary_estimation_status"], "Estimated")
            self.assertEqual(synthetic[0]["salary_estimate_reference_count"], "5")
            self.assertEqual(synthetic[0]["salary_estimation_method"], "synthetic_exact_country_title_median")
            self.assertEqual(synthetic[0]["salary_raw"], "")
            self.assertEqual(synthetic[0]["salary_source_value_type"], "missing")
            self.assertTrue(float(synthetic[0]["salary_annual_salary_usd"]) > 0)
            self.assertAlmostEqual(
                float(synthetic[0]["salary_annual_salary_egp"]),
                float(synthetic[0]["salary_annual_salary_usd"]) * 56.129,
                places=1,
            )
            self.assertEqual(cleaned[0]["source_collected_at_iso"], "2026-10-20T00:00:00Z")
            self.assertTrue(notebook_path.is_file())
            generated_notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
            notebook_text = "\\n".join("".join(cell.get("source", [])) for cell in generated_notebook["cells"])
            self.assertIn("stream-validated rows", notebook_text)
            self.assertIn("Restore jobs_cleaned_audited.csv.gz from Drive", notebook_text)
            self.assertNotIn("duplicate_review_candidates.csv", notebook_text)
            self.assertTrue((report_dir / "skill_alias_audit.csv").is_file())
            self.assertTrue((report_dir / "salary_model_and_fx_policy.json").is_file())
            self.assertEqual(summary["salary"]["actual_statistics_eligible_records"], 5)
            self.assertEqual(summary["salary"]["eligible_actual_records_used_for_benchmarks"], 5)
            self.assertEqual(summary["salary_policy"]["benchmark_training"]["benchmark_actual_record_count"], 5)
            with (report_dir / "field_consistency_checks.csv").open(encoding="utf-8", newline="") as handle:
                consistency_rows = list(csv.DictReader(handle))
            database_check = next(row for row in consistency_rows if row["check_name"] == "database_reconciliation")
            self.assertEqual(database_check["status"], "not_checked")
            self.assertEqual(database_check["violations"], "")
            final_report = (report_dir / "final_data_quality_report.md").read_text(encoding="utf-8")
            self.assertIn("فحص SQLite الداخلي لقراءة CSV وتجميع الرواتب: `passed`", final_report)
            self.assertIn("مطابقة قاعدة البيانات الخارجية: `not_checked`", final_report)


if __name__ == "__main__":
    unittest.main()
