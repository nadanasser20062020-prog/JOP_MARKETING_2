from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT_DIRECTORY / "scripts" / "data_cleaning"))

import build_site_data as builder


class SkillParsingTests(unittest.TestCase):
    def test_international_python_list_is_parsed_and_deduplicated(self) -> None:
        self.assertEqual(
            builder.split_skill_labels("['Python', 'SQL', 'Python']", builder.INTERNATIONAL_JOB_SOURCE_FILE),
            ["Python", "SQL"],
        )

    def test_merged_workbook_mixed_delimiters_are_split(self) -> None:
        self.assertEqual(
            builder.split_skill_labels(
                "Java, CI/CD; Python; Java; Go; Node.js; SQL", builder.MERGED_EXCEL_WORKBOOK_SOURCE_FILE
            ),
            ["Java", "CI/CD", "Python", "Go", "Node.js", "SQL"],
        )

    def test_source_specific_delimiters_are_respected(self) -> None:
        self.assertEqual(
            builder.split_skill_labels("Python; SQL; Communication", builder.ARAB_TECH_SOURCE_FILE),
            ["Python", "SQL", "Communication"],
        )
        self.assertEqual(
            builder.split_skill_labels(
                "Python, SQL, Python", "remote_tech_jobs_foreign_after_adding_skills.csv"
            ),
            ["Python", "SQL"],
        )

    def test_duplicate_tokens_can_be_counted_before_removal(self) -> None:
        raw = builder.split_skill_labels(
            "Python; Python; SQL", builder.MERGED_EXCEL_WORKBOOK_SOURCE_FILE, deduplicate=False
        )
        self.assertEqual(raw, ["Python", "Python", "SQL"])
        self.assertEqual(len(raw) - len(builder.ordered_unique_skills(raw)), 1)


class SkillReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.aliases = builder.load_skill_aliases(PROJECT_ROOT_DIRECTORY / "data" / "reference" / "skill_curation.json")

    def test_curated_aliases_resolve_to_canonical_skill(self) -> None:
        self.assertEqual(
            builder.resolve_skill_metadata("postgres", self.aliases)["skill_id"],
            "skill:postgresql",
        )
        self.assertEqual(
            builder.resolve_skill_metadata("Python 3", self.aliases)["skill_id"],
            "skill:python",
        )

    def test_ambiguous_tokens_are_not_eligible_for_matching(self) -> None:
        for token in ("can", "flow", "word"):
            metadata = builder.resolve_skill_metadata(token, self.aliases)
            self.assertEqual(metadata["match_policy"], "exclude_pending_review")

    def test_unknown_terms_are_exact_only_and_ids_are_stable(self) -> None:
        first = builder.resolve_skill_metadata("Novel Tool", self.aliases)
        second = builder.resolve_skill_metadata(" novel   tool ", self.aliases)
        self.assertEqual(first, second)
        self.assertEqual(first["match_policy"], "exact_only")
        self.assertEqual(first["review_status"], "needs_review")


class ProvenanceAndIdentityTests(unittest.TestCase):
    def test_skill_provenance_compares_canonical_skills_with_base_export(self) -> None:
        record = {"skills_source": "after_adding_skills_without_row_level_provenance"}
        aliases = builder.load_skill_aliases(PROJECT_ROOT_DIRECTORY / "data" / "reference" / "skill_curation.json")
        baseline = {builder.resolve_skill_metadata("Python", aliases)["skill_id"]}
        self.assertEqual(
            builder.skill_provenance_status(record, "Python 3", baseline, aliases),
            "present_in_base_export",
        )
        self.assertEqual(
            builder.skill_provenance_status(record, "SQL", baseline, aliases),
            "added_in_enriched_export_provenance_unverified",
        )

    def test_record_ids_are_unique_for_duplicate_source_rows(self) -> None:
        row = {"id": "same-source-id", "title": "Engineer", "skills": "Python, SQL"}
        first = builder.build_record(row, "sample.csv", "sample", "snapshot", 1)
        second = builder.build_record(row, "sample.csv", "sample", "snapshot", 2)
        self.assertNotEqual(first["record_id"], second["record_id"])
        self.assertEqual(first["listing_status"], "unknown_not_verified")

    def test_salary_provenance_does_not_report_an_estimate_when_amount_is_missing(self) -> None:
        row = {"title": "Analyst", "salary_source": "Paylab market range; research"}
        record = builder.build_record(row, "sample.csv", "sample", "snapshot", 1)
        self.assertEqual(record["salary_provenance_status"], "not_available")

    def test_salary_estimate_is_flagged_only_when_value_is_present(self) -> None:
        row = {"title": "Analyst", "salary": "1000 EGP monthly", "salary_source": "Paylab market range"}
        record = builder.build_record(row, "sample.csv", "sample", "snapshot", 1)
        self.assertEqual(record["salary_provenance_status"], "estimate_or_research_indicated")

    def test_nondisclosure_text_is_not_counted_as_a_salary_amount(self) -> None:
        self.assertFalse(builder.contains_numeric_salary_amount("Not disclosed"))
        self.assertFalse(builder.contains_numeric_salary_amount("Salary compensation in EUR (amount not disclosed)"))
        self.assertTrue(builder.contains_numeric_salary_amount("13,880 - 63,797 EGP / monthly"))
        record = builder.build_record(
            {"title": "Security Engineer", "salary": "Not disclosed"},
            "sample.csv",
            "sample",
            "snapshot",
            1,
        )
        self.assertEqual(record["salary_raw"], "Not disclosed")
        self.assertEqual(record["salary_provenance_status"], "not_available")
        self.assertIn("missing_salary", record["data_quality_flags"])


if __name__ == "__main__":
    unittest.main()
