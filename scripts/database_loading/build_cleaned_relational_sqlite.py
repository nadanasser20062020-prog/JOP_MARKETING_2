#!/usr/bin/env python3
"""Import the complete cleaned-audit CSV into the project's relational SQLite schema.

The existing domain tables remain the application-facing model. A one-to-one
``job_cleaning_audit`` table stores every cleaned CSV column, unchanged by name,
while normalized skills, source lineage, import history, and learning resources
are loaded into their ERD tables. The CSV and raw source files are read-only.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
import unicodedata
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

csv.field_size_limit(2**31 - 1)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import connect_to_database, resolve_database_path  # noqa: E402
from scripts.database_loading import sqlite_database  # noqa: E402

DEFAULT_DATASET = PROJECT_ROOT / "data" / "processed" / "jobs_cleaned_audited.csv.gz"
DEFAULT_DATABASE = PROJECT_ROOT / "data" / "processed" / "jobs_cleaned_audited.sqlite3"
DEFAULT_SUMMARY = PROJECT_ROOT / "analysis" / "reports" / "data_cleaning" / "cleaning_summary.json"
DEFAULT_SOURCE_MANIFEST = PROJECT_ROOT / "analysis" / "reports" / "data_cleaning" / "source_manifest.csv"
REFERENCE_DIRECTORY = PROJECT_ROOT / "data" / "reference"
SKILL_CATALOG_PATH = REFERENCE_DIRECTORY / "skill_catalog.csv"
SKILL_ALIASES_PATH = REFERENCE_DIRECTORY / "skill_aliases.csv"
LEARNING_RESOURCES_JSON_PATH = REFERENCE_DIRECTORY / "learning_resources.json"
LEARNING_RESOURCES_CSV_PATH = REFERENCE_DIRECTORY / "learning_resources.csv"
AUDIT_TABLE = "job_cleaning_audit"
BATCH_SIZE = 500
PROGRESS_INTERVAL = 50_000

INTEGER_FIELDS = frozenset(
    {
        "source_row_number",
        "experience_years_min",
        "experience_years_max",
        "description_char_count",
        "skill_token_count_raw",
        "skill_token_count_unique",
        "skill_canonical_id_count",
        "skill_duplicate_token_count",
        "salary_estimate_reference_count",
    }
)
REAL_FIELDS = frozenset(
    {
        "salary_amount_1_original_currency",
        "salary_amount_2_original_currency",
        "salary_min_original_currency",
        "salary_max_original_currency",
        "salary_midpoint_original_currency",
        "salary_annualized_min_native",
        "salary_annualized_max_native",
        "salary_annualized_midpoint_native",
        "salary_fx_rate_to_reporting_currency",
        "salary_annualized_min_reporting_currency",
        "salary_annualized_max_reporting_currency",
        "salary_annualized_midpoint_reporting_currency",
        "salary_annual_min_usd",
        "salary_annual_salary_usd",
        "salary_annual_max_usd",
        "salary_annual_min_egp",
        "salary_annual_salary_egp",
        "salary_annual_max_egp",
        "salary_annual_min_sar",
        "salary_annual_salary_sar",
        "salary_annual_max_sar",
    }
)

SOURCE_BUCKETS = {
    "international_jobs": "historical_2023_sample",
    "merged_tech_jobs": "other_snapshot",
    "arab_tech_jobs": "other_snapshot",
    "cybersecurity_jobs": "other_snapshot",
    "remote_tech_jobs": "latest_export_unverified",
    "startup_jobs": "latest_export_unverified",
    "jooble_careerjet_jobs": "latest_export_unverified",
}
SOURCE_DATE_SEMANTICS = {
    "international_jobs": "source posting dates are a 2023 historical sample",
    "merged_tech_jobs": "source date semantics are not established",
    "arab_tech_jobs": "partial posting-date coverage",
    "cybersecurity_jobs": "source has no posting-date field",
    "remote_tech_jobs": "latest export snapshot; listing activity is unverified",
    "startup_jobs": "latest export snapshot; listing activity is unverified",
    "jooble_careerjet_jobs": "latest export snapshot; listing activity is unverified",
}

JOB_FIELDS = tuple(sqlite_database.JOB_FIELD_NAMES)
JOB_SKILL_FIELDS = tuple(sqlite_database.JOB_SKILL_FIELD_NAMES)


def quote_identifier(value: str) -> str:
    if not value:
        raise ValueError("SQLite identifiers cannot be empty")
    return '"' + value.replace('"', '""') + '"'


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def optional_text(value: Any) -> str | None:
    if value is None:
        return None
    result = str(value)
    return result if result.strip() else None


def normalized_skill(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", value).strip()


def sqlite_column_value(value: str | None, field_name: str, csv_row_number: int) -> Any:
    if value is None or value == "":
        return None
    if field_name in INTEGER_FIELDS:
        try:
            return int(value)
        except ValueError as error:
            raise ValueError(
                f"Invalid integer at CSV row {csv_row_number}, column {field_name}: {value!r}"
            ) from error
    if field_name in REAL_FIELDS:
        try:
            number = float(value)
        except ValueError as error:
            raise ValueError(
                f"Invalid real number at CSV row {csv_row_number}, column {field_name}: {value!r}"
            ) from error
        if not math.isfinite(number):
            raise ValueError(
                f"Non-finite real number at CSV row {csv_row_number}, column {field_name}: {value!r}"
            )
        return number
    return value


def read_json_list(value: str | None, field_name: str, csv_row_number: int) -> list[str]:
    if not value:
        return []
    try:
        result = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON at CSV row {csv_row_number}, column {field_name}") from error
    if not isinstance(result, list) or any(not isinstance(item, str) for item in result):
        raise ValueError(f"Expected a JSON string array at CSV row {csv_row_number}, column {field_name}")
    return result


def read_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Cleaning summary not found: {path}")
    summary = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict):
        raise ValueError("Cleaning summary must contain a JSON object")
    for field in ("cleaned_dataset_sha256", "input_rows", "output_rows", "rows_dropped", "audit_date", "source_ref"):
        if field not in summary:
            raise ValueError(f"Cleaning summary is missing {field!r}")
    if int(summary["input_rows"]) != int(summary["output_rows"]) or int(summary["rows_dropped"]) != 0:
        raise ValueError("Refusing to import a cleaned dataset whose summary reports dropped rows")
    expected_hash = str(summary["cleaned_dataset_sha256"]).lower()
    if len(expected_hash) != 64:
        raise ValueError("Cleaning summary contains an invalid SHA-256 value")
    return summary


def read_source_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Source manifest not found: {path}")
    result: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = {"file", "role", "size_bytes", "sha256", "status"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Source manifest is missing columns: {sorted(missing)}")
        for row in reader:
            name = row.get("file", "")
            if name:
                result[name] = row
    return result


def count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source)
        next(reader, None)
        return sum(1 for _ in reader)


def resource_file_counts() -> dict[str, int]:
    resource_document = json.loads(LEARNING_RESOURCES_JSON_PATH.read_text(encoding="utf-8"))
    resources = resource_document.get("resources")
    if not isinstance(resources, list):
        raise ValueError(f"Learning-resource JSON has no resources list: {LEARNING_RESOURCES_JSON_PATH}")
    return {
        "skill_catalog.csv": count_csv_rows(SKILL_CATALOG_PATH),
        "skill_aliases.csv": count_csv_rows(SKILL_ALIASES_PATH),
        "learning_resources.json": len(resources),
        "learning_resources.csv": count_csv_rows(LEARNING_RESOURCES_CSV_PATH),
    }


def import_fingerprint(paths: list[Path], dataset_sha256: str) -> str:
    digest = hashlib.sha256()
    for path in sorted((Path(item).resolve() for item in paths), key=str):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(dataset_sha256.encode("ascii") if path.name.endswith(".csv.gz") else sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def snapshot_type_for(source_dataset: str) -> str:
    try:
        return SOURCE_BUCKETS[source_dataset]
    except KeyError as error:
        raise ValueError(f"No snapshot classification is defined for source {source_dataset!r}") from error


def insert_data_source(
    connection: sqlite3.Connection,
    source_dataset: str,
    display_name: str,
    notes: str,
    source_kind: str,
    snapshot_bucket: str,
    date_semantics: str | None,
    listing_status: str | None,
    source_file_count: int,
    source_row_count: int,
) -> None:
    connection.execute(
        "INSERT INTO data_sources "
        "(source_dataset, display_name, notes, source_kind, snapshot_bucket, date_semantics, "
        "listing_status, source_file_count, source_row_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            source_dataset,
            display_name,
            notes,
            source_kind,
            snapshot_bucket,
            date_semantics,
            listing_status,
            source_file_count,
            source_row_count,
        ),
    )


def insert_source_file(
    connection: sqlite3.Connection,
    *,
    source_dataset: str,
    source_file: str,
    snapshot_group: str,
    snapshot_type: str | None,
    notes: str,
    physical_file_name: str,
    logical_file_name: str,
    file_format: str,
    file_role: str,
    byte_size: int | None,
    sha256: str | None,
    source_row_count: int | None,
    source_dataset_original: str | None = None,
) -> None:
    connection.execute(
        "INSERT INTO source_files "
        "(source_dataset, source_file, snapshot_group, snapshot_type, notes, source_file_id, "
        "source_dataset_original, physical_file_name, logical_file_name, file_format, file_role, "
        "archive_member_name, byte_size, sha256, source_row_count, archive_member_count) "
        "VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, NULL, ?, ?, ?, NULL)",
        (
            source_dataset,
            source_file,
            snapshot_group,
            snapshot_type,
            notes,
            source_dataset_original,
            physical_file_name,
            logical_file_name,
            file_format,
            file_role,
            byte_size,
            sha256,
            source_row_count,
        ),
    )


def register_sources(
    connection: sqlite3.Connection,
    summary: dict[str, Any],
    source_manifest: dict[str, dict[str, str]],
    cleaned_dataset: Path,
    dataset_sha256: str,
    reference_counts: dict[str, int],
) -> dict[tuple[str, str], int]:
    file_reports = summary.get("file_reports")
    if not isinstance(file_reports, dict):
        raise ValueError("Cleaning summary has no per-source file reports")
    selected_files: dict[tuple[str, str], int] = {}
    for source_file, report in file_reports.items():
        if not isinstance(report, dict) or report.get("status") != "processed":
            continue
        source_dataset = str(report.get("source_dataset", "")).strip()
        if source_dataset:
            selected_files[(source_dataset, source_file)] = int(report.get("rows", 0))
    if not selected_files:
        raise ValueError("Cleaning summary has no processed job-source files")
    if len({dataset for dataset, _ in selected_files}) != int(summary.get("available_job_source_count", len(selected_files))):
        raise ValueError("Summary source count disagrees with processed source files")

    rows_by_dataset: Counter[str] = Counter()
    files_by_dataset: Counter[str] = Counter()
    for (source_dataset, _), row_count in selected_files.items():
        rows_by_dataset[source_dataset] += row_count
        files_by_dataset[source_dataset] += 1

    for source_dataset in sorted(rows_by_dataset):
        display_name, source_notes = sqlite_database.SOURCE_METADATA.get(
            source_dataset,
            (source_dataset.replace("_", " ").title(), "Source snapshot semantics are not independently verified."),
        )
        bucket = snapshot_type_for(source_dataset)
        date_semantics = SOURCE_DATE_SEMANTICS.get(source_dataset, "source date semantics are not established")
        insert_data_source(
            connection,
            source_dataset,
            display_name,
            source_notes,
            "job_source",
            bucket,
            date_semantics,
            "unknown_not_verified",
            files_by_dataset[source_dataset],
            rows_by_dataset[source_dataset],
        )

    cleaned_source = "cleaned_audit_snapshot"
    curated_source = "curated_reference_data"
    insert_data_source(
        connection,
        cleaned_source,
        "Cleaned Audit Dataset",
        "Loss-preserving cleaned CSV used as the input to this SQLite import.",
        "cleaned_audit_dataset",
        "full_cleaned_audit_snapshot",
        "Source-level date semantics are retained per job record.",
        "unknown_not_verified",
        1,
        int(summary["output_rows"]),
    )
    reference_total_rows = sum(reference_counts.values())
    insert_data_source(
        connection,
        curated_source,
        "Curated Reference Data",
        "Project-reviewed skill taxonomy, aliases, and learning-resource metadata.",
        "curated_reference",
        "project_reference",
        None,
        None,
        len(reference_counts),
        reference_total_rows,
    )

    for (source_dataset, source_file), row_count in sorted(selected_files.items()):
        manifest_row = source_manifest.get(source_file)
        if not manifest_row or manifest_row.get("role") != "selected_job_source":
            raise ValueError(f"Missing selected-source manifest entry for {source_file!r}")
        if manifest_row.get("status") != "available":
            raise ValueError(f"Source manifest marks {source_file!r} as unavailable")
        digest = manifest_row.get("sha256") or None
        size_text = manifest_row.get("size_bytes", "")
        byte_size = int(size_text) if size_text else None
        snapshot_type = snapshot_type_for(source_dataset)
        insert_source_file(
            connection,
            source_dataset=source_dataset,
            source_file=source_file,
            snapshot_group=sqlite_database.source_snapshot_group(source_dataset),
            snapshot_type=snapshot_type,
            notes=f"Original source file represented by the cleaned audit; {row_count} job rows retained. Listing activity is unverified.",
            physical_file_name=source_file,
            logical_file_name=source_file,
            file_format=Path(source_file).suffix.lstrip(".").lower() or "unknown",
            file_role="selected_job_source",
            byte_size=byte_size,
            sha256=digest,
            source_row_count=row_count,
            source_dataset_original=source_dataset,
        )

    insert_source_file(
        connection,
        source_dataset=cleaned_source,
        source_file=cleaned_dataset.name,
        snapshot_group="cleaned_audit_snapshot",
        snapshot_type="full_cleaned_audit",
        notes=f"Verified cleaned dataset; SHA-256 {dataset_sha256}.",
        physical_file_name=cleaned_dataset.name,
        logical_file_name=cleaned_dataset.name,
        file_format="csv.gz",
        file_role="cleaned_audit_input",
        byte_size=cleaned_dataset.stat().st_size,
        sha256=dataset_sha256,
        source_row_count=int(summary["output_rows"]),
        source_dataset_original=cleaned_source,
    )

    reference_paths = {
        "skill_catalog.csv": SKILL_CATALOG_PATH,
        "skill_aliases.csv": SKILL_ALIASES_PATH,
        "learning_resources.json": LEARNING_RESOURCES_JSON_PATH,
        "learning_resources.csv": LEARNING_RESOURCES_CSV_PATH,
    }
    for file_name, file_path in reference_paths.items():
        insert_source_file(
            connection,
            source_dataset=curated_source,
            source_file=file_name,
            snapshot_group="curated_reference",
            snapshot_type="project_reference",
            notes=f"Local curated reference file; {reference_counts[file_name]} records read.",
            physical_file_name=file_name,
            logical_file_name=file_name,
            file_format=file_path.suffix.lstrip(".").lower(),
            file_role="curated_reference",
            byte_size=file_path.stat().st_size,
            sha256=sha256_file(file_path),
            source_row_count=reference_counts[file_name],
            source_dataset_original=curated_source,
        )
    return selected_files


def make_job_values(row: dict[str, str | None], csv_row_number: int) -> tuple[Any, ...]:
    record_id = optional_text(row.get("record_id"))
    source_dataset = optional_text(row.get("source_dataset"))
    source_file = optional_text(row.get("source_file"))
    row_number_text = row.get("source_row_number")
    if not record_id or not source_dataset or not source_file or not row_number_text:
        raise ValueError(f"Missing job key/provenance at cleaned CSV row {csv_row_number}")
    try:
        source_row_number = int(row_number_text)
    except ValueError as error:
        raise ValueError(f"Invalid source_row_number at cleaned CSV row {csv_row_number}") from error
    if source_row_number < 1:
        raise ValueError(f"source_row_number must be positive at cleaned CSV row {csv_row_number}")

    title = optional_text(row.get("title_clean")) or optional_text(row.get("title_raw"))
    company = optional_text(row.get("company_clean")) or optional_text(row.get("company_raw"))
    country = optional_text(row.get("country_standardized")) or optional_text(row.get("country_raw"))
    posted_at = optional_text(row.get("posted_at_iso")) or optional_text(row.get("posted_at_raw"))
    source_updated_at = optional_text(row.get("source_updated_at_iso")) or optional_text(row.get("source_updated_at_raw"))
    salary_period = optional_text(row.get("salary_period_code"))
    salary_eligible = row.get("salary_statistics_eligible") == "yes"
    salary_year_avg = (
        optional_text(row.get("salary_annualized_midpoint_native"))
        if salary_eligible and salary_period == "YEAR"
        else None
    )
    salary_hour_avg = (
        optional_text(row.get("salary_midpoint_original_currency"))
        if salary_eligible and salary_period == "HOUR"
        else None
    )

    values = {
        "record_id": record_id,
        "source_dataset": source_dataset,
        "source_file": source_file,
        "source_row_number": source_row_number,
        "source_record_id": optional_text(row.get("source_record_id")),
        "record_origin": optional_text(row.get("record_origin")),
        "source_platform": optional_text(row.get("source_platform")),
        "title": title,
        "title_short": title,
        "company": company,
        "country": country,
        "city": optional_text(row.get("city_raw")),
        "region": optional_text(row.get("region_raw")),
        "location_raw": optional_text(row.get("location_raw")),
        "work_mode_raw": optional_text(row.get("work_mode_raw")),
        "remote_flag": optional_text(row.get("remote_flag_raw")),
        "employment_type_raw": optional_text(row.get("employment_type_raw")),
        "experience_raw": optional_text(row.get("experience_raw")),
        "category_raw": optional_text(row.get("category_raw")),
        "description": optional_text(row.get("description_raw")),
        "posted_at": posted_at,
        "source_updated_at": source_updated_at,
        "source_date_field": optional_text(row.get("source_date_field")),
        "salary_raw": optional_text(row.get("salary_raw")),
        "salary_rate": salary_period or optional_text(row.get("salary_rate_raw")),
        "salary_year_avg": salary_year_avg,
        "salary_hour_avg": salary_hour_avg,
        "salary_currency": optional_text(row.get("salary_currency_code")) or optional_text(row.get("salary_currency_raw")),
        "salary_basis": salary_period or optional_text(row.get("salary_basis_raw")),
        "salary_source": optional_text(row.get("salary_source_raw")) or optional_text(row.get("salary_estimation_source")),
        "salary_provenance_status": optional_text(row.get("salary_provenance_status")),
        "skills": optional_text(row.get("skills_tokens_json")),
        "skills_original": optional_text(row.get("skills_raw")),
        "skills_source": optional_text(row.get("skills_source_raw")),
        "skills_enrichment_status": optional_text(row.get("skills_enrichment_status")),
        "source_url": optional_text(row.get("source_url_raw")),
        "listing_status": optional_text(row.get("listing_status")),
        "snapshot_type": optional_text(row.get("snapshot_type")),
        "exact_duplicate_within_source": optional_text(row.get("exact_duplicate_within_source")),
        "data_quality_flags": optional_text(row.get("data_quality_flags")),
    }
    missing_fields = set(JOB_FIELDS) - set(values)
    if missing_fields:
        raise RuntimeError(f"The project jobs mapping is incomplete: {sorted(missing_fields)}")
    return tuple(values[field] for field in JOB_FIELDS)


def provenance_bucket(source_text: str | None, skills_raw: str | None) -> str:
    value = (source_text or "").casefold()
    if "research_added" in value:
        return "research_added"
    if "research_filled" in value:
        return "research_filled"
    if "inferred" in value:
        return "inferred"
    if "description" in value or "reading the job description" in value:
        return "description_extraction"
    if "skills_column" in value:
        return "enriched_skills_column"
    if "original" in value or "source" in value:
        return "source_original"
    if skills_raw:
        return "source_skill_text"
    return "cleaned_skill_ids_json"


def skill_label_for_id(
    skill_id: str,
    tokens: list[str],
    index: int,
    skill_id_count: int,
    aliases_by_label: dict[str, set[str]],
    catalog: dict[str, dict[str, str]],
) -> tuple[str, str, bool]:
    # A positional pairing is meaningful only when both JSON arrays have the
    # same length, and only when the label resolves uniquely to this skill.
    if len(tokens) == skill_id_count and index < len(tokens):
        candidate = tokens[index]
        candidate_normalized = normalized_skill(candidate)
        if aliases_by_label.get(candidate_normalized, set()) == {skill_id}:
            return candidate, candidate_normalized, False

    # If positional correspondence is unavailable, accept a label only when
    # exactly one distinct normalized label resolves uniquely to this skill.
    # Multiple plausible labels are ambiguous, so use the catalog's canonical
    # name instead of arbitrarily selecting the first token.
    candidates: dict[str, str] = {}
    for token in tokens:
        candidate_normalized = normalized_skill(token)
        if candidate_normalized and aliases_by_label.get(candidate_normalized, set()) == {skill_id}:
            candidates.setdefault(candidate_normalized, token)
    if len(candidates) == 1:
        candidate_normalized, candidate = next(iter(candidates.items()))
        return candidate, candidate_normalized, False

    canonical = catalog[skill_id]["canonical_name"]
    return canonical, normalized_skill(canonical), True


def add_import_run_file(
    connection: sqlite3.Connection,
    import_run_id: int,
    *,
    source_dataset: str,
    source_file: str,
    rows: int,
    output_tables: list[str],
    processing_role: str,
    notes: str,
    job_rows_emitted: int = 0,
    job_skill_rows_emitted: int = 0,
    reference_rows_emitted: int = 0,
) -> None:
    connection.execute(
        "INSERT INTO import_run_files "
        "(import_run_id, source_dataset, source_file, rows_read, rows_loaded, rows_rejected, "
        "import_status, notes, job_rows_emitted, job_skill_rows_emitted, reference_rows_emitted, "
        "output_tables, processing_role) VALUES (?, ?, ?, ?, ?, 0, 'succeeded', ?, ?, ?, ?, ?, ?)",
        (
            import_run_id,
            source_dataset,
            source_file,
            rows,
            rows,
            notes,
            job_rows_emitted,
            job_skill_rows_emitted,
            reference_rows_emitted,
            json.dumps(output_tables, ensure_ascii=False),
            processing_role,
        ),
    )


def build_database(
    dataset_path: Path = DEFAULT_DATASET,
    database_path: Path = DEFAULT_DATABASE,
    *,
    summary_path: Path = DEFAULT_SUMMARY,
    source_manifest_path: Path = DEFAULT_SOURCE_MANIFEST,
    replace_existing: bool = False,
    progress: bool = True,
) -> dict[str, Any]:
    dataset_path = Path(dataset_path).expanduser().resolve()
    summary_path = Path(summary_path).expanduser().resolve()
    source_manifest_path = Path(source_manifest_path).expanduser().resolve()
    database_path = resolve_database_path(Path(database_path).expanduser())

    if not dataset_path.is_file():
        raise FileNotFoundError(f"Cleaned audit CSV is not available: {dataset_path}")
    if not database_path.parent.is_dir():
        database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path == dataset_path:
        raise ValueError("SQLite output cannot overwrite the cleaned CSV input")
    if database_path.exists() and not replace_existing:
        raise FileExistsError(f"SQLite database already exists; pass --replace to rebuild: {database_path}")

    summary = read_summary(summary_path)
    expected_sha256 = str(summary["cleaned_dataset_sha256"]).lower()
    actual_sha256 = sha256_file(dataset_path)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            "Cleaned dataset SHA-256 does not match the current cleaning summary; "
            f"expected {expected_sha256}, found {actual_sha256}. Refusing to import a different snapshot."
        )
    expected_rows = int(summary["output_rows"])
    source_manifest = read_source_manifest(source_manifest_path)
    reference_counts = resource_file_counts()
    input_paths = [
        dataset_path,
        summary_path,
        source_manifest_path,
        SKILL_CATALOG_PATH,
        SKILL_ALIASES_PATH,
        LEARNING_RESOURCES_JSON_PATH,
        LEARNING_RESOURCES_CSV_PATH,
    ]
    input_fingerprint = import_fingerprint(input_paths, actual_sha256)

    temporary_database = database_path.with_name(f".{database_path.name}.{uuid.uuid4().hex}.building")
    connection: sqlite3.Connection | None = None
    try:
        connection = connect_to_database(temporary_database, create_if_missing=True)
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute("PRAGMA temp_store=MEMORY")
        connection.execute("PRAGMA cache_size=-65536")
        sqlite_database.apply_migrations(connection)

        with gzip.open(dataset_path, "rt", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source, strict=True)
            fieldnames = reader.fieldnames or []
            if not fieldnames or len(fieldnames) != 123 or len(set(fieldnames)) != 123:
                raise ValueError(f"Expected 123 unique cleaned CSV columns, found {len(fieldnames)}")
            table_columns = [
                row["name"] for row in connection.execute(f"PRAGMA table_info({quote_identifier(AUDIT_TABLE)})")
            ]
            if fieldnames != table_columns:
                raise ValueError(
                    "Cleaned CSV header does not match migration 006. "
                    "Create a follow-up migration for schema changes instead of dropping/reordering columns."
                )
            if not INTEGER_FIELDS.issubset(fieldnames) or not REAL_FIELDS.issubset(fieldnames):
                raise ValueError("The cleaned column type map does not cover the current CSV schema")

            job_insert_sql = (
                f"INSERT INTO jobs ({', '.join(quote_identifier(name) for name in JOB_FIELDS)}) "
                f"VALUES ({', '.join('?' for _ in JOB_FIELDS)})"
            )
            audit_insert_sql = (
                f"INSERT INTO {quote_identifier(AUDIT_TABLE)} "
                f"({', '.join(quote_identifier(name) for name in fieldnames)}) "
                f"VALUES ({', '.join('?' for _ in fieldnames)})"
            )
            skill_insert_sql = (
                f"INSERT INTO job_skills ({', '.join(quote_identifier(name) for name in JOB_SKILL_FIELDS)}) "
                f"VALUES ({', '.join('?' for _ in JOB_SKILL_FIELDS)})"
            )

            connection.execute("BEGIN IMMEDIATE")
            run_notes = (
                "Loaded the complete cleaned-audit CSV without dropping source rows. "
                f"Source SHA-256: {actual_sha256}; cleaning audit date: {summary['audit_date']}; "
                f"source reference: {summary['source_ref']}. The original source row is retained in source_row_json."
            )
            import_run_id, _ = sqlite_database.create_import_run(
                connection,
                "sqlite_cleaned_audit_relational_v1",
                input_fingerprint,
                run_notes,
            )
            selected_files = register_sources(
                connection,
                summary,
                source_manifest,
                dataset_path,
                actual_sha256,
                reference_counts,
            )

            skills_loaded = sqlite_database.load_skill_catalog(connection)
            aliases_loaded = sqlite_database.load_skill_aliases(connection)
            resource_counts = sqlite_database.load_learning_resources(connection)
            skill_catalog = {
                row["skill_id"]: {
                    "canonical_name": row["canonical_name"],
                    "category": row["category"],
                    "match_policy": row["match_policy"],
                    "review_status": row["review_status"],
                }
                for row in connection.execute(
                    "SELECT skill_id, canonical_name, category, match_policy, review_status FROM skills"
                )
            }
            aliases_by_label: dict[str, set[str]] = defaultdict(set)
            for alias_row in connection.execute("SELECT alias_normalized, skill_id FROM skill_aliases"):
                aliases_by_label[normalized_skill(alias_row["alias_normalized"])].add(alias_row["skill_id"])
            for skill_id, skill in skill_catalog.items():
                aliases_by_label[normalized_skill(skill["canonical_name"])].add(skill_id)

            rows_loaded = 0
            skill_links_loaded = 0
            label_observations: Counter[tuple[str, str, str]] = Counter()
            source_counts: Counter[tuple[str, str]] = Counter()
            observed_snapshot_types: dict[tuple[str, str], str] = {}
            fallback_skill_labels = 0
            job_batch: list[tuple[Any, ...]] = []
            audit_batch: list[tuple[Any, ...]] = []
            skill_batch: list[tuple[Any, ...]] = []
            validation_samples: list[tuple[str, dict[str, str | None]]] = []
            sample_rows = {1, expected_rows, *range(PROGRESS_INTERVAL, expected_rows + 1, PROGRESS_INTERVAL)}

            for csv_row_number, row in enumerate(reader, start=2):
                if None in row:
                    raise ValueError(f"Cleaned CSV row {csv_row_number} contains extra fields")
                if any(row.get(name) is None for name in fieldnames):
                    raise ValueError(f"Cleaned CSV row {csv_row_number} has fewer fields than the header")
                if not row.get("record_id") or not row.get("source_dataset") or not row.get("source_file"):
                    raise ValueError(f"Cleaned CSV row {csv_row_number} has incomplete provenance keys")

                audit_values = tuple(
                    sqlite_column_value(row[name], name, csv_row_number) for name in fieldnames
                )
                job_values = make_job_values(row, csv_row_number)
                tokens = read_json_list(row.get("skills_tokens_json"), "skills_tokens_json", csv_row_number)
                skill_ids = read_json_list(row.get("skill_ids_json"), "skill_ids_json", csv_row_number)
                if len(skill_ids) != len(set(skill_ids)):
                    raise ValueError(f"Duplicate skill IDs in cleaned CSV row {csv_row_number}")
                source_dataset = row["source_dataset"]
                source_file = row["source_file"]
                source_pair = (source_dataset, source_file)
                source_counts[source_pair] += 1
                snapshot_type = row.get("snapshot_type") or ""
                prior_snapshot_type = observed_snapshot_types.setdefault(source_pair, snapshot_type)
                if prior_snapshot_type != snapshot_type:
                    raise ValueError(f"Inconsistent snapshot_type for {source_dataset}/{source_file}")

                for token in tokens:
                    token_normalized = normalized_skill(token)
                    if token_normalized:
                        label_observations[(source_dataset, token_normalized, token)] += 1

                skill_status = optional_text(row.get("skills_enrichment_status"))
                provenance = provenance_bucket(row.get("skills_source_raw"), row.get("skills_raw"))
                for skill_index, skill_id in enumerate(skill_ids):
                    if skill_id not in skill_catalog:
                        raise ValueError(f"Unknown skill_id {skill_id!r} at cleaned CSV row {csv_row_number}")
                    skill_raw, skill_normalized, used_fallback = skill_label_for_id(
                        skill_id,
                        tokens,
                        skill_index,
                        len(skill_ids),
                        aliases_by_label,
                        skill_catalog,
                    )
                    fallback_skill_labels += int(used_fallback)
                    skill = skill_catalog[skill_id]
                    skill_batch.append(
                        (
                            row["record_id"],
                            source_dataset,
                            source_file,
                            skill_raw,
                            skill_normalized,
                            skill_id,
                            skill["category"],
                            skill["match_policy"],
                            skill["review_status"],
                            provenance,
                            skill_status,
                        )
                    )
                skill_links_loaded += len(skill_ids)
                job_batch.append(job_values)
                audit_batch.append(audit_values)
                rows_loaded += 1

                if rows_loaded in sample_rows:
                    validation_samples.append(
                        (
                            row["record_id"],
                            {
                                name: row.get(name)
                                for name in (
                                    "record_id",
                                    "source_dataset",
                                    "source_file",
                                    "title_clean",
                                    "salary_value_type",
                                    "skills_tokens_json",
                                    "skill_ids_json",
                                    "source_row_json",
                                )
                            },
                        )
                    )

                if len(job_batch) >= BATCH_SIZE:
                    connection.executemany(job_insert_sql, job_batch)
                    connection.executemany(audit_insert_sql, audit_batch)
                    if skill_batch:
                        connection.executemany(skill_insert_sql, skill_batch)
                    job_batch.clear()
                    audit_batch.clear()
                    skill_batch.clear()
                    if progress and rows_loaded % PROGRESS_INTERVAL == 0:
                        print(f"Loaded {rows_loaded:,} cleaned rows; {skill_links_loaded:,} skill links...", file=sys.stderr, flush=True)

            if job_batch:
                connection.executemany(job_insert_sql, job_batch)
                connection.executemany(audit_insert_sql, audit_batch)
                if skill_batch:
                    connection.executemany(skill_insert_sql, skill_batch)

        if rows_loaded != expected_rows:
            raise ValueError(f"Loaded {rows_loaded:,} rows; cleaning summary expects {expected_rows:,}")
        if dict(source_counts) != selected_files:
            raise ValueError("Per-source row counts in the cleaned CSV do not match the cleaning summary")
        for source_pair, snapshot_type in observed_snapshot_types.items():
            if snapshot_type != snapshot_type_for(source_pair[0]):
                raise ValueError(f"Snapshot classification mismatch for {source_pair[0]}/{source_pair[1]}")

        observation_rows = [
            (source_dataset, skill_raw, skill_normalized, occurrence_count)
            for (source_dataset, skill_normalized, skill_raw), occurrence_count in sorted(label_observations.items())
        ]
        connection.executemany(
            "INSERT INTO skill_observations "
            "(source_dataset, skill_raw, skill_normalized, occurrence_count) VALUES (?, ?, ?, ?)",
            observation_rows,
        )

        add_import_run_file(
            connection,
            import_run_id,
            source_dataset="cleaned_audit_snapshot",
            source_file=dataset_path.name,
            rows=rows_loaded,
            output_tables=["jobs", "job_cleaning_audit", "job_skills", "skill_observations"],
            processing_role="full_cleaned_audit_csv",
            notes="Full cleaned-audit input; all 123 columns are retained in job_cleaning_audit.",
            job_rows_emitted=rows_loaded,
            job_skill_rows_emitted=skill_links_loaded,
        )
        add_import_run_file(
            connection,
            import_run_id,
            source_dataset="curated_reference_data",
            source_file="skill_catalog.csv",
            rows=skills_loaded,
            output_tables=["skills"],
            processing_role="curated_skill_catalog",
            notes="Project skill catalog loaded with its review and matching policies.",
            reference_rows_emitted=skills_loaded,
        )
        add_import_run_file(
            connection,
            import_run_id,
            source_dataset="curated_reference_data",
            source_file="skill_aliases.csv",
            rows=aliases_loaded,
            output_tables=["skill_aliases"],
            processing_role="curated_skill_aliases",
            notes="Project skill aliases loaded without dropping review-status labels.",
            reference_rows_emitted=aliases_loaded,
        )
        add_import_run_file(
            connection,
            import_run_id,
            source_dataset="curated_reference_data",
            source_file="learning_resources.json",
            rows=resource_counts["learning_resources"],
            output_tables=["learning_resources", "learning_resource_skills"],
            processing_role="curated_learning_resources",
            notes="Course-specific skill links and verification metadata.",
            reference_rows_emitted=resource_counts["learning_resource_skills"],
        )
        add_import_run_file(
            connection,
            import_run_id,
            source_dataset="curated_reference_data",
            source_file="learning_resources.csv",
            rows=reference_counts["learning_resources.csv"],
            output_tables=["learning_resource_languages"],
            processing_role="curated_resource_languages",
            notes="Verified language labels for the curated learning-resource catalog.",
            reference_rows_emitted=resource_counts["learning_resource_languages"],
        )

        sqlite_database.refresh_api_rollups(connection)
        sqlite_database.validate_database(connection)
        expected_audit_rows = int(connection.execute(f"SELECT COUNT(*) FROM {quote_identifier(AUDIT_TABLE)}").fetchone()[0])
        expected_job_rows = int(connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])
        stored_skill_links = int(connection.execute("SELECT COUNT(*) FROM job_skills").fetchone()[0])
        if expected_audit_rows != rows_loaded or expected_job_rows != rows_loaded:
            raise RuntimeError(
                f"Job/audit row-count mismatch: jobs={expected_job_rows}, audit={expected_audit_rows}, loaded={rows_loaded}"
            )
        if stored_skill_links != skill_links_loaded:
            raise RuntimeError(f"Stored {stored_skill_links:,} job-skill links; expected {skill_links_loaded:,}")
        if not sqlite_database.api_rollups_are_ready(connection):
            raise RuntimeError("API rollups do not cover the imported jobs and eligible skills")

        quality_report = sqlite_database.complete_import_run(
            connection,
            import_run_id,
            "sqlite_cleaned_audit_relational_v1",
            input_fingerprint,
            run_notes,
        )
        quality_report.update(
            {
                "cleaned_dataset_sha256": actual_sha256,
                "cleaning_audit_date": summary["audit_date"],
                "cleaned_dataset_rows": rows_loaded,
                "cleaning_audit_columns": len(fieldnames),
                "job_skill_links": skill_links_loaded,
                "skill_observation_rows": len(observation_rows),
                "skill_labels_resolved_to_canonical_fallback": fallback_skill_labels,
                "source_ref": summary["source_ref"],
            }
        )
        connection.execute(
            "UPDATE import_runs SET quality_report = ? WHERE import_run_id = ?",
            (json.dumps(quality_report, ensure_ascii=False, sort_keys=True), import_run_id),
        )
        connection.execute("ANALYZE")
        connection.commit()

        for record_id, expected in validation_samples:
            stored = connection.execute(
                "SELECT record_id, source_dataset, source_file, title_clean, salary_value_type, "
                "skills_tokens_json, skill_ids_json, source_row_json "
                f"FROM {quote_identifier(AUDIT_TABLE)} WHERE record_id = ?",
                (record_id,),
            ).fetchone()
            if stored is None:
                raise RuntimeError(f"Post-load audit sample is missing: {record_id}")
            for field in expected:
                if stored[field] != (expected[field] if expected[field] != "" else None):
                    raise RuntimeError(f"Post-load value mismatch for {record_id}/{field}")

        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise RuntimeError(f"SQLite integrity_check failed: {integrity[0] if integrity else 'no result'}")
        final_counts = sqlite_database.query_table_counts(connection)
        connection.close()
        connection = None

        if database_path.exists() and not replace_existing:
            raise FileExistsError(f"SQLite database appeared during build; refusing to replace: {database_path}")
        os.replace(temporary_database, database_path)
        return {
            "database": str(database_path),
            "status": "created",
            "engine": "SQLite",
            "rows": rows_loaded,
            "cleaned_columns": len(fieldnames),
            "job_skill_links": skill_links_loaded,
            "skill_observation_rows": len(observation_rows),
            "source_sha256": actual_sha256,
            "source_ref": summary["source_ref"],
            "integrity_check": "ok",
            "foreign_key_violations": 0,
            "row_counts": final_counts,
            "size_bytes": database_path.stat().st_size,
        }
    except Exception:
        if connection is not None:
            connection.close()
        for candidate in (
            temporary_database,
            Path(str(temporary_database) + "-journal"),
            Path(str(temporary_database) + "-wal"),
            Path(str(temporary_database) + "-shm"),
        ):
            try:
                candidate.unlink()
            except FileNotFoundError:
                pass
        raise


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the relational SQLite database from the full cleaned-audit CSV."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET, help="Complete jobs_cleaned_audited.csv.gz input.")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE, help="SQLite output path (Git-ignored under data/processed by default).")
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY, help="Cleaning summary whose SHA-256 and row count must match the dataset.")
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST, help="Source file manifest used for provenance metadata.")
    parser.add_argument("--replace", action="store_true", help="Atomically replace an existing database only after the rebuilt file passes validation.")
    parser.add_argument("--quiet", action="store_true", help="Suppress periodic import progress messages.")
    return parser


def main(arguments: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(arguments)
    try:
        result = build_database(
            dataset_path=args.dataset,
            database_path=args.database,
            summary_path=args.summary,
            source_manifest_path=args.source_manifest,
            replace_existing=args.replace,
            progress=not args.quiet,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
