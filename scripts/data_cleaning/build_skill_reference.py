

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
DEFAULT_SKILL_OBSERVATIONS_FILE = PROJECT_ROOT_DIRECTORY / "data" / "processed" / "skill_observations.csv.gz"
DEFAULT_SKILL_CURATION_FILE = PROJECT_ROOT_DIRECTORY / "data" / "reference" / "skill_curation.json"
DEFAULT_REFERENCE_OUTPUT_DIRECTORY = PROJECT_ROOT_DIRECTORY / "data" / "reference"

SKILL_CATALOG_FIELD_NAMES = [
    "skill_id",
    "canonical_name",
    "category",
    "match_policy",
    "review_status",
    "observed_alias_count",
    "observed_source_count",
    "observed_job_skill_occurrences",
    "notes",
]
SKILL_ALIAS_FIELD_NAMES = [
    "alias_normalized",
    "alias_label",
    "skill_id",
    "alias_type",
    "match_policy",
    "review_status",
    "observed_source_count",
    "observed_job_skill_occurrences",
    "notes",
]


def normalize_skill_label(value: str) -> str:

    return " ".join((value or "").casefold().split())


def read_skill_observations(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Skill observations not found: {path}; run build_site_data.py first")
    skill_catalog_statistics: dict[str, dict[str, Any]] = {}
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            label = (row.get("skill_raw") or "").strip()
            key = normalize_skill_label(row.get("skill_normalized") or label)
            if not key:
                continue
            item = skill_catalog_statistics.setdefault(key, {"labels": Counter(), "sources": set(), "occurrences": 0})
            count = int(row.get("occurrence_count") or 0)
            item["labels"][label] += count
            item["sources"].add(row.get("source_dataset", ""))
            item["occurrences"] += count
    return skill_catalog_statistics


def read_skill_curation(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("skills")
    if not isinstance(entries, list):
        raise ValueError("Curation JSON must contain a 'skills' array")
    return entries


def build_skill_reference(observations_path: Path, curation_path: Path, output_directory: Path) -> tuple[int, int]:
    observed = read_skill_observations(observations_path)
    curated = read_skill_curation(curation_path)

    curated_skills_by_identifier: dict[str, dict[str, Any]] = {}
    normalized_aliases_to_skills: dict[str, tuple[dict[str, Any], str, str]] = {}
    for entry in curated:
        skill_identifier = str(entry.get("skill_id", "")).strip()
        canonical_name = str(entry.get("canonical_name", "")).strip()
        if not skill_identifier or not canonical_name:
            raise ValueError(f"Each curation entry requires skill_id and canonical_name: {entry}")
        if skill_identifier in curated_skills_by_identifier:
            raise ValueError(f"Duplicate skill_id in curation: {skill_identifier}")
        curated_skills_by_identifier[skill_identifier] = entry

        canonical_normalized_label = normalize_skill_label(canonical_name)
        values = [(canonical_name, "canonical")]
        values.extend((str(alias).strip(), "curated_alias") for alias in entry.get("aliases", []))
        seen_entry_aliases: set[str] = set()
        for label, alias_type in values:
            key = normalize_skill_label(label)
            if not key or key in seen_entry_aliases:
                continue
            seen_entry_aliases.add(key)
            other = normalized_aliases_to_skills.get(key)
            if other and other[0]["skill_id"] != skill_identifier:
                raise ValueError(
                    f"Alias collision for {label!r}: {other[0]['skill_id']} vs {skill_identifier}"
                )
            normalized_aliases_to_skills[key] = (entry, alias_type, canonical_normalized_label)

    skill_catalog_statistics_by_identifier: dict[str, dict[str, Any]] = {
        skill_identifier: {"alias_count": 0, "source_count": set(), "occurrences": 0}
        for skill_identifier in curated_skills_by_identifier
    }
    skill_alias_records: dict[str, dict[str, Any]] = {}
    for key, skill_statistics in observed.items():
        if not skill_statistics["labels"]:
            continue
        label = sorted(skill_statistics["labels"].items(), key=lambda pair: (-pair[1], pair[0].casefold()))[0][0]
        match = normalized_aliases_to_skills.get(key)
        if match:
            entry, alias_type, canonical_normalized_label = match
            skill_identifier = entry["skill_id"]
            policy = entry.get("match_policy", "exact_only")
            review_status = entry.get("review_status", "needs_review")
            notes = entry.get("notes", "")
            if key == canonical_normalized_label:
                alias_type = "canonical"
            skill_catalog_statistics_by_identifier[skill_identifier]["alias_count"] += 1
            skill_catalog_statistics_by_identifier[skill_identifier]["source_count"].update(skill_statistics["sources"])
            skill_catalog_statistics_by_identifier[skill_identifier]["occurrences"] += skill_statistics["occurrences"]
        else:
            skill_identifier = "term:" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
            policy = "exact_only"
            review_status = "needs_review"
            alias_type = "observed_unreviewed_exact"
            notes = "Observed source token; no synonym expansion. Review before category-based recommendations."
            skill_catalog_statistics_by_identifier.setdefault(skill_identifier, {"alias_count": 0, "source_count": set(), "occurrences": 0})
            skill_catalog_statistics_by_identifier[skill_identifier]["alias_count"] += 1
            skill_catalog_statistics_by_identifier[skill_identifier]["source_count"].update(skill_statistics["sources"])
            skill_catalog_statistics_by_identifier[skill_identifier]["occurrences"] += skill_statistics["occurrences"]

        skill_alias_records[key] = {
            "alias_normalized": key,
            "alias_label": label,
            "skill_id": skill_identifier,
            "alias_type": alias_type,
            "match_policy": policy,
            "review_status": review_status,
            "observed_source_count": len({source for source in skill_statistics["sources"] if source}),
            "observed_job_skill_occurrences": skill_statistics["occurrences"],
            "notes": notes,
        }


    for key, (entry, alias_type, canonical_normalized_label) in normalized_aliases_to_skills.items():
        if key in skill_alias_records:
            continue
        skill_alias_records[key] = {
            "alias_normalized": key,
            "alias_label": entry["canonical_name"] if key == canonical_normalized_label else next(
                (str(alias).strip() for alias in entry.get("aliases", []) if normalize_skill_label(str(alias)) == key),
                entry["canonical_name"],
            ),
            "skill_id": entry["skill_id"],
            "alias_type": "canonical" if key == canonical_normalized_label else alias_type,
            "match_policy": entry.get("match_policy", "exact_only"),
            "review_status": entry.get("review_status", "needs_review"),
            "observed_source_count": 0,
            "observed_job_skill_occurrences": 0,
            "notes": entry.get("notes", ""),
        }

    skill_catalog_records: list[dict[str, Any]] = []
    for skill_identifier, skill_catalog_statistics in skill_catalog_statistics_by_identifier.items():
        entry = curated_skills_by_identifier.get(skill_identifier)
        if entry:
            skill_catalog_records.append({
                "skill_id": skill_identifier,
                "canonical_name": entry["canonical_name"],
                "category": entry.get("category", "uncategorized"),
                "match_policy": entry.get("match_policy", "exact_only"),
                "review_status": entry.get("review_status", "needs_review"),
                "observed_alias_count": skill_catalog_statistics["alias_count"],
                "observed_source_count": len({source for source in skill_catalog_statistics["source_count"] if source}),
                "observed_job_skill_occurrences": skill_catalog_statistics["occurrences"],
                "notes": entry.get("notes", ""),
            })
        else:
            key = next(alias for alias, row in skill_alias_records.items() if row["skill_id"] == skill_identifier)
            label = skill_alias_records[key]["alias_label"]
            skill_catalog_records.append({
                "skill_id": skill_identifier,
                "canonical_name": label,
                "category": "uncategorized",
                "match_policy": "exact_only",
                "review_status": "needs_review",
                "observed_alias_count": skill_catalog_statistics["alias_count"],
                "observed_source_count": len({source for source in skill_catalog_statistics["source_count"] if source}),
                "observed_job_skill_occurrences": skill_catalog_statistics["occurrences"],
                "notes": "Source term kept for exact-only matching; review before broader matching or recommendations.",
            })

    output_directory.mkdir(parents=True, exist_ok=True)
    skill_catalog_file_path = output_directory / "skill_catalog.csv"
    skill_alias_file_path = output_directory / "skill_aliases.csv"
    with skill_catalog_file_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SKILL_CATALOG_FIELD_NAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(skill_catalog_records, key=lambda row: (row["category"], row["canonical_name"].casefold())))
    with skill_alias_file_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SKILL_ALIAS_FIELD_NAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(skill_alias_records.values(), key=lambda row: (row["skill_id"], row["alias_normalized"])))
    return len(skill_catalog_records), len(skill_alias_records)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the reviewed skill catalog and matching aliases")
    parser.add_argument("--skill-observations-file", dest="skill_observations_file", type=Path, default=DEFAULT_SKILL_OBSERVATIONS_FILE)
    parser.add_argument("--skill-curation-file", dest="skill_curation_file", type=Path, default=DEFAULT_SKILL_CURATION_FILE)
    parser.add_argument("--output-directory", dest="output_directory", type=Path, default=DEFAULT_REFERENCE_OUTPUT_DIRECTORY)
    command_line_arguments = parser.parse_args()
    skill_catalog_record_count, skill_alias_record_count = build_skill_reference(
        command_line_arguments.skill_observations_file.resolve(), command_line_arguments.skill_curation_file.resolve(), command_line_arguments.output_directory.resolve()
    )
    skill_catalog_file_path = command_line_arguments.output_directory.resolve() / "skill_catalog.csv"
    skill_alias_file_path = command_line_arguments.output_directory.resolve() / "skill_aliases.csv"
    print(json.dumps({
        "skill_catalog_rows": skill_catalog_record_count,
        "skill_alias_rows": skill_alias_record_count,
        "catalog_path": str(skill_catalog_file_path.relative_to(PROJECT_ROOT_DIRECTORY) if skill_catalog_file_path.is_relative_to(PROJECT_ROOT_DIRECTORY) else skill_catalog_file_path),
        "aliases_path": str(skill_alias_file_path.relative_to(PROJECT_ROOT_DIRECTORY) if skill_alias_file_path.is_relative_to(PROJECT_ROOT_DIRECTORY) else skill_alias_file_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
