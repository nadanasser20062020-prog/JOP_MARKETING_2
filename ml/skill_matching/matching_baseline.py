from __future__ import annotations

from typing import Iterable, Mapping

MAXIMUM_USER_SKILL_COUNT = 50


def calculate_skill_profile_overlap(
    user_skill_ids: Iterable[str],
    candidate_skill_ids: Iterable[str],
) -> dict[str, object]:
    normalized_user_skill_ids = frozenset(
        skill_identifier.strip()
        for skill_identifier in user_skill_ids
        if isinstance(skill_identifier, str) and skill_identifier.strip()
    )
    normalized_candidate_skill_ids = frozenset(
        skill_identifier.strip()
        for skill_identifier in candidate_skill_ids
        if isinstance(skill_identifier, str) and skill_identifier.strip()
    )
    if len(normalized_user_skill_ids) > MAXIMUM_USER_SKILL_COUNT:
        raise ValueError(f"At most {MAXIMUM_USER_SKILL_COUNT} unique user skills are supported.")

    matched_skill_ids = normalized_user_skill_ids.intersection(normalized_candidate_skill_ids)
    user_only_skill_ids = normalized_user_skill_ids.difference(normalized_candidate_skill_ids)
    candidate_only_skill_ids = normalized_candidate_skill_ids.difference(normalized_user_skill_ids)
    union_skill_count = len(normalized_user_skill_ids.union(normalized_candidate_skill_ids))
    jaccard_score = len(matched_skill_ids) / union_skill_count if union_skill_count else 0.0
    user_skill_coverage = (
        len(matched_skill_ids) / len(normalized_user_skill_ids)
        if normalized_user_skill_ids
        else 0.0
    )
    candidate_skill_coverage = (
        len(matched_skill_ids) / len(normalized_candidate_skill_ids)
        if normalized_candidate_skill_ids
        else 0.0
    )
    return {
        "score_name": "jaccard_skill_overlap",
        "score": jaccard_score,
        "score_percent": round(100.0 * jaccard_score, 2),
        "matched_skill_ids": sorted(matched_skill_ids),
        "user_only_skill_ids": sorted(user_only_skill_ids),
        "candidate_only_skill_ids": sorted(candidate_only_skill_ids),
        "user_skill_coverage": user_skill_coverage,
        "candidate_skill_coverage": candidate_skill_coverage,
        "user_skill_count": len(normalized_user_skill_ids),
        "candidate_skill_count": len(normalized_candidate_skill_ids),
        "matched_skill_count": len(matched_skill_ids),
        "interpretation": "Skill overlap only; not a hiring probability or a complete suitability assessment.",
    }


def rank_skill_profiles(
    user_skill_ids: Iterable[str],
    candidate_skill_profiles: Iterable[Mapping[str, object]],
) -> list[dict[str, object]]:
    normalized_user_skill_ids = frozenset(
        skill_identifier.strip()
        for skill_identifier in user_skill_ids
        if isinstance(skill_identifier, str) and skill_identifier.strip()
    )
    if len(normalized_user_skill_ids) > MAXIMUM_USER_SKILL_COUNT:
        raise ValueError(f"At most {MAXIMUM_USER_SKILL_COUNT} unique user skills are supported.")

    ranked_profiles = []
    for candidate_profile in candidate_skill_profiles:
        candidate_identifier = candidate_profile.get("candidate_id")
        candidate_skill_ids = candidate_profile.get("skill_ids", ())
        if not isinstance(candidate_identifier, str) or not candidate_identifier.strip():
            raise ValueError("Every candidate profile must have a non-empty string candidate_id.")
        if isinstance(candidate_skill_ids, str) or not isinstance(candidate_skill_ids, Iterable):
            raise ValueError(f"Candidate {candidate_identifier!r} must provide an iterable of skill IDs.")
        overlap_result = calculate_skill_profile_overlap(
            normalized_user_skill_ids,
            candidate_skill_ids,
        )
        ranked_profiles.append(
            {
                "candidate_id": candidate_identifier,
                **overlap_result,
            }
        )
    return sorted(
        ranked_profiles,
        key=lambda profile: (
            -float(profile["score"]),
            -int(profile["matched_skill_count"]),
            str(profile["candidate_id"]).casefold(),
        ),
    )
