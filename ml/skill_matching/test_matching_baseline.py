from __future__ import annotations

import unittest

from ml.skill_matching.matching_baseline import (
    MAXIMUM_USER_SKILL_COUNT,
    calculate_skill_profile_overlap,
    rank_skill_profiles,
)


class SkillProfileOverlapTests(unittest.TestCase):
    def test_calculates_intersection_over_union_and_directional_coverage(self) -> None:
        result = calculate_skill_profile_overlap(
            ["skill_python", "skill_sql", "skill_python"],
            ["skill_sql", "skill_spark"],
        )

        self.assertEqual(result["matched_skill_ids"], ["skill_sql"])
        self.assertEqual(result["user_only_skill_ids"], ["skill_python"])
        self.assertEqual(result["candidate_only_skill_ids"], ["skill_spark"])
        self.assertAlmostEqual(result["score"], 1 / 3)
        self.assertAlmostEqual(result["user_skill_coverage"], 1 / 2)
        self.assertAlmostEqual(result["candidate_skill_coverage"], 1 / 2)

    def test_empty_profiles_return_zero_without_division_by_zero(self) -> None:
        result = calculate_skill_profile_overlap([], [])

        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["matched_skill_count"], 0)

    def test_rejects_more_than_configured_user_skill_limit(self) -> None:
        user_skill_ids = [f"skill_{index}" for index in range(MAXIMUM_USER_SKILL_COUNT + 1)]

        with self.assertRaises(ValueError):
            calculate_skill_profile_overlap(user_skill_ids, [])

    def test_candidate_ranking_is_deterministic_and_breaks_ties_by_identifier(self) -> None:
        profiles = [
            {"candidate_id": "job-z", "skill_ids": ["skill_python"]},
            {"candidate_id": "job-a", "skill_ids": ["skill_python"]},
            {"candidate_id": "job-b", "skill_ids": ["skill_sql"]},
        ]

        ranked_profiles = rank_skill_profiles(["skill_python"], profiles)

        self.assertEqual(
            [profile["candidate_id"] for profile in ranked_profiles],
            ["job-a", "job-z", "job-b"],
        )

    def test_rejects_candidate_with_invalid_identifier(self) -> None:
        with self.assertRaises(ValueError):
            rank_skill_profiles(["skill_python"], [{"candidate_id": "", "skill_ids": []}])

    def test_rejects_candidate_skill_string_instead_of_collection(self) -> None:
        with self.assertRaises(ValueError):
            rank_skill_profiles(
                ["skill_python"],
                [{"candidate_id": "job-1", "skill_ids": "skill_python"}],
            )


if __name__ == "__main__":
    unittest.main()
