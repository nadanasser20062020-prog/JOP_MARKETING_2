





from __future__ import annotations

import argparse
import ast
import csv
import gzip
import hashlib
import io
import json
import re
import sys
import zipfile
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator
import xml.etree.ElementTree as xml_element_tree

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
RAW_DATA_DIRECTORY = PROJECT_ROOT_DIRECTORY / "data" / "raw"
DEFAULT_PROCESSED_DATA_DIRECTORY = PROJECT_ROOT_DIRECTORY / "data" / "processed"
SKILL_CURATION_FILE_PATH = PROJECT_ROOT_DIRECTORY / "data" / "reference" / "skill_curation.json"
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

INTERNATIONAL_JOB_SOURCE_FILE = "International_Tech_Jobs_Filtered.csv"
MERGED_EXCEL_WORKBOOK_SOURCE_FILE = "Merged_Tech_Jobs_45k_skills_enriched_AFTER_ADDING_SKILLS.xlsx"
ARAB_TECH_SOURCE_FILE = "arab_tech_jobs_skills_enriched_AFTER_ADDING_SKILLS_439.csv"
CYBERSECURITY_JOB_SOURCE_FILE = "cybersecurity_jobs_expanded_6_columns.csv"
LATEST_JOB_EXPORTS = {
    "remote_tech_jobs_foreign_after_adding_skills.csv": (
        "remote_tech_jobs_foreign.csv", "remote_tech_jobs"
    ),
    "startup_jobs_foreign_after_adding_skills.csv": (
        "startup_jobs_foreign.csv", "startup_jobs"
    ),
    "tech_jobs_jooble_careerjet_AGNABY_after_adding_skills.csv": (
        "tech_jobs_jooble_careerjet_AGNABY.csv", "jooble_careerjet_jobs"
    ),
}

OUTPUT_FIELDS = [
    "record_id",
    "source_dataset",
    "source_file",
    "source_row_number",
    "source_record_id",
    "record_origin",
    "source_platform",
    "title",
    "title_short",
    "company",
    "country",
    "city",
    "region",
    "location_raw",
    "work_mode_raw",
    "remote_flag",
    "employment_type_raw",
    "experience_raw",
    "category_raw",
    "description",
    "posted_at",
    "source_updated_at",
    "source_date_field",
    "salary_raw",
    "salary_rate",
    "salary_year_avg",
    "salary_hour_avg",
    "salary_currency",
    "salary_basis",
    "salary_source",
    "salary_provenance_status",
    "skills",
    "skills_original",
    "skills_source",
    "skills_enrichment_status",
    "source_url",
    "listing_status",
    "snapshot_type",
    "exact_duplicate_within_source",
    "data_quality_flags",
]

SKILL_FIELDS = [
    "record_id",
    "source_dataset",
    "source_file",
    "skill_raw",
    "skill_normalized",
    "skill_id",
    "skill_category",
    "skill_match_policy",
    "skill_review_status",
    "skill_provenance",
    "skill_status",
]

EMPTY_TOKENS = {"", "null", "none", "nan", "n/a", "na", "<na>", "unknown"}


def clean_source_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def first_available_source_value(row: dict[str, Any], *names: str) -> str:
    lowered = {str(k).strip().casefold(): v for k, v in row.items()}
    for name in names:
        value = clean_source_value(lowered.get(name.casefold()))
        if value and value.casefold() not in EMPTY_TOKENS:
            return value
    return ""


def contains_source_value(value: str) -> bool:
    return bool(value.strip()) and value.strip().casefold() not in EMPTY_TOKENS


def contains_numeric_salary_amount(value: str) -> bool:

    text = clean_source_value(value)
    if not contains_source_value(text):
        return False
    folded = text.casefold()
    non_disclosure = (
        "not disclosed", "not specified", "not provided", "not available", "not mentioned",
        "not listed", "undisclosed", "confidential", "no data", "not found",
    )
    if any(phrase in folded for phrase in non_disclosure):
        return False
    return re.search(r"(?<![a-z])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", folded) is not None


@contextmanager
def open_comma_separated_values_reader(path: Path) -> Iterator[csv.DictReader]:

    if path.is_file():
        with path.open("r", encoding="utf-8-sig", errors="strict", newline="") as handle:
            yield csv.DictReader(handle, strict=True)
        return

    compressed_archive_path = path.with_suffix(".zip")
    if compressed_archive_path.is_file():
        with zipfile.ZipFile(compressed_archive_path) as archive:
            member_name = path.name
            try:
                member = archive.getinfo(member_name)
            except KeyError as exc:
                raise FileNotFoundError(
                    f"{path} is missing and {zip_path} has no {member_name!r} member"
                ) from exc
            with archive.open(member) as binary:
                with io.TextIOWrapper(binary, encoding="utf-8-sig", errors="strict", newline="") as handle:
                    yield csv.DictReader(handle, strict=True)
        return
    raise FileNotFoundError(f"Required source file not found: {path}")


def read_excel_workbook_rows(path: Path, sheet_name: str = "jobs") -> Iterator[dict[str, str]]:

    namespace_mappings = {
        "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    relationship_namespace_mappings = {"relationship": "http://schemas.openxmlformats.org/package/2006/relationships"}

    with zipfile.ZipFile(path) as archive:
        workbook = xml_element_tree.fromstring(archive.read("xl/workbook.xml"))
        relationships = xml_element_tree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationship_targets = {
            relationship_entry.attrib["Id"]: relationship_entry.attrib["Target"]
            for relationship_entry in relationships.findall("relationship:Relationship", relationship_namespace_mappings)
        }
        selected = None
        for sheet in workbook.findall("m:sheets/m:sheet", namespace_mappings):
            if sheet.attrib.get("name") == sheet_name:
                selected = sheet
                break
        if selected is None:
            raise ValueError(f"Worksheet {sheet_name!r} not found in {path.name}")

        target = relationship_targets[selected.attrib[f"{{{namespace_mappings['r']}}}id"]]
        if target.startswith("/"):
            worksheet_path = target.lstrip("/")
        else:
            worksheet_path = str(PurePosixPath("xl") / PurePosixPath(target))
            parts: list[str] = []
            for part in PurePosixPath(worksheet_path).parts:
                if part == "..":
                    if parts:
                        parts.pop()
                elif part != ".":
                    parts.append(part)
            worksheet_path = "/".join(parts)
        if worksheet_path not in archive.namelist():
            raise ValueError(f"Worksheet XML not found: {worksheet_path}")

        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            with archive.open("xl/sharedStrings.xml") as shared_file:
                for _, elem in xml_element_tree.iterparse(shared_file, events=("end",)):
                    if elem.tag.endswith("}si"):
                        shared_strings.append(
                            "".join(node.text or "" for node in elem.iter() if node.tag.endswith("}t"))
                        )
                        elem.clear()

        def column_number(reference: str) -> int:
            letters = re.match(r"[A-Z]+", reference.upper())
            if not letters:
                return 0
            result = 0
            for char in letters.group(0):
                result = result * 26 + ord(char) - ord("A") + 1
            return result

        def cell_value(cell: xml_element_tree.Element) -> str:
            cell_type = cell.attrib.get("t")
            value = cell.find("m:v", namespace_mappings)
            if cell_type == "inlineStr":
                return "".join(node.text or "" for node in cell.iter() if node.tag.endswith("}t"))
            if value is None:
                return ""
            raw = value.text or ""
            if cell_type == "s":
                try:
                    return shared_strings[int(raw)]
                except (ValueError, IndexError):
                    return ""
            return raw

        header: list[str] | None = None
        with archive.open(worksheet_path) as sheet_file:
            for _, row_element in xml_element_tree.iterparse(sheet_file, events=("end",)):
                if not row_element.tag.endswith("}row"):
                    continue
                cells: dict[int, str] = {}
                for cell in row_element:
                    if not cell.tag.endswith("}c"):
                        continue
                    index = column_number(cell.attrib.get("r", ""))
                    if index:
                        cells[index - 1] = cell_value(cell)
                width = max(cells, default=-1) + 1
                values = [""] * width
                for index, value in cells.items():
                    values[index] = value
                row_element.clear()
                if header is None:
                    header = values
                    continue
                if not any(clean_source_value(value) for value in values):
                    continue
                yield {
                    header[index]: values[index] if index < len(values) else ""
                    for index in range(len(header))
                }


def load_original_skills(path: Path) -> dict[str, str]:

    result: dict[str, str] = {}
    if not path.is_file():
        return result
    with open_comma_separated_values_reader(path) as reader:
        for row in reader:
            record_identifier = first_available_source_value(row, "id", "job_id", "row_id")
            if record_identifier:
                result[record_identifier] = first_available_source_value(row, "skills", "job_skills", "required_skills")
    return result


def normalize_skill_label(value: str) -> str:

    return re.sub(r"\s+", " ", clean_source_value(value).casefold()).strip()


def ordered_unique_skills(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        token = clean_source_value(value).strip("\"'")
        normalized = normalize_skill_label(token)
        if not contains_source_value(token) or not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(token)
    return unique


def split_skill_labels(value: str, source_file: str, *, deduplicate: bool = True) -> list[str]:

    value = clean_source_value(value)
    if not value:
        return []

    if value.startswith("["):
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, (list, tuple, set)):
                items = sorted(parsed, key=lambda item: clean_source_value(item).casefold()) if isinstance(parsed, set) else parsed
                candidates = [clean_source_value(item).strip("\"'") for item in items if contains_source_value(clean_source_value(item))]
                return ordered_unique_skills(candidates) if deduplicate else candidates
        except (ValueError, SyntaxError):
            pass

    if source_file == MERGED_EXCEL_WORKBOOK_SOURCE_FILE:
        parts = re.split(r"[;,]", value)
    else:
        separator = ";" if source_file.startswith(("arab_tech_jobs", "cybersecurity_jobs")) else ","
        parts = value.split(separator)
    candidates = [clean_source_value(part).strip("\"'") for part in parts if contains_source_value(clean_source_value(part))]
    return ordered_unique_skills(candidates) if deduplicate else candidates


def skill_provenance_status(
    record: dict[str, str],
    token: str,
    original_skill_identifiers: set[str] | None,
    skill_aliases: dict[str, dict[str, str]],
) -> str:
    if original_skill_identifiers is not None:
        canonical_skill_identifier = resolve_skill_metadata(token, skill_aliases)["skill_id"]
        if canonical_skill_identifier in original_skill_identifiers:
            return "present_in_base_export"
        return "added_in_enriched_export_provenance_unverified"

    source = record.get("skills_source", "").casefold()
    if source == "source_field_provenance_not_supplied":
        return "source_field_provenance_not_supplied"
    if source == "after_adding_skills_without_row_level_provenance":
        return "enriched_export_no_per_skill_lineage"
    if "research_added" in source or "research_filled" in source or "inferred" in source:
        return "row_level_mixed_provenance_no_per_skill_lineage"
    if "extract" in source:
        return "description_extraction_row_level_no_per_skill_lineage"
    if "original" in source:
        return "source_origin_claimed_row_level_no_per_skill_lineage"
    if source:
        return "row_level_provenance_no_per_skill_lineage"
    return "source_field_provenance_not_supplied"


def load_skill_aliases(path: Path) -> dict[str, dict[str, str]]:

    payload = json.loads(path.read_text(encoding="utf-8"))
    alias_map: dict[str, dict[str, str]] = {}
    for entry in payload.get("skills", []):
        values = [entry.get("canonical_name", ""), *entry.get("aliases", [])]
        for value in values:
            key = normalize_skill_label(str(value))
            if not key:
                continue
            existing = alias_map.get(key)
            if existing and existing["skill_id"] != entry["skill_id"]:
                raise ValueError(f"Skill alias collision in {path}: {value!r}")
            alias_map[key] = {
                "skill_id": str(entry["skill_id"]),
                "category": str(entry.get("category", "uncategorized")),
                "match_policy": str(entry.get("match_policy", "exact_only")),
                "review_status": str(entry.get("review_status", "needs_review")),
            }
    return alias_map


def resolve_skill_metadata(token: str, alias_map: dict[str, dict[str, str]]) -> dict[str, str]:
    key = normalize_skill_label(token)
    curated = alias_map.get(key)
    if curated:
        return curated
    stable_identifier = "term:" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return {
        "skill_id": stable_identifier,
        "category": "uncategorized",
        "match_policy": "exact_only",
        "review_status": "needs_review",
    }


def identify_source(filename: str) -> tuple[str, str]:
    if filename == INTERNATIONAL_JOB_SOURCE_FILE:
        return "international_jobs", "historical_2023_sample"
    if filename == MERGED_EXCEL_WORKBOOK_SOURCE_FILE:
        return "merged_tech_jobs", "merged_source_snapshot_date_semantics_unverified"
    if filename == ARAB_TECH_SOURCE_FILE:
        return "arab_tech_jobs", "regional_snapshot_date_coverage_partial"
    if filename == CYBERSECURITY_JOB_SOURCE_FILE:
        return "cybersecurity_jobs", "regional_snapshot_date_unavailable"
    for enriched_name, (_, source_identifier) in LATEST_JOB_EXPORTS.items():
        if filename == enriched_name:
            return source_identifier, "recent_export_listing_status_unverified"
    raise ValueError(f"No source mapping is defined for {filename}")


def build_record(
    row: dict[str, Any],
    source_file: str,
    source_dataset: str,
    snapshot_type: str,
    row_number: int,
    original_skills: dict[str, str] | None = None,
) -> dict[str, str]:
    source_record_identifier = first_available_source_value(row, "id", "job_id", "row_id")
    title = first_available_source_value(row, "title", "job_title")
    title_short = first_available_source_value(row, "job_title_short")
    if not title:
        title = title_short

    raw_skills = first_available_source_value(row, "skills", "job_skills", "required_skills")
    source_identifier = source_record_identifier or f"row-{row_number}"
    row_material = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    row_digest = hashlib.sha256(row_material.encode("utf-8")).hexdigest()[:16]
    record_identifier = f"{source_dataset}:{source_identifier}:row-{row_number}:{row_digest}"

    original_skill_value = raw_skills
    enrichment_status = "not_compared"
    if original_skills is not None:
        if source_record_identifier and source_record_identifier in original_skills:
            original_skill_value = original_skills[source_record_identifier]
            enrichment_status = "matches_source_version" if original_skill_value == raw_skills else "changed_source_version_unverified"
        else:
            original_skill_value = ""
            enrichment_status = "base_row_not_found_or_id_missing"

    explicit_skill_source = first_available_source_value(row, "skills_source")
    if explicit_skill_source:
        skill_source = explicit_skill_source
    elif enrichment_status == "changed_source_version_unverified":
        skill_source = "after_adding_skills_without_row_level_provenance"
    else:
        skill_source = "source_field_provenance_not_supplied"

    posted_at = first_available_source_value(row, "posted_at", "job_posted_date", "date_posted")
    source_updated_at = first_available_source_value(row, "updated", "source_updated_at")
    if posted_at:
        source_date_field = "posted_at_or_job_posted_date"
    elif source_updated_at:
        source_date_field = "updated_semantics_unverified"
    else:
        source_date_field = "not_available"

    remote_flag = first_available_source_value(row, "job_work_from_home")
    work_mode_raw = first_available_source_value(row, "work_mode", "work_arrangement")
    if not work_mode_raw and remote_flag:
        work_mode_raw = f"job_work_from_home={remote_flag}"

    salary_raw = first_available_source_value(row, "salary", "salary_raw")
    salary_source = first_available_source_value(row, "salary_source", "salary_fill_source", "salary_sources")
    salary_basis = first_available_source_value(row, "salary_basis", "salary_period", "salary_rate")
    salary_note = (salary_source + " " + salary_basis + " " + salary_raw).casefold()
    salary_value_present = any(
        contains_numeric_salary_amount(value)
        for value in (
            salary_raw,
            first_available_source_value(row, "salary_year_avg"),
            first_available_source_value(row, "salary_hour_avg"),
        )
    )
    if not salary_value_present:
        salary_provenance_status = "not_available"
    elif any(term in salary_note for term in (
        "research", "benchmark", "estimate", "inference", "estimated", "market range", "paylab", "verified respondents"
    )):
        salary_provenance_status = "estimate_or_research_indicated"
    else:
        salary_provenance_status = "source_or_origin_unverified"

    description = first_available_source_value(row, "description", "job_description", "description_text")
    source_url = first_available_source_value(row, "link", "apply_url", "source_url", "job_url")
    country = first_available_source_value(row, "country", "job_country")
    company = first_available_source_value(row, "company", "company_name")
    platform = first_available_source_value(row, "source", "platform", "job_via")
    if platform.startswith("via "):
        platform = platform[4:]

    flags: list[str] = []
    for field_name, value in (
        ("missing_title", title),
        ("missing_company", company),
        ("missing_country", country),
        ("missing_description", description),
        ("missing_source_url", source_url),
        ("missing_skills", raw_skills),
        ("missing_source_record_id", source_record_identifier),
    ):
        if not contains_source_value(value):
            flags.append(field_name)
    if not any(
        contains_numeric_salary_amount(value)
        for value in (salary_raw, first_available_source_value(row, "salary_year_avg"), first_available_source_value(row, "salary_hour_avg"))
    ):
        flags.append("missing_salary")
    if not posted_at and source_updated_at:
        flags.append("updated_field_not_confirmed_as_posting_date")
    if not posted_at and not source_updated_at:
        flags.append("missing_posted_or_updated_date")
    if enrichment_status in {"changed_source_version_unverified", "base_row_not_found_or_id_missing"}:
        flags.append("skills_enrichment_provenance_missing")
    if salary_provenance_status == "estimate_or_research_indicated":
        flags.append("salary_is_estimate_or_research_based")
    flags.append("listing_active_status_unverified")

    return {
        "record_id": record_identifier,
        "source_dataset": source_dataset,
        "source_file": source_file,
        "source_row_number": str(row_number),
        "source_record_id": source_record_identifier,
        "record_origin": first_available_source_value(row, "record_origin", "source_file"),
        "source_platform": platform,
        "title": title,
        "title_short": title_short,
        "company": company,
        "country": country,
        "city": first_available_source_value(row, "city"),
        "region": first_available_source_value(row, "state_region", "region", "state"),
        "location_raw": first_available_source_value(row, "location_raw", "job_location", "job_location_raw"),
        "work_mode_raw": work_mode_raw,
        "remote_flag": remote_flag,
        "employment_type_raw": first_available_source_value(row, "job_type", "job_schedule_type", "employment_type"),
        "experience_raw": first_available_source_value(row, "level", "years_experience", "experience"),
        "category_raw": first_available_source_value(row, "category", "job_category", "sub_category", "job_track"),
        "description": description,
        "posted_at": posted_at,
        "source_updated_at": source_updated_at,
        "source_date_field": source_date_field,
        "salary_raw": salary_raw,
        "salary_rate": first_available_source_value(row, "salary_rate"),
        "salary_year_avg": first_available_source_value(row, "salary_year_avg"),
        "salary_hour_avg": first_available_source_value(row, "salary_hour_avg"),
        "salary_currency": first_available_source_value(row, "salary_currency", "currency"),
        "salary_basis": salary_basis,
        "salary_source": salary_source,
        "salary_provenance_status": salary_provenance_status,
        "skills": raw_skills,
        "skills_original": original_skill_value,
        "skills_source": skill_source,
        "skills_enrichment_status": enrichment_status,
        "source_url": source_url,
        "listing_status": "unknown_not_verified",
        "snapshot_type": snapshot_type,
        "exact_duplicate_within_source": "pending_exact_row_check",
        "data_quality_flags": ";".join(flags),
    }


def exact_row_digest(row: dict[str, Any]) -> bytes:
    return hashlib.blake2b(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        digest_size=16,
    ).digest()


def write_compressed_csv(path: Path, fields: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = gzip.open(path, "wt", encoding="utf-8", newline="", compresslevel=6)
    writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    return handle, writer


def source_specs() -> list[tuple[str, Path, str, str, bool]]:
    specs: list[tuple[str, Path, str, str, bool]] = []
    specs.append((INTERNATIONAL_JOB_SOURCE_FILE, RAW_DATA_DIRECTORY / INTERNATIONAL_JOB_SOURCE_FILE, "historical_sample", "international_jobs", False))
    specs.append((MERGED_EXCEL_WORKBOOK_SOURCE_FILE, RAW_DATA_DIRECTORY / MERGED_EXCEL_WORKBOOK_SOURCE_FILE, "other_snapshot", "merged_tech_jobs", True))
    specs.append((ARAB_TECH_SOURCE_FILE, RAW_DATA_DIRECTORY / ARAB_TECH_SOURCE_FILE, "other_snapshot", "arab_tech_jobs", False))
    specs.append((CYBERSECURITY_JOB_SOURCE_FILE, RAW_DATA_DIRECTORY / CYBERSECURITY_JOB_SOURCE_FILE, "other_snapshot", "cybersecurity_jobs", False))
    for enriched_name, (_, source_identifier) in LATEST_JOB_EXPORTS.items():
        specs.append((enriched_name, RAW_DATA_DIRECTORY / enriched_name, "latest_export", source_identifier, False))
    return specs


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean available job data and prepare normalized site datasets")
    parser.add_argument("--raw-data-directory", dest="raw_data_directory", type=Path, default=RAW_DATA_DIRECTORY, help="Directory containing unchanged source files")
    parser.add_argument("--output-directory", dest="output_directory", type=Path, default=DEFAULT_PROCESSED_DATA_DIRECTORY, help="Directory for generated data files")
    parser.add_argument("--skill-curation-file", dest="skill_curation_file_path", type=Path, default=SKILL_CURATION_FILE_PATH, help="Reviewed skill identifiers and aliases JSON file")
    command_line_arguments = parser.parse_args()
    raw_data_directory = command_line_arguments.raw_data_directory.resolve()
    output_directory = command_line_arguments.output_directory.resolve()
    skill_aliases = load_skill_aliases(command_line_arguments.skill_curation_file_path.resolve())

    specs = source_specs()
    missing: list[str] = []
    for name, path, _, _, is_xlsx in specs:
        candidate = raw_data_directory / name
        if is_xlsx:
            if not candidate.is_file():
                missing.append(name)
        elif not candidate.is_file() and not candidate.with_suffix(".zip").is_file():
            missing.append(name)
    if missing:
        raise SystemExit("Missing required raw inputs:\n- " + "\n- ".join(missing))

    output_directory.mkdir(parents=True, exist_ok=True)
    historical_path = output_directory / "jobs_historical_2023_sample.csv.gz"
    latest_path = output_directory / "jobs_latest_export_unverified.csv.gz"
    snapshots_path = output_directory / "jobs_other_snapshots_unverified.csv.gz"
    skills_path = output_directory / "job_skills.csv.gz"
    observed_path = output_directory / "skill_observations.csv.gz"
    report_path = output_directory / "data_quality_report.json"

    historical_handle, historical_writer = write_compressed_csv(historical_path, OUTPUT_FIELDS)
    latest_handle, latest_writer = write_compressed_csv(latest_path, OUTPUT_FIELDS)
    snapshots_handle, snapshots_writer = write_compressed_csv(snapshots_path, OUTPUT_FIELDS)
    skills_handle, skills_writer = write_compressed_csv(skills_path, SKILL_FIELDS)

    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generated_by": "scripts/data_cleaning/build_site_data.py",
        "record_status_policy": "Every row is marked unknown_not_verified; the source exports do not establish that a listing is currently active.",
        "deduplication_policy": "No cross-source deduplication is performed. Exact duplicate rows within each source are flagged, not deleted.",
        "date_policy": "Only explicit posted_at/job_posted_date fields populate posted_at. A field named updated is preserved separately and not treated as a posting or collection date.",
        "salary_policy": "Salary values and provenance are preserved as text. No currency conversion or estimate-to-advertised-salary inference is performed.",
        "files": {},
        "bucket_policy": {
            "historical_sample": "International export only; all source posting dates were observed in 2023.",
            "latest_export": "Remote, startup, and Jooble/Careerjet after-adding-skills exports. Listing activity is not verified.",
            "other_snapshot": "Merged, Arab, and cybersecurity exports kept separate because their date and current-status semantics do not establish historical coverage or active listings.",
        },
        "totals": {
            "historical_sample_rows": 0,
            "latest_export_rows": 0,
            "other_snapshot_rows": 0,
            "job_skill_rows": 0,
        },
        "outputs": {},
    }
    skill_counts: Counter[tuple[str, str]] = Counter()
    try:
        for filename, path, bucket, source_dataset, is_xlsx in specs:
            source_path = raw_data_directory / filename
            source_file = source_path.name
            if is_xlsx:
                rows: Iterable[dict[str, Any]] = read_excel_workbook_rows(source_path)
                original_skills = None
            else:
                rows = ()
                original_skills = None
                if filename in LATEST_JOB_EXPORTS:
                    base_name, _ = LATEST_JOB_EXPORTS[filename]
                    base_path = raw_data_directory / base_name
                    original_skills = load_original_skills(base_path) if base_path.is_file() else None

            file_report: dict[str, Any] = {
                "source_file": source_file,
                "source_dataset": source_dataset,
                "bucket": bucket,
                "rows": 0,
                "exact_duplicate_rows": 0,
                "missing": Counter(),
                "skill_rows_changed_vs_base": 0,
                "skill_rows_filled_vs_base": 0,
                "skill_rows_base_comparison_unavailable": 0,
                "duplicate_skill_tokens_removed": 0,
                "duplicate_skill_assignments_after_canonicalization": 0,
                "salary_raw_text_without_numeric_amount": 0,
            }
            seen: set[bytes] = set()

            def consume(row_iter: Iterable[dict[str, Any]]) -> None:
                for row_number, row in enumerate(row_iter, start=1):
                    file_report["rows"] += 1
                    digest = exact_row_digest(row)
                    duplicate = digest in seen
                    if duplicate:
                        file_report["exact_duplicate_rows"] += 1
                    else:
                        seen.add(digest)

                    source_record_identifier = first_available_source_value(row, "id", "job_id", "row_id")
                    baseline_skill = None
                    if original_skills is not None:
                        if source_record_identifier and source_record_identifier in original_skills:
                            baseline_skill = original_skills[source_record_identifier]
                            enriched_skill = first_available_source_value(row, "skills", "job_skills", "required_skills")
                            if baseline_skill != enriched_skill:
                                file_report["skill_rows_changed_vs_base"] += 1
                                if not contains_source_value(baseline_skill) and contains_source_value(enriched_skill):
                                    file_report["skill_rows_filled_vs_base"] += 1
                        else:
                            file_report["skill_rows_base_comparison_unavailable"] += 1

                    record = build_record(
                        row,
                        source_file,
                        source_dataset,
                        "latest_export_listing_status_unverified" if bucket == "latest_export" else identify_source(filename)[1],
                        row_number,
                        original_skills,
                    )
                    record["exact_duplicate_within_source"] = "yes" if duplicate else "no"
                    if duplicate:
                        record["data_quality_flags"] += ";exact_duplicate_within_source"

                    for field_name in (
                        "title", "company", "country", "description", "source_url", "salary_raw", "skills", "posted_at"
                    ):
                        if not contains_source_value(record.get(field_name, "")):
                            file_report["missing"][field_name] += 1
                    salary_values = (record.get("salary_raw", ""), record.get("salary_year_avg", ""), record.get("salary_hour_avg", ""))
                    if not any(contains_numeric_salary_amount(value) for value in salary_values):
                        file_report["missing"]["salary_any_value"] += 1
                    if contains_source_value(record.get("salary_raw", "")) and not contains_numeric_salary_amount(record.get("salary_raw", "")):
                        file_report["salary_raw_text_without_numeric_amount"] += 1

                    if bucket == "historical_sample":
                        writer = historical_writer
                        total_key = "historical_sample_rows"
                    elif bucket == "latest_export":
                        writer = latest_writer
                        total_key = "latest_export_rows"
                    else:
                        writer = snapshots_writer
                        total_key = "other_snapshot_rows"
                    writer.writerow(record)
                    report["totals"][total_key] += 1

                    raw_tokens = split_skill_labels(record["skills"], source_file, deduplicate=False)
                    tokens = ordered_unique_skills(raw_tokens)
                    file_report["duplicate_skill_tokens_removed"] += len(raw_tokens) - len(tokens)
                    baseline_available = (
                        original_skills is not None
                        and source_record_identifier
                        and source_record_identifier in original_skills
                    )
                    original_skill_identifiers = (
                        {
                            resolve_skill_metadata(token, skill_aliases)["skill_id"]
                            for token in split_skill_labels(record["skills_original"], source_file)
                        }
                        if baseline_available
                        else None
                    )
                    canonical_assignments: dict[str, dict[str, str]] = {}
                    for token in tokens:
                        normalized = normalize_skill_label(token)
                        metadata = resolve_skill_metadata(token, skill_aliases)
                        skill_counts[(source_dataset, token)] += 1
                        provenance_status = skill_provenance_status(
                            record, token, original_skill_identifiers, skill_aliases
                        )
                        if metadata["skill_id"] in canonical_assignments:
                            file_report["duplicate_skill_assignments_after_canonicalization"] += 1
                            if provenance_status == "present_in_base_export":
                                canonical_assignments[metadata["skill_id"]]["skill_status"] = provenance_status
                            continue
                        canonical_assignments[metadata["skill_id"]] = {
                            "record_id": record["record_id"],
                            "source_dataset": source_dataset,
                            "source_file": source_file,
                            "skill_raw": token,
                            "skill_normalized": normalized,
                            "skill_id": metadata["skill_id"],
                            "skill_category": metadata["category"],
                            "skill_match_policy": metadata["match_policy"],
                            "skill_review_status": metadata["review_status"],
                            "skill_provenance": record["skills_source"],
                            "skill_status": provenance_status,
                        }
                    for assignment in canonical_assignments.values():
                        skills_writer.writerow(assignment)
                        report["totals"]["job_skill_rows"] += 1

            if is_xlsx:
                consume(rows)
            else:
                with open_comma_separated_values_reader(raw_data_directory / filename) as reader:
                    consume(reader)

            file_report["missing"] = dict(file_report["missing"])
            report["files"][filename] = file_report
    finally:
        historical_handle.close()
        latest_handle.close()
        snapshots_handle.close()
        skills_handle.close()

    observed_handle, observed_writer = write_compressed_csv(
        observed_path, ["source_dataset", "skill_raw", "skill_normalized", "occurrence_count"]
    )
    try:
        for (source_dataset, skill_raw), count in sorted(
            skill_counts.items(), key=lambda item: (item[0][0], item[0][1].casefold())
        ):
            observed_writer.writerow({
                "source_dataset": source_dataset,
                "skill_raw": skill_raw,
                "skill_normalized": re.sub(r"\s+", " ", skill_raw.casefold()).strip(),
                "occurrence_count": count,
            })
    finally:
        observed_handle.close()

    for name, output in (
        ("jobs_historical_2023_sample", historical_path),
        ("jobs_latest_export_unverified", latest_path),
        ("jobs_other_snapshots_unverified", snapshots_path),
        ("job_skills", skills_path),
        ("skill_observations", observed_path),
    ):
        report["outputs"][name] = {"path": str(output.relative_to(PROJECT_ROOT_DIRECTORY) if output.is_relative_to(PROJECT_ROOT_DIRECTORY) else output), "size_bytes": output.stat().st_size}

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "historical_sample_rows": report["totals"]["historical_sample_rows"],
        "latest_export_rows": report["totals"]["latest_export_rows"],
        "other_snapshot_rows": report["totals"]["other_snapshot_rows"],
        "job_skill_rows": report["totals"]["job_skill_rows"],
        "files": report["outputs"],
        "report": str(report_path.relative_to(PROJECT_ROOT_DIRECTORY) if report_path.is_relative_to(PROJECT_ROOT_DIRECTORY) else report_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
