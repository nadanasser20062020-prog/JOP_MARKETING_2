from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_DIRECTORY))

from backend.database import connect_to_database, resolve_database_path

MIGRATIONS_DIRECTORY = PROJECT_ROOT_DIRECTORY / "database" / "migrations"
API_ROLLUPS_SQL_PATH = MIGRATIONS_DIRECTORY / "refresh_api_rollups.sql"
DEFAULT_PROCESSED_DIRECTORY = PROJECT_ROOT_DIRECTORY / "data" / "processed"
DEFAULT_ARCHIVE_DIRECTORY = DEFAULT_PROCESSED_DIRECTORY / "full_archive_parquet_v1_20261028"
REFERENCE_DIRECTORY = PROJECT_ROOT_DIRECTORY / "data" / "reference"
ARCHIVE_TABLE_NAMES = (
    "data_sources",
    "source_files",
    "import_runs",
    "import_run_files",
    "skills",
    "skill_aliases",
    "jobs",
    "job_skills",
    "skill_observations",
    "learning_resources",
    "learning_resource_skills",
    "learning_resource_languages",
)
ARCHIVE_METADATA_SOURCE_DATASET = "archive_integrity"
SKILL_CATALOG_FILE_PATH = REFERENCE_DIRECTORY / "skill_catalog.csv"
SKILL_ALIASES_FILE_PATH = REFERENCE_DIRECTORY / "skill_aliases.csv"
LEARNING_RESOURCES_FILE_PATH = REFERENCE_DIRECTORY / "learning_resources.json"
LEARNING_RESOURCES_CSV_FILE_PATH = REFERENCE_DIRECTORY / "learning_resources.csv"

JOB_FIELD_NAMES = (
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
)

JOB_SKILL_FIELD_NAMES = (
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
)

SKILL_CATALOG_FIELD_NAMES = (
    "skill_id",
    "canonical_name",
    "category",
    "match_policy",
    "review_status",
    "observed_alias_count",
    "observed_source_count",
    "observed_job_skill_occurrences",
    "notes",
)

SKILL_ALIAS_FIELD_NAMES = (
    "alias_normalized",
    "alias_label",
    "skill_id",
    "alias_type",
    "match_policy",
    "review_status",
    "observed_source_count",
    "observed_job_skill_occurrences",
    "notes",
)

SKILL_OBSERVATION_FIELD_NAMES = (
    "source_dataset",
    "skill_raw",
    "skill_normalized",
    "occurrence_count",
)

LEARNING_RESOURCE_FIELD_NAMES = (
    "resource_id",
    "title",
    "provider",
    "resource_type",
    "level",
    "access_status",
    "cost_status",
    "account_requirement",
    "credential",
    "resource_url",
    "verification_status",
    "verified_on",
    "notes",
)

ALLOWED_COST_STATUSES = {
    "free_verified",
    "some_free_options",
    "conditional_or_mixed",
    "cost_unverified",
}

SOURCE_METADATA = {
    "international_jobs": (
        "International Tech Jobs",
        "Historical 2023 sample.",
    ),
    "merged_tech_jobs": (
        "Merged Tech Jobs",
        "Merged workbook; source-date semantics are not established.",
    ),
    "arab_tech_jobs": (
        "Arab Tech Jobs",
        "Regional sample with partial posting-date coverage.",
    ),
    "cybersecurity_jobs": (
        "Cybersecurity Jobs",
        "Regional sample with no posting-date field.",
    ),
    "remote_tech_jobs": (
        "Remote Tech Jobs",
        "Latest available export; listing activity is unverified.",
    ),
    "startup_jobs": (
        "Startup Jobs",
        "Latest available export; listing activity is unverified.",
    ),
    "jooble_careerjet_jobs": (
        "Jooble and Careerjet Tech Jobs",
        "Latest available export; listing activity is unverified.",
    ),
}

LATEST_EXPORT_DATASETS = {
    "remote_tech_jobs",
    "startup_jobs",
    "jooble_careerjet_jobs",
}
OTHER_SNAPSHOT_DATASETS = {
    "merged_tech_jobs",
    "arab_tech_jobs",
    "cybersecurity_jobs",
}

DOMAIN_TABLE_NAMES = (
    "data_sources",
    "source_files",
    "import_runs",
    "import_run_files",
    "skills",
    "skill_aliases",
    "jobs",
    "job_cleaning_audit",
    "job_skills",
    "skill_observations",
    "learning_resources",
    "learning_resource_skills",
    "learning_resource_languages",
)

TABLE_INSERT_SQL = {
    "data_sources": (
        "INSERT INTO data_sources (source_dataset, display_name, notes) VALUES (?, ?, ?) "
        "ON CONFLICT (source_dataset) DO UPDATE SET "
        "display_name = excluded.display_name, notes = excluded.notes"
    ),
    "source_files": (
        "INSERT INTO source_files "
        "(source_dataset, source_file, snapshot_group, snapshot_type, notes) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT (source_dataset, source_file) DO UPDATE SET "
        "snapshot_group = excluded.snapshot_group, "
        "snapshot_type = excluded.snapshot_type, notes = excluded.notes"
    ),
    "skills": (
        "INSERT INTO skills "
        "(skill_id, canonical_name, category, match_policy, review_status, "
        "observed_alias_count, observed_source_count, observed_job_skill_occurrences, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (skill_id) DO UPDATE SET "
        "canonical_name = excluded.canonical_name, category = excluded.category, "
        "match_policy = excluded.match_policy, review_status = excluded.review_status, "
        "observed_alias_count = excluded.observed_alias_count, "
        "observed_source_count = excluded.observed_source_count, "
        "observed_job_skill_occurrences = excluded.observed_job_skill_occurrences, "
        "notes = excluded.notes"
    ),
    "skill_aliases": (
        "INSERT INTO skill_aliases "
        "(alias_normalized, alias_label, skill_id, alias_type, match_policy, review_status, "
        "observed_source_count, observed_job_skill_occurrences, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (alias_normalized, skill_id) DO UPDATE SET "
        "alias_label = excluded.alias_label, alias_type = excluded.alias_type, "
        "match_policy = excluded.match_policy, review_status = excluded.review_status, "
        "observed_source_count = excluded.observed_source_count, "
        "observed_job_skill_occurrences = excluded.observed_job_skill_occurrences, "
        "notes = excluded.notes"
    ),
    "jobs": (
        "INSERT INTO jobs (" + ", ".join(JOB_FIELD_NAMES) + ") VALUES ("
        + ", ".join("?" for _ in JOB_FIELD_NAMES)
        + ") ON CONFLICT (record_id) DO UPDATE SET "
        + ", ".join(
            f"{field_name} = excluded.{field_name}"
            for field_name in JOB_FIELD_NAMES
            if field_name != "record_id"
        )
    ),
    "job_skills": (
        "INSERT INTO job_skills (" + ", ".join(JOB_SKILL_FIELD_NAMES) + ") VALUES ("
        + ", ".join("?" for _ in JOB_SKILL_FIELD_NAMES)
        + ") ON CONFLICT (record_id, skill_id) DO UPDATE SET "
        + ", ".join(
            f"{field_name} = excluded.{field_name}"
            for field_name in JOB_SKILL_FIELD_NAMES
            if field_name not in {"record_id", "skill_id"}
        )
    ),
    "skill_observations": (
        "INSERT INTO skill_observations "
        "(source_dataset, skill_raw, skill_normalized, occurrence_count) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT (source_dataset, skill_normalized, skill_raw) DO UPDATE SET "
        "occurrence_count = excluded.occurrence_count"
    ),
    "learning_resources": (
        "INSERT INTO learning_resources (" + ", ".join(LEARNING_RESOURCE_FIELD_NAMES) + ") VALUES ("
        + ", ".join("?" for _ in LEARNING_RESOURCE_FIELD_NAMES)
        + ") ON CONFLICT (resource_id) DO UPDATE SET "
        + ", ".join(
            f"{field_name} = excluded.{field_name}"
            for field_name in LEARNING_RESOURCE_FIELD_NAMES
            if field_name != "resource_id"
        )
    ),
}


class DatasetAlreadyLoadedError(ValueError):
    pass


def timestamp_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def apply_migrations(connection):
    connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "migration_version INTEGER PRIMARY KEY, "
        "migration_name TEXT NOT NULL UNIQUE, "
        "checksum_sha256 TEXT NOT NULL, "
        "applied_at TEXT NOT NULL)"
    )
    migration_paths = sorted(MIGRATIONS_DIRECTORY.glob("[0-9]*_*.sql"))
    if not migration_paths:
        raise FileNotFoundError(f"No SQLite migration files found in {MIGRATIONS_DIRECTORY}")

    for migration_path in migration_paths:
        version_text = migration_path.name.split("_", maxsplit=1)[0]
        if not version_text.isdigit():
            raise ValueError(f"Migration name must start with a numeric version: {migration_path.name}")
        migration_version = int(version_text)
        migration_sql = migration_path.read_text(encoding="utf-8")
        checksum_sha256 = hashlib.sha256(migration_sql.encode("utf-8")).hexdigest()
        applied_migration = connection.execute(
            "SELECT migration_name, checksum_sha256 FROM schema_migrations "
            "WHERE migration_version = ?",
            (migration_version,),
        ).fetchone()
        if applied_migration is not None:
            if (
                applied_migration["migration_name"] != migration_path.name
                or applied_migration["checksum_sha256"] != checksum_sha256
            ):
                raise ValueError(
                    f"Applied migration {migration_version} changed. Add a new migration instead."
                )
            continue

        migration_record = (
            f"INSERT INTO schema_migrations "
            f"(migration_version, migration_name, checksum_sha256, applied_at) VALUES "
            f"({migration_version}, {sql_text_literal(migration_path.name)}, "
            f"{sql_text_literal(checksum_sha256)}, {sql_text_literal(timestamp_utc())});"
        )
        try:
            connection.executescript(
                "BEGIN IMMEDIATE;\n"
                + migration_sql
                + "\n"
                + migration_record
                + "\nCOMMIT;"
            )
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise


def sql_text_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def initialize_database(database_path=None):
    resolved_path = resolve_database_path(database_path)
    connection = connect_to_database(resolved_path, create_if_missing=True)
    try:
        apply_migrations(connection)
        return resolved_path
    finally:
        connection.close()


def select_import_source(source_mode, processed_directory, archive_directory=None):
    processed_directory = Path(processed_directory).expanduser().resolve()
    archive_directory = Path(archive_directory or DEFAULT_ARCHIVE_DIRECTORY).expanduser().resolve()
    processed_job_paths = sorted(processed_directory.glob("jobs_*.csv.gz"))
    if source_mode == "archive":
        return "archive", validate_archive_input_paths(archive_directory)
    if source_mode == "processed":
        return "processed", validate_processed_input_paths(processed_directory, processed_job_paths)
    if source_mode != "auto":
        raise ValueError(f"Unsupported import source: {source_mode}")
    if (archive_directory / "manifest.json").is_file():
        return "archive", validate_archive_input_paths(archive_directory)
    if processed_job_paths:
        return "processed", validate_processed_input_paths(processed_directory, processed_job_paths)
    raise FileNotFoundError(
        "No full local archive or complete normalized job data was found. "
        f"Place the verified Parquet archive in {archive_directory} or provide full processed files. "
        "Automatic loading requires complete input data and does not substitute partial records."
    )


def validate_processed_input_paths(processed_directory, processed_job_paths):
    if not processed_job_paths:
        raise FileNotFoundError(
            f"No normalized jobs_*.csv.gz files found in {processed_directory}. "
            "Place the complete Parquet archive in the configured archive directory or run the data-cleaning pipeline."
        )
    required_paths = [
        *processed_job_paths,
        processed_directory / "job_skills.csv.gz",
        processed_directory / "skill_observations.csv.gz",
        SKILL_CATALOG_FILE_PATH,
        SKILL_ALIASES_FILE_PATH,
        LEARNING_RESOURCES_FILE_PATH,
        LEARNING_RESOURCES_CSV_FILE_PATH,
    ]
    missing_paths = [path for path in required_paths if not path.is_file()]
    if missing_paths:
        missing_names = ", ".join(str(path) for path in missing_paths)
        raise FileNotFoundError(f"Required local processed/reference inputs are missing: {missing_names}")
    return required_paths


def import_input_paths(source_mode, processed_directory, selected_paths):
    return selected_paths


def sha256_file(file_path):
    checksum = hashlib.sha256()
    with Path(file_path).open("rb") as source_file:
        for data_chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            checksum.update(data_chunk)
    return checksum.hexdigest()


def validate_archive_input_paths(archive_directory):
    archive_directory = Path(archive_directory).expanduser().resolve()
    manifest_path = archive_directory / "manifest.json"
    checksums_path = archive_directory / "checksums.sha256"
    required_paths = [manifest_path, checksums_path]
    missing_paths = [path for path in required_paths if not path.is_file()]
    if missing_paths:
        raise FileNotFoundError(
            "Full Parquet archive is missing required package files: "
            + ", ".join(str(path) for path in missing_paths)
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("package_name") != "full_archive_parquet_v1":
        raise ValueError("Unsupported full Parquet archive package name")
    archive_tables = manifest.get("tables")
    if not isinstance(archive_tables, dict) or set(archive_tables) != set(ARCHIVE_TABLE_NAMES):
        raise ValueError("Full Parquet archive manifest does not contain the expected twelve tables")

    checksums = {}
    archive_input_paths = []
    for line_number, line in enumerate(checksums_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        checksum_parts = line.split(maxsplit=1)
        if len(checksum_parts) != 2:
            raise ValueError(f"Malformed archive checksum record on line {line_number}")
        expected_checksum, relative_name = checksum_parts
        relative_path = Path(relative_name.strip())
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"Unsafe archive checksum path on line {line_number}")
        archive_file_path = (archive_directory / relative_path).resolve()
        if archive_directory not in archive_file_path.parents:
            raise ValueError(f"Archive checksum path escapes the package directory: {relative_name}")
        if not archive_file_path.is_file():
            raise FileNotFoundError(f"Archive package file is missing: {archive_file_path}")
        actual_checksum = sha256_file(archive_file_path)
        if actual_checksum != expected_checksum:
            raise ValueError(f"Archive checksum mismatch for {archive_file_path.name}")
        checksums[relative_path.as_posix()] = expected_checksum
        archive_input_paths.append(archive_file_path)

    if not checksums:
        raise ValueError("Full Parquet archive checksums file is empty")
    for table_name in ARCHIVE_TABLE_NAMES:
        table_info = archive_tables[table_name]
        table_file_name = table_info.get("file")
        if table_file_name != f"{table_name}.parquet":
            raise ValueError(f"Unexpected Parquet file name for archive table {table_name}")
        if checksums.get(table_file_name) != table_info.get("sha256"):
            raise ValueError(f"Archive checksum manifest disagrees for {table_file_name}")
        if not isinstance(table_info.get("row_count"), int) or table_info["row_count"] < 0:
            raise ValueError(f"Invalid row count for archive table {table_name}")

    archive_totals = manifest.get("totals", {})
    if archive_totals.get("jobs") != archive_tables["jobs"]["row_count"]:
        raise ValueError("Archive job total does not match the jobs Parquet table")
    if archive_totals.get("job_skills") != archive_tables["job_skills"]["row_count"]:
        raise ValueError("Archive job-skill total does not match the job_skills Parquet table")

    local_reference_paths = [
        LEARNING_RESOURCES_FILE_PATH,
        LEARNING_RESOURCES_CSV_FILE_PATH,
    ]
    missing_reference_paths = [path for path in local_reference_paths if not path.is_file()]
    if missing_reference_paths:
        raise FileNotFoundError(
            "Full archive loading requires the reviewed local reference files: "
            + ", ".join(str(path) for path in missing_reference_paths)
        )

    return sorted(
        {*archive_input_paths, *local_reference_paths, manifest_path, checksums_path},
        key=str,
    )


def calculate_source_fingerprint(input_paths):
    fingerprint = hashlib.sha256()
    for input_path in sorted((Path(path).resolve() for path in input_paths), key=str):
        fingerprint.update(str(input_path).encode("utf-8"))
        fingerprint.update(b"\0")
        fingerprint.update(sha256_file(input_path).encode("ascii"))
        fingerprint.update(b"\n")
    return fingerprint.hexdigest()


def query_table_counts(connection):
    return {
        table_name: connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        for table_name in DOMAIN_TABLE_NAMES
    }


def database_contains_data(connection):
    for table_name in ("data_sources", "skills", "jobs", "learning_resources"):
        if connection.execute(f"SELECT 1 FROM {table_name} LIMIT 1").fetchone() is not None:
            return True
    return False


def matching_successful_import(connection, source_fingerprint):
    return connection.execute(
        "SELECT import_run_id FROM import_runs "
        "WHERE source_fingerprint = ? AND run_status = 'succeeded' "
        "ORDER BY import_run_id DESC LIMIT 1",
        (source_fingerprint,),
    ).fetchone()


def clear_domain_data(connection):
    for table_name in (
        "api_scope_skill_rollups",
        "api_scope_rollups",
        "api_role_skill_rollups",
        "api_role_scope_rollups",
        "api_source_field_coverage",
        "api_historical_month_rollups",
        "import_run_files",
        "job_skills",
        "job_cleaning_audit",
        "jobs",
        "skill_observations",
        "learning_resource_skills",
        "learning_resource_languages",
        "learning_resources",
        "skill_aliases",
        "skills",
        "source_files",
        "data_sources",
        "import_runs",
    ):
        connection.execute(f"DELETE FROM {table_name}")


def create_import_run(connection, pipeline_version, source_fingerprint, notes):
    started_at = timestamp_utc()
    insert_result = connection.execute(
        "INSERT INTO import_runs "
        "(run_status, started_at, pipeline_version, source_fingerprint, notes) "
        "VALUES ('running', ?, ?, ?, ?)",
        (started_at, pipeline_version, source_fingerprint, notes),
    )
    return insert_result.lastrowid, started_at


def record_failed_import(connection, pipeline_version, source_fingerprint, started_at, error):
    connection.execute(
        "INSERT INTO import_runs "
        "(run_status, started_at, finished_at, pipeline_version, source_fingerprint, notes) "
        "VALUES ('failed', ?, ?, ?, ?, ?)",
        (
            started_at,
            timestamp_utc(),
            pipeline_version,
            source_fingerprint,
            f"Import rolled back: {type(error).__name__}: {error}",
        ),
    )
    connection.commit()


def add_data_source(connection, source_dataset, display_name=None, notes=None):
    known_metadata = SOURCE_METADATA.get(source_dataset)
    if known_metadata is not None:
        display_name = display_name or known_metadata[0]
        notes = notes or known_metadata[1]
    display_name = display_name or source_dataset.replace("_", " ").title()
    connection.execute(
        TABLE_INSERT_SQL["data_sources"],
        (source_dataset, display_name, notes),
    )


def add_source_file(connection, source_dataset, source_file, snapshot_group, snapshot_type, notes):
    connection.execute(
        TABLE_INSERT_SQL["source_files"],
        (source_dataset, source_file, snapshot_group, snapshot_type, notes),
    )


def register_reference_data_source(connection, file_row_counts):
    add_data_source(
        connection,
        "curated_reference_data",
        "Curated Reference Data",
        "Project-reviewed skill taxonomy and learning-resource metadata.",
    )
    for source_file, row_count in file_row_counts.items():
        add_source_file(
            connection,
            "curated_reference_data",
            source_file,
            "curated_reference",
            "project_reference",
            f"Local curated reference file; {row_count} records loaded.",
        )


def required_csv_reader(source_file, required_field_names, file_path):
    reader = csv.DictReader(source_file, strict=True)
    if reader.fieldnames is None:
        raise ValueError(f"CSV input has no header: {file_path}")
    missing_field_names = [field_name for field_name in required_field_names if field_name not in reader.fieldnames]
    if missing_field_names:
        raise ValueError(f"{file_path} is missing required fields: {missing_field_names}")
    return reader


def parse_nonnegative_integer(value, field_name, file_path):
    cleaned_value = str(value or "").strip()
    if not cleaned_value:
        return 0
    try:
        parsed_value = int(cleaned_value)
    except ValueError as error:
        raise ValueError(f"Invalid integer in {file_path} field {field_name}: {cleaned_value!r}") from error
    if parsed_value < 0:
        raise ValueError(f"Negative count in {file_path} field {field_name}: {parsed_value}")
    return parsed_value


def load_skill_catalog(connection):
    loaded_rows = 0
    with SKILL_CATALOG_FILE_PATH.open("r", encoding="utf-8-sig", newline="") as source_file:
        reader = required_csv_reader(source_file, SKILL_CATALOG_FIELD_NAMES, SKILL_CATALOG_FILE_PATH)
        for row in reader:
            skill_identifier = (row.get("skill_id") or "").strip()
            canonical_name = (row.get("canonical_name") or "").strip()
            if not skill_identifier or not canonical_name:
                raise ValueError(f"Skill catalog row {reader.line_num} has no skill_id or canonical_name")
            connection.execute(
                TABLE_INSERT_SQL["skills"],
                (
                    skill_identifier,
                    canonical_name,
                    (row.get("category") or "uncategorized").strip() or "uncategorized",
                    (row.get("match_policy") or "exact_only").strip(),
                    (row.get("review_status") or "needs_review").strip(),
                    parse_nonnegative_integer(
                        row.get("observed_alias_count"),
                        "observed_alias_count",
                        SKILL_CATALOG_FILE_PATH,
                    ),
                    parse_nonnegative_integer(
                        row.get("observed_source_count"),
                        "observed_source_count",
                        SKILL_CATALOG_FILE_PATH,
                    ),
                    parse_nonnegative_integer(
                        row.get("observed_job_skill_occurrences"),
                        "observed_job_skill_occurrences",
                        SKILL_CATALOG_FILE_PATH,
                    ),
                    optional_text(row.get("notes")),
                ),
            )
            loaded_rows += 1
    return loaded_rows


def load_skill_aliases(connection):
    loaded_rows = 0
    with SKILL_ALIASES_FILE_PATH.open("r", encoding="utf-8-sig", newline="") as source_file:
        reader = required_csv_reader(source_file, SKILL_ALIAS_FIELD_NAMES, SKILL_ALIASES_FILE_PATH)
        for row in reader:
            alias_normalized = (row.get("alias_normalized") or "").strip()
            alias_label = (row.get("alias_label") or "").strip()
            skill_identifier = (row.get("skill_id") or "").strip()
            if not alias_normalized or not alias_label or not skill_identifier:
                raise ValueError(f"Skill alias row {reader.line_num} has a missing key field")
            connection.execute(
                TABLE_INSERT_SQL["skill_aliases"],
                (
                    alias_normalized,
                    alias_label,
                    skill_identifier,
                    (row.get("alias_type") or "observed_unreviewed_exact").strip(),
                    (row.get("match_policy") or "exact_only").strip(),
                    (row.get("review_status") or "needs_review").strip(),
                    parse_nonnegative_integer(
                        row.get("observed_source_count"),
                        "observed_source_count",
                        SKILL_ALIASES_FILE_PATH,
                    ),
                    parse_nonnegative_integer(
                        row.get("observed_job_skill_occurrences"),
                        "observed_job_skill_occurrences",
                        SKILL_ALIASES_FILE_PATH,
                    ),
                    optional_text(row.get("notes")),
                ),
            )
            loaded_rows += 1
    return loaded_rows


def optional_text(value):
    if value is None:
        return None
    text_value = str(value)
    return text_value if text_value.strip() else None


def read_learning_resource_language_labels():
    language_labels_by_resource = {}
    with LEARNING_RESOURCES_CSV_FILE_PATH.open(
        "r", encoding="utf-8-sig", newline=""
    ) as source_file:
        reader = required_csv_reader(
            source_file,
            ("resource_id", "languages"),
            LEARNING_RESOURCES_CSV_FILE_PATH,
        )
        for row in reader:
            resource_identifier = (row.get("resource_id") or "").strip()
            if not resource_identifier or resource_identifier in language_labels_by_resource:
                raise ValueError(
                    f"Missing or duplicate resource_id in {LEARNING_RESOURCES_CSV_FILE_PATH}"
                )
            language_labels = [
                language_label.strip()
                for language_label in (row.get("languages") or "").split(";")
                if language_label.strip()
            ]
            if not language_labels:
                raise ValueError(
                    f"Resource {resource_identifier} has no language labels in "
                    f"{LEARNING_RESOURCES_CSV_FILE_PATH}"
                )
            language_labels_by_resource[resource_identifier] = language_labels
    return language_labels_by_resource


def validate_learning_resource(resource, resource_number, language_labels):
    resource_identifier = str(resource.get("resource_id", "")).strip()
    if not resource_identifier:
        raise ValueError(f"Learning resource {resource_number} has no resource_id")
    missing_fields = [
        field_name
        for field_name in LEARNING_RESOURCE_FIELD_NAMES
        if not str(resource.get(field_name, "")).strip()
    ]
    if missing_fields:
        raise ValueError(f"Learning resource {resource_identifier} is missing fields: {missing_fields}")
    if resource["cost_status"] not in ALLOWED_COST_STATUSES:
        raise ValueError(
            f"Learning resource {resource_identifier} has unsupported cost_status: "
            f"{resource['cost_status']!r}"
        )
    parsed_url = urlparse(resource["resource_url"])
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValueError(f"Learning resource {resource_identifier} must have a valid HTTPS URL")
    skill_identifiers = resource.get("skill_ids")
    source_language_labels = resource.get("languages")
    if not isinstance(source_language_labels, list) or not source_language_labels:
        raise ValueError(f"Learning resource {resource_identifier} must have source language labels")
    expected_language_labels = [
        language_label.strip()
        for source_label in source_language_labels
        for language_label in str(source_label).split(";")
        if language_label.strip()
    ]
    if not isinstance(skill_identifiers, list) or not skill_identifiers:
        raise ValueError(f"Learning resource {resource_identifier} must have at least one linked skill")
    if not language_labels:
        raise ValueError(f"Learning resource {resource_identifier} must have at least one language label")
    if len(skill_identifiers) != len(set(skill_identifiers)):
        raise ValueError(f"Learning resource {resource_identifier} repeats a skill identifier")
    if language_labels != expected_language_labels:
        raise ValueError(
            f"Language labels in the CSV and JSON references disagree for {resource_identifier}"
        )
    if len(language_labels) != len(set(language_labels)):
        raise ValueError(f"Learning resource {resource_identifier} repeats a language label")
    return skill_identifiers, language_labels


def load_learning_resources(connection):
    resource_document = json.loads(LEARNING_RESOURCES_FILE_PATH.read_text(encoding="utf-8"))
    resource_rows = resource_document.get("resources")
    if not isinstance(resource_rows, list):
        raise ValueError(f"Learning-resource file has no resources list: {LEARNING_RESOURCES_FILE_PATH}")
    language_labels_by_resource = read_learning_resource_language_labels()
    resource_identifiers = {
        str(resource.get("resource_id", "")).strip()
        for resource in resource_rows
        if isinstance(resource, dict)
    }
    if resource_identifiers != set(language_labels_by_resource):
        raise ValueError("Learning-resource JSON and CSV files contain different resource ids")

    connection.execute("DELETE FROM learning_resource_skills")
    connection.execute("DELETE FROM learning_resource_languages")
    loaded_resources = 0
    loaded_resource_skills = 0
    loaded_resource_languages = 0
    seen_resource_identifiers = set()

    for resource_number, resource in enumerate(resource_rows, start=1):
        if not isinstance(resource, dict):
            raise ValueError(f"Learning resource {resource_number} is not an object")
        resource_identifier = str(resource["resource_id"]).strip()
        language_labels = language_labels_by_resource[resource_identifier]
        skill_identifiers, language_labels = validate_learning_resource(
            resource, resource_number, language_labels
        )
        if resource_identifier in seen_resource_identifiers:
            raise ValueError(f"Duplicate learning resource id: {resource_identifier}")
        seen_resource_identifiers.add(resource_identifier)
        connection.execute(
            TABLE_INSERT_SQL["learning_resources"],
            tuple(str(resource[field_name]).strip() for field_name in LEARNING_RESOURCE_FIELD_NAMES),
        )
        connection.executemany(
            "INSERT INTO learning_resource_skills (resource_id, skill_id) VALUES (?, ?) "
            "ON CONFLICT (resource_id, skill_id) DO NOTHING",
            [(resource_identifier, str(skill_identifier).strip()) for skill_identifier in skill_identifiers],
        )
        connection.executemany(
            "INSERT INTO learning_resource_languages (resource_id, language_label) VALUES (?, ?) "
            "ON CONFLICT (resource_id, language_label) DO NOTHING",
            [(resource_identifier, str(language_label).strip()) for language_label in language_labels],
        )
        loaded_resources += 1
        loaded_resource_skills += len(skill_identifiers)
        loaded_resource_languages += len(language_labels)

    return {
        "learning_resources": loaded_resources,
        "learning_resource_skills": loaded_resource_skills,
        "learning_resource_languages": loaded_resource_languages,
    }


def register_import_run_files(connection, import_run_id, files):
    for file_record in files:
        rows_read = int(file_record["rows_read"])
        rows_loaded = int(file_record["rows_loaded"])
        rows_rejected = int(file_record.get("rows_rejected", 0))
        if rows_loaded + rows_rejected > rows_read:
            raise ValueError(
                f"Import counts exceed rows read for "
                f"{file_record['source_dataset']}/{file_record['source_file']}"
            )
        connection.execute(
            "INSERT INTO import_run_files "
            "(import_run_id, source_dataset, source_file, rows_read, rows_loaded, rows_rejected, "
            "import_status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                import_run_id,
                file_record["source_dataset"],
                file_record["source_file"],
                rows_read,
                rows_loaded,
                rows_rejected,
                file_record.get("import_status", "succeeded"),
                file_record.get("notes"),
            ),
        )


def source_snapshot_group(source_dataset):
    if source_dataset == "international_jobs":
        return "historical_sample"
    if source_dataset in LATEST_EXPORT_DATASETS:
        return "latest_export_unverified"
    if source_dataset in OTHER_SNAPSHOT_DATASETS:
        return "other_snapshots_unverified"
    return "source_snapshot_unverified"


def open_gzip_csv(file_path, required_field_names):
    source_file = gzip.open(file_path, "rt", encoding="utf-8-sig", newline="")
    reader = required_csv_reader(source_file, required_field_names, file_path)
    return source_file, reader


def collect_processed_job_metadata(processed_job_paths):
    source_file_counts = Counter()
    source_snapshot_types = {}
    source_dataset_names = set()

    for job_file_path in processed_job_paths:
        source_file, reader = open_gzip_csv(job_file_path, JOB_FIELD_NAMES)
        with source_file:
            for row in reader:
                source_dataset = (row.get("source_dataset") or "").strip()
                source_filename = (row.get("source_file") or "").strip()
                snapshot_type = (row.get("snapshot_type") or "").strip()
                if not source_dataset or not source_filename:
                    raise ValueError(
                        f"Missing source_dataset or source_file in {job_file_path} row {reader.line_num}"
                    )
                source_dataset_names.add(source_dataset)
                source_key = (source_dataset, source_filename)
                source_file_counts[source_key] += 1
                previous_snapshot_type = source_snapshot_types.setdefault(source_key, snapshot_type)
                if previous_snapshot_type != snapshot_type:
                    raise ValueError(
                        f"Inconsistent snapshot_type for {source_dataset}/{source_filename}"
                    )

    return source_file_counts, source_snapshot_types, source_dataset_names


def collect_observation_source_names(observation_file_path):
    source_dataset_names = set()
    source_file, reader = open_gzip_csv(observation_file_path, SKILL_OBSERVATION_FIELD_NAMES)
    with source_file:
        for row in reader:
            source_dataset = (row.get("source_dataset") or "").strip()
            if not source_dataset:
                raise ValueError(
                    f"Missing source_dataset in {observation_file_path} row {reader.line_num}"
                )
            source_dataset_names.add(source_dataset)
    return source_dataset_names


def register_processed_sources(
    connection,
    source_file_counts,
    source_snapshot_types,
    source_dataset_names,
):
    for source_dataset in sorted(source_dataset_names):
        add_data_source(connection, source_dataset)

    for (source_dataset, source_file), row_count in sorted(source_file_counts.items()):
        snapshot_type = source_snapshot_types[(source_dataset, source_file)] or None
        add_source_file(
            connection,
            source_dataset,
            source_file,
            source_snapshot_group(source_dataset),
            snapshot_type,
            f"Imported from normalized local staging data; {row_count} job rows. "
            "Listing activity remains unverified.",
        )


def load_processed_jobs(connection, processed_job_paths):
    loaded_rows = 0
    insert_sql = TABLE_INSERT_SQL["jobs"]
    batch_rows = []
    batch_size = 2000

    for job_file_path in processed_job_paths:
        source_file, reader = open_gzip_csv(job_file_path, JOB_FIELD_NAMES)
        with source_file:
            for row in reader:
                record_identifier = (row.get("record_id") or "").strip()
                source_dataset = (row.get("source_dataset") or "").strip()
                source_filename = (row.get("source_file") or "").strip()
                if not record_identifier or not source_dataset or not source_filename:
                    raise ValueError(
                        f"Missing job key/provenance in {job_file_path} row {reader.line_num}"
                    )
                try:
                    source_row_number = int(str(row.get("source_row_number") or "").strip())
                except ValueError as error:
                    raise ValueError(
                        f"Invalid source_row_number in {job_file_path} row {reader.line_num}"
                    ) from error
                if source_row_number < 1:
                    raise ValueError(
                        f"source_row_number must be positive in {job_file_path} row {reader.line_num}"
                    )
                batch_rows.append(
                    tuple(
                        record_identifier
                        if field_name == "record_id"
                        else source_dataset
                        if field_name == "source_dataset"
                        else source_filename
                        if field_name == "source_file"
                        else source_row_number
                        if field_name == "source_row_number"
                        else optional_text(row.get(field_name))
                        for field_name in JOB_FIELD_NAMES
                    )
                )
                loaded_rows += 1
                if len(batch_rows) >= batch_size:
                    connection.executemany(insert_sql, batch_rows)
                    batch_rows.clear()

    if batch_rows:
        connection.executemany(insert_sql, batch_rows)
    return loaded_rows


def load_processed_job_skills(connection, job_skills_file_path):
    source_file, reader = open_gzip_csv(job_skills_file_path, JOB_SKILL_FIELD_NAMES)
    loaded_rows = 0
    batch_rows = []
    batch_size = 5000
    with source_file:
        for row in reader:
            cleaned_values = tuple(optional_text(row.get(field_name)) for field_name in JOB_SKILL_FIELD_NAMES)
            if any(cleaned_values[index] is None for index in range(9)):
                raise ValueError(
                    f"Missing job-skill key or policy field in "
                    f"{job_skills_file_path} row {reader.line_num}"
                )
            batch_rows.append(cleaned_values)
            loaded_rows += 1
            if len(batch_rows) >= batch_size:
                connection.executemany(TABLE_INSERT_SQL["job_skills"], batch_rows)
                batch_rows.clear()
    if batch_rows:
        connection.executemany(TABLE_INSERT_SQL["job_skills"], batch_rows)
    return loaded_rows


def load_processed_skill_observations(connection, observation_file_path):
    source_file, reader = open_gzip_csv(observation_file_path, SKILL_OBSERVATION_FIELD_NAMES)
    loaded_rows = 0
    batch_rows = []
    batch_size = 5000
    with source_file:
        for row in reader:
            source_dataset = (row.get("source_dataset") or "").strip()
            skill_raw = (row.get("skill_raw") or "").strip()
            skill_normalized = (row.get("skill_normalized") or "").strip()
            if not source_dataset or not skill_raw or not skill_normalized:
                raise ValueError(
                    f"Missing skill observation key in "
                    f"{observation_file_path} row {reader.line_num}"
                )
            occurrence_count = parse_nonnegative_integer(
                row.get("occurrence_count"), "occurrence_count", observation_file_path
            )
            batch_rows.append(
                (source_dataset, skill_raw, skill_normalized, occurrence_count)
            )
            loaded_rows += 1
            if len(batch_rows) >= batch_size:
                connection.executemany(TABLE_INSERT_SQL["skill_observations"], batch_rows)
                batch_rows.clear()
    if batch_rows:
        connection.executemany(TABLE_INSERT_SQL["skill_observations"], batch_rows)
    return loaded_rows


def load_processed_dataset(connection, import_run_id, processed_directory, processed_job_paths):
    job_skills_file_path = processed_directory / "job_skills.csv.gz"
    observation_file_path = processed_directory / "skill_observations.csv.gz"
    source_file_counts, source_snapshot_types, job_source_names = collect_processed_job_metadata(
        processed_job_paths
    )
    observation_source_names = collect_observation_source_names(observation_file_path)
    source_dataset_names = job_source_names | observation_source_names
    register_processed_sources(
        connection,
        source_file_counts,
        source_snapshot_types,
        source_dataset_names,
    )
    skill_catalog_count = load_skill_catalog(connection)
    skill_alias_count = load_skill_aliases(connection)
    loaded_observations = load_processed_skill_observations(connection, observation_file_path)
    loaded_jobs = load_processed_jobs(connection, processed_job_paths)
    loaded_job_skills = load_processed_job_skills(connection, job_skills_file_path)
    resource_counts = load_learning_resources(connection)
    register_reference_data_source(
        connection,
        {
            "skill_catalog.csv": skill_catalog_count,
            "skill_aliases.csv": skill_alias_count,
            "skill_observations.csv.gz": loaded_observations,
            "learning_resources.json": resource_counts["learning_resources"],
            "learning_resources.csv": resource_counts["learning_resources"],
        },
    )

    import_files = [
        {
            "source_dataset": source_dataset,
            "source_file": source_file,
            "rows_read": row_count,
            "rows_loaded": row_count,
            "notes": "Normalized job rows; source listing status is not verified.",
        }
        for (source_dataset, source_file), row_count in sorted(source_file_counts.items())
    ]
    import_files.extend(
        (
            {
                "source_dataset": "curated_reference_data",
                "source_file": "skill_catalog.csv",
                "rows_read": skill_catalog_count,
                "rows_loaded": skill_catalog_count,
                "notes": "Curated and observed skill catalog.",
            },
            {
                "source_dataset": "curated_reference_data",
                "source_file": "skill_aliases.csv",
                "rows_read": skill_alias_count,
                "rows_loaded": skill_alias_count,
                "notes": "Normalized skill aliases and match policies.",
            },
            {
                "source_dataset": "curated_reference_data",
                "source_file": "skill_observations.csv.gz",
                "rows_read": loaded_observations,
                "rows_loaded": loaded_observations,
                "notes": "Observed source-skill terms and their frequencies.",
            },
            {
                "source_dataset": "curated_reference_data",
                "source_file": "learning_resources.json",
                "rows_read": resource_counts["learning_resources"],
                "rows_loaded": resource_counts["learning_resources"],
                "notes": "Course-specific access, cost, language, and verification metadata.",
            },
            {
                "source_dataset": "curated_reference_data",
                "source_file": "learning_resources.csv",
                "rows_read": resource_counts["learning_resources"],
                "rows_loaded": resource_counts["learning_resources"],
                "notes": "Semicolon-separated resource language labels; all 37 labels are retained.",
            },
        )
    )
    register_import_run_files(connection, import_run_id, import_files)
    return {
        "loaded_job_rows": loaded_jobs,
        "loaded_job_skill_rows": loaded_job_skills,
        "loaded_skill_observation_rows": loaded_observations,
        "loaded_skill_catalog_rows": skill_catalog_count,
        "loaded_skill_alias_rows": skill_alias_count,
        **resource_counts,
    }


def sqlite_compatible_value(value):
    if value is not None and not isinstance(value, (str, bytes)) and hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def iter_archive_rows(duckdb_connection, archive_directory, table_name, expected_field_names, batch_size=5000):
    if table_name not in ARCHIVE_TABLE_NAMES:
        raise ValueError(f"Unsupported archive table: {table_name}")
    archive_file_path = Path(archive_directory) / f"{table_name}.parquet"
    result = duckdb_connection.execute(
        "SELECT * FROM read_parquet(?)",
        [str(archive_file_path)],
    )
    actual_field_names = tuple(column[0] for column in result.description)
    if actual_field_names != tuple(expected_field_names):
        raise ValueError(
            f"Unexpected columns in {archive_file_path.name}: {actual_field_names}"
        )
    while True:
        batch_rows = result.fetchmany(batch_size)
        if not batch_rows:
            break
        for row in batch_rows:
            yield tuple(sqlite_compatible_value(value) for value in row)


def plain_insert_sql(table_name, field_names):
    if table_name not in ARCHIVE_TABLE_NAMES:
        raise ValueError(f"Unsupported archive table: {table_name}")
    columns = ", ".join(field_names)
    placeholders = ", ".join("?" for _ in field_names)
    return f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"


def insert_archive_table(
    connection,
    duckdb_connection,
    archive_directory,
    table_name,
    expected_field_names,
    insert_sql,
    batch_size=5000,
):
    loaded_rows = 0
    pending_rows = []
    for row in iter_archive_rows(
        duckdb_connection,
        archive_directory,
        table_name,
        expected_field_names,
        batch_size,
    ):
        pending_rows.append(row)
        loaded_rows += 1
        if len(pending_rows) >= batch_size:
            connection.executemany(insert_sql, pending_rows)
            pending_rows.clear()
    if pending_rows:
        connection.executemany(insert_sql, pending_rows)
    return loaded_rows


def load_archive_source_metadata(connection, duckdb_connection, archive_directory, manifest):
    data_source_field_names = (
        "source_dataset",
        "source_kind",
        "snapshot_bucket",
        "date_semantics",
        "listing_status",
        "source_file_count",
        "source_row_count",
    )
    source_file_field_names = (
        "source_file_id",
        "source_dataset",
        "physical_file_name",
        "logical_file_name",
        "file_format",
        "file_role",
        "archive_member_name",
        "byte_size",
        "sha256",
        "source_row_count",
        "archive_member_count",
    )
    source_rows = list(
        iter_archive_rows(
            duckdb_connection,
            archive_directory,
            "data_sources",
            data_source_field_names,
        )
    )
    source_file_rows = list(
        iter_archive_rows(
            duckdb_connection,
            archive_directory,
            "source_files",
            source_file_field_names,
        )
    )
    if len(source_rows) != manifest["tables"]["data_sources"]["row_count"]:
        raise ValueError("Archive data-source row count disagrees with its manifest")
    if len(source_file_rows) != manifest["tables"]["source_files"]["row_count"]:
        raise ValueError("Archive source-file row count disagrees with its manifest")

    source_metadata = {}
    for row in source_rows:
        source_dataset, source_kind, snapshot_bucket, date_semantics, listing_status, source_file_count, source_row_count = row
        if not source_dataset:
            raise ValueError("Archive data_sources contains an empty source_dataset")
        source_metadata[source_dataset] = {
            "snapshot_bucket": snapshot_bucket,
            "source_file_count": source_file_count,
            "source_row_count": source_row_count,
        }
        connection.execute(
            "INSERT INTO data_sources "
            "(source_dataset, display_name, notes, source_kind, snapshot_bucket, date_semantics, "
            "listing_status, source_file_count, source_row_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                source_dataset,
                source_dataset.replace("_", " ").title(),
                optional_text(date_semantics),
                source_kind,
                snapshot_bucket,
                optional_text(date_semantics),
                listing_status,
                source_file_count,
                source_row_count,
            ),
        )

    has_unassigned_source_file = any(row[1] is None for row in source_file_rows)
    if has_unassigned_source_file:
        connection.execute(
            "INSERT INTO data_sources "
            "(source_dataset, display_name, notes, source_kind, snapshot_bucket, date_semantics, "
            "listing_status, source_file_count, source_row_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ARCHIVE_METADATA_SOURCE_DATASET,
                "Archive Integrity Metadata",
                "Local bookkeeping key for an archive-integrity artifact that has no job-data source dataset.",
                "archive_integrity_metadata",
                "archive_integrity",
                "No job rows are associated with this artifact.",
                "not_applicable",
                1,
                0,
            ),
        )
        source_metadata[ARCHIVE_METADATA_SOURCE_DATASET] = {
            "snapshot_bucket": "archive_integrity",
            "source_file_count": 1,
            "source_row_count": 0,
        }

    source_file_lookup = {}
    for row in source_file_rows:
        (
            source_file_id,
            original_source_dataset,
            physical_file_name,
            logical_file_name,
            file_format,
            file_role,
            archive_member_name,
            byte_size,
            checksum_sha256,
            source_row_count,
            archive_member_count,
        ) = row
        source_dataset = original_source_dataset or ARCHIVE_METADATA_SOURCE_DATASET
        source_file = logical_file_name or physical_file_name
        if not source_file_id or not source_file or source_dataset not in source_metadata:
            raise ValueError("Archive source_files contains an invalid source-file key")
        snapshot_group = source_metadata[source_dataset]["snapshot_bucket"]
        source_notes = json.dumps(
            {
                "physical_file_name": physical_file_name,
                "logical_file_name": logical_file_name,
                "file_format": file_format,
                "file_role": file_role,
                "archive_member_name": archive_member_name,
                "byte_size": byte_size,
                "sha256": checksum_sha256,
                "source_row_count": source_row_count,
                "archive_member_count": archive_member_count,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        connection.execute(
            "INSERT INTO source_files "
            "(source_dataset, source_file, snapshot_group, snapshot_type, notes, source_file_id, "
            "source_dataset_original, physical_file_name, logical_file_name, file_format, file_role, "
            "archive_member_name, byte_size, sha256, source_row_count, archive_member_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                source_dataset,
                source_file,
                snapshot_group,
                file_role,
                source_notes,
                source_file_id,
                original_source_dataset,
                physical_file_name,
                logical_file_name,
                file_format,
                file_role,
                archive_member_name,
                byte_size,
                checksum_sha256,
                source_row_count,
                archive_member_count,
            ),
        )
        source_file_lookup[source_file_id] = {
            "source_dataset": source_dataset,
            "source_file": source_file,
            "original_source_dataset": original_source_dataset,
        }
    return source_file_lookup


def register_archive_import_run_files(
    connection,
    import_run_id,
    duckdb_connection,
    archive_directory,
    archive_run_id,
    source_file_lookup,
):
    archive_file_rows = list(
        iter_archive_rows(
            duckdb_connection,
            archive_directory,
            "import_run_files",
            (
                "import_run_id",
                "source_file_id",
                "rows_read",
                "job_rows_emitted",
                "job_skill_rows_emitted",
                "reference_rows_emitted",
                "output_tables",
                "processing_role",
            ),
        )
    )
    expected_row_count = len(source_file_lookup)
    if len(archive_file_rows) != expected_row_count:
        raise ValueError("Archive import-run file count does not match its source-file metadata")
    for row in archive_file_rows:
        (
            archived_run_id,
            source_file_id,
            rows_read,
            job_rows_emitted,
            job_skill_rows_emitted,
            reference_rows_emitted,
            output_tables,
            processing_role,
        ) = row
        if archived_run_id != archive_run_id or source_file_id not in source_file_lookup:
            raise ValueError("Archive import_run_files contains an unknown source-file key")
        source_file_record = source_file_lookup[source_file_id]
        rows_read = int(rows_read or 0)
        job_rows_emitted = int(job_rows_emitted or 0)
        job_skill_rows_emitted = int(job_skill_rows_emitted or 0)
        reference_rows_emitted = int(reference_rows_emitted or 0)
        rows_loaded = job_rows_emitted + reference_rows_emitted
        if rows_loaded > rows_read:
            raise ValueError(f"Archive import counts exceed source rows for {source_file_id}")
        connection.execute(
            "INSERT INTO import_run_files "
            "(import_run_id, source_dataset, source_file, rows_read, rows_loaded, rows_rejected, "
            "import_status, notes, source_file_id, job_rows_emitted, job_skill_rows_emitted, "
            "reference_rows_emitted, output_tables, processing_role) "
            "VALUES (?, ?, ?, ?, ?, 0, 'succeeded', ?, ?, ?, ?, ?, ?, ?)",
            (
                import_run_id,
                source_file_record["source_dataset"],
                source_file_record["source_file"],
                rows_read,
                rows_loaded,
                processing_role,
                source_file_id,
                job_rows_emitted,
                job_skill_rows_emitted,
                reference_rows_emitted,
                output_tables,
                processing_role,
            ),
        )


def register_local_reference_import_files(connection, import_run_id, file_row_counts):
    for source_file, row_count in file_row_counts.items():
        connection.execute(
            "INSERT INTO import_run_files "
            "(import_run_id, source_dataset, source_file, rows_read, rows_loaded, rows_rejected, "
            "import_status, notes) VALUES (?, 'curated_reference_data', ?, ?, ?, 0, 'succeeded', ?)",
            (
                import_run_id,
                source_file,
                row_count,
                row_count,
                "Local reference data used to load learning-resource details and language labels.",
            ),
        )


def verify_archive_table_counts(duckdb_connection, archive_directory, manifest):
    archive_counts = {}
    for table_name in ARCHIVE_TABLE_NAMES:
        archive_file_path = Path(archive_directory) / f"{table_name}.parquet"
        actual_count = duckdb_connection.execute(
            "SELECT COUNT(*) FROM read_parquet(?)",
            [str(archive_file_path)],
        ).fetchone()[0]
        expected_count = manifest["tables"][table_name]["row_count"]
        if actual_count != expected_count:
            raise ValueError(
                f"Archive row count mismatch for {table_name}: expected {expected_count}, found {actual_count}"
            )
        archive_counts[table_name] = actual_count
    return archive_counts


def validate_database_table_matches_archive(
    connection,
    duckdb_connection,
    archive_directory,
    archive_table_name,
    archive_field_names,
    database_query,
):
    expected_rows = list(
        iter_archive_rows(
            duckdb_connection,
            archive_directory,
            archive_table_name,
            archive_field_names,
        )
    )
    actual_rows = [tuple(row) for row in connection.execute(database_query).fetchall()]
    if archive_table_name == "learning_resource_languages":
        expected_rows = [(resource_id, language.strip()) for resource_id, language in expected_rows]
    expected_rows.sort(key=lambda row: tuple("" if value is None else str(value) for value in row))
    actual_rows.sort(key=lambda row: tuple("" if value is None else str(value) for value in row))
    if actual_rows != expected_rows:
        raise ValueError(
            f"SQLite learning-resource table does not match the verified archive table {archive_table_name}"
        )


def load_parquet_archive(connection, import_run_id, archive_directory):
    try:
        import duckdb
    except ImportError as error:
        raise RuntimeError(
            "Full Parquet archive loading requires DuckDB. Activate the project virtual environment and install "
            "scripts/database_loading/requirements.txt before loading."
        ) from error

    archive_directory = Path(archive_directory).expanduser().resolve()
    manifest = json.loads((archive_directory / "manifest.json").read_text(encoding="utf-8"))
    duckdb_connection = duckdb.connect(database=":memory:")
    try:
        archive_counts = verify_archive_table_counts(duckdb_connection, archive_directory, manifest)
        archived_runs = list(
            iter_archive_rows(
                duckdb_connection,
                archive_directory,
                "import_runs",
                (
                    "import_run_id",
                    "generated_on_utc",
                    "generator",
                    "build_status",
                    "source_file_count",
                    "job_rows",
                    "job_skill_rows",
                    "notes",
                ),
            )
        )
        if len(archived_runs) != 1:
            raise ValueError("Full archive must contain exactly one validated import run")
        (
            archive_run_id,
            generated_on_utc,
            archive_generator,
            archive_build_status,
            archive_source_file_count,
            archive_job_rows,
            archive_job_skill_rows,
            archive_notes,
        ) = archived_runs[0]
        if archive_build_status != "validated":
            raise ValueError(f"Archive build is not validated: {archive_build_status}")
        if archive_job_rows != manifest["totals"]["jobs"]:
            raise ValueError("Archive import-run job total disagrees with the package manifest")
        if archive_job_skill_rows != manifest["totals"]["job_skills"]:
            raise ValueError("Archive import-run job-skill total disagrees with the package manifest")

        source_file_lookup = load_archive_source_metadata(
            connection,
            duckdb_connection,
            archive_directory,
            manifest,
        )
        connection.execute(
            "UPDATE import_runs SET source_archive_run_id = ?, archive_generated_on_utc = ?, "
            "archive_generator = ?, archive_build_status = ?, archive_source_file_count = ?, "
            "archive_job_rows = ?, archive_job_skill_rows = ? WHERE import_run_id = ?",
            (
                archive_run_id,
                generated_on_utc,
                archive_generator,
                archive_build_status,
                archive_source_file_count,
                archive_job_rows,
                archive_job_skill_rows,
                import_run_id,
            ),
        )
        register_archive_import_run_files(
            connection,
            import_run_id,
            duckdb_connection,
            archive_directory,
            archive_run_id,
            source_file_lookup,
        )

        loaded_skills = insert_archive_table(
            connection,
            duckdb_connection,
            archive_directory,
            "skills",
            SKILL_CATALOG_FIELD_NAMES,
            plain_insert_sql("skills", SKILL_CATALOG_FIELD_NAMES),
        )
        loaded_aliases = insert_archive_table(
            connection,
            duckdb_connection,
            archive_directory,
            "skill_aliases",
            SKILL_ALIAS_FIELD_NAMES,
            plain_insert_sql("skill_aliases", SKILL_ALIAS_FIELD_NAMES),
        )
        loaded_observations = insert_archive_table(
            connection,
            duckdb_connection,
            archive_directory,
            "skill_observations",
            SKILL_OBSERVATION_FIELD_NAMES,
            plain_insert_sql("skill_observations", SKILL_OBSERVATION_FIELD_NAMES),
        )
        loaded_jobs = insert_archive_table(
            connection,
            duckdb_connection,
            archive_directory,
            "jobs",
            JOB_FIELD_NAMES,
            plain_insert_sql("jobs", JOB_FIELD_NAMES),
            batch_size=2000,
        )
        loaded_job_skills = insert_archive_table(
            connection,
            duckdb_connection,
            archive_directory,
            "job_skills",
            JOB_SKILL_FIELD_NAMES,
            plain_insert_sql("job_skills", JOB_SKILL_FIELD_NAMES),
            batch_size=10000,
        )
        resource_counts = load_learning_resources(connection)
        if loaded_skills != archive_counts["skills"]:
            raise ValueError("Loaded skill catalog count disagrees with the full archive")
        if loaded_aliases != archive_counts["skill_aliases"]:
            raise ValueError("Loaded skill alias count disagrees with the full archive")
        if loaded_observations != archive_counts["skill_observations"]:
            raise ValueError("Loaded skill observation count disagrees with the full archive")
        if loaded_jobs != manifest["totals"]["jobs"]:
            raise ValueError("Loaded job count disagrees with the full archive")
        if loaded_job_skills != manifest["totals"]["job_skills"]:
            raise ValueError("Loaded job-skill count disagrees with the full archive")
        for table_name, loaded_count in resource_counts.items():
            if loaded_count != archive_counts[table_name]:
                raise ValueError(
                    f"Loaded {table_name} count disagrees with the full archive"
                )

        validate_database_table_matches_archive(
            connection,
            duckdb_connection,
            archive_directory,
            "learning_resources",
            LEARNING_RESOURCE_FIELD_NAMES,
            "SELECT " + ", ".join(LEARNING_RESOURCE_FIELD_NAMES) + " FROM learning_resources",
        )
        validate_database_table_matches_archive(
            connection,
            duckdb_connection,
            archive_directory,
            "learning_resource_skills",
            ("resource_id", "skill_id"),
            "SELECT resource_id, skill_id FROM learning_resource_skills",
        )
        validate_database_table_matches_archive(
            connection,
            duckdb_connection,
            archive_directory,
            "learning_resource_languages",
            ("resource_id", "language"),
            "SELECT resource_id, language_label FROM learning_resource_languages",
        )

        local_reference_counts = {
            "learning_resources.json": resource_counts["learning_resources"],
            "learning_resources.csv": resource_counts["learning_resources"],
        }
        register_reference_data_source(connection, local_reference_counts)
        register_local_reference_import_files(connection, import_run_id, local_reference_counts)
        expected_file_count = archive_counts["import_run_files"] + len(local_reference_counts)
        actual_file_count = connection.execute(
            "SELECT COUNT(*) FROM import_run_files WHERE import_run_id = ?",
            (import_run_id,),
        ).fetchone()[0]
        if actual_file_count != expected_file_count:
            raise ValueError("Local import-run file audit count does not match archive inputs")

        return {
            "loaded_job_rows": loaded_jobs,
            "loaded_job_skill_rows": loaded_job_skills,
            "loaded_skill_observation_rows": loaded_observations,
            "loaded_skill_catalog_rows": loaded_skills,
            "loaded_skill_alias_rows": loaded_aliases,
            "source_archive_run_id": archive_run_id,
            "archive_table_counts": archive_counts,
            **resource_counts,
        }
    finally:
        duckdb_connection.close()


def complete_import_run(connection, import_run_id, pipeline_version, source_fingerprint, notes):
    table_counts = query_table_counts(connection)
    by_source = {
        row["source_dataset"]: row["job_count"]
        for row in connection.execute(
            "SELECT source_dataset, COUNT(*) AS job_count FROM jobs "
            "GROUP BY source_dataset ORDER BY source_dataset"
        )
    }
    quality_report = {
        "database_engine": "SQLite",
        "pipeline_version": pipeline_version,
        "source_fingerprint": source_fingerprint,
        "row_counts": table_counts,
        "job_rows_by_source": by_source,
        "foreign_key_violations": 0,
    }
    source_archive = connection.execute(
        "SELECT source_archive_run_id, archive_generated_on_utc, archive_generator, "
        "archive_build_status, archive_source_file_count, archive_job_rows, archive_job_skill_rows "
        "FROM import_runs WHERE import_run_id = ?",
        (import_run_id,),
    ).fetchone()
    if source_archive is not None and source_archive["source_archive_run_id"]:
        quality_report["source_archive"] = dict(source_archive)
    connection.execute(
        "UPDATE import_runs SET run_status = 'succeeded', finished_at = ?, quality_report = ?, notes = ? "
        "WHERE import_run_id = ?",
        (
            timestamp_utc(),
            json.dumps(quality_report, ensure_ascii=False, sort_keys=True),
            notes,
            import_run_id,
        ),
    )
    return quality_report


def validate_database(connection):
    foreign_key_violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_violations:
        first_violations = [tuple(row) for row in foreign_key_violations[:10]]
        raise sqlite3.IntegrityError(f"SQLite foreign-key validation failed: {first_violations}")


def api_rollups_are_ready(connection):
    required_tables = {
        "api_scope_rollups",
        "api_scope_skill_rollups",
        "api_role_scope_rollups",
        "api_role_skill_rollups",
        "api_source_field_coverage",
        "api_historical_month_rollups",
    }
    existing_tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if not required_tables.issubset(existing_tables):
        return False
    totals = connection.execute("""
        SELECT
            (SELECT COUNT(*) FROM jobs) AS job_count,
            (SELECT COALESCE(SUM(job_record_count), 0) FROM api_scope_rollups) AS scope_job_count,
            (SELECT COALESCE(SUM(job_record_count), 0) FROM api_role_scope_rollups) AS role_job_count,
            (SELECT COALESCE(SUM(job_record_count), 0) FROM api_source_field_coverage) AS coverage_job_count,
            (SELECT COALESCE(SUM(eligible_job_record_count), 0) FROM api_scope_rollups) AS scope_eligible_records,
            (SELECT COALESCE(SUM(eligible_job_record_count), 0) FROM api_role_scope_rollups) AS role_eligible_records,
            (SELECT COALESCE(SUM(job_record_count), 0) FROM api_scope_skill_rollups) AS scope_skill_links,
            (SELECT COALESCE(SUM(job_record_count), 0) FROM api_role_skill_rollups) AS role_skill_links
    """).fetchone()
    return (
        totals["job_count"] == totals["scope_job_count"]
        == totals["role_job_count"] == totals["coverage_job_count"]
        and totals["scope_eligible_records"] == totals["role_eligible_records"]
        and totals["scope_skill_links"] == totals["role_skill_links"]
    )


def refresh_api_rollups(connection):
    if not API_ROLLUPS_SQL_PATH.is_file():
        raise FileNotFoundError(f"API rollup SQL is missing: {API_ROLLUPS_SQL_PATH}")
    sql_text = API_ROLLUPS_SQL_PATH.read_text(encoding="utf-8")
    pending_statement = ""
    for line in sql_text.splitlines(keepends=True):
        pending_statement += line
        if sqlite3.complete_statement(pending_statement):
            statement = pending_statement.strip()
            if statement:
                connection.execute(statement)
            pending_statement = ""
    if pending_statement.strip():
        raise sqlite3.OperationalError("API rollup SQL contains an incomplete statement.")

    if not api_rollups_are_ready(connection):
        raise sqlite3.IntegrityError("API rollups do not cover every local job record.")
    if connection.execute(
        "SELECT COALESCE(SUM(job_record_count), 0) FROM api_scope_skill_rollups"
    ).fetchone()[0] != connection.execute(
        "SELECT COALESCE(SUM(job_record_count), 0) FROM api_role_skill_rollups"
    ).fetchone()[0]:
        raise sqlite3.IntegrityError("Scope and role skill rollup totals disagree.")


def load_database(
    database_path=None,
    source_mode="auto",
    processed_directory=DEFAULT_PROCESSED_DIRECTORY,
    archive_directory=DEFAULT_ARCHIVE_DIRECTORY,
    replace_existing=False,
):
    resolved_path = resolve_database_path(database_path)
    connection = connect_to_database(resolved_path, create_if_missing=True)
    try:
        apply_migrations(connection)
        selected_source, selected_paths = select_import_source(
            source_mode,
            processed_directory,
            archive_directory,
        )
        fingerprint_paths = import_input_paths(selected_source, processed_directory, selected_paths)
        missing_inputs = [path for path in fingerprint_paths if not path.is_file()]
        if missing_inputs:
            raise FileNotFoundError(
                "Required local import files are missing: "
                + ", ".join(str(path) for path in missing_inputs)
            )
        source_fingerprint = calculate_source_fingerprint(fingerprint_paths)
        existing_import = matching_successful_import(connection, source_fingerprint)
        if existing_import is not None and not replace_existing:
            if not api_rollups_are_ready(connection):
                connection.execute("BEGIN IMMEDIATE")
                try:
                    refresh_api_rollups(connection)
                    connection.commit()
                except Exception:
                    if connection.in_transaction:
                        connection.rollback()
                    raise
            return {
                "database": str(resolved_path),
                "source_mode": selected_source,
                "skipped": True,
                "reason": "The same local input fingerprint was already imported successfully.",
                "row_counts": query_table_counts(connection),
            }
        if database_contains_data(connection) and not replace_existing:
            raise DatasetAlreadyLoadedError(
                "The local SQLite database already contains a different dataset. "
                "Use --replace only when you intend to rebuild it from the selected local inputs."
            )

        pipeline_version = f"sqlite_{selected_source}_v1"
        if selected_source == "archive":
            archive_manifest = json.loads(
                (Path(archive_directory).expanduser().resolve() / "manifest.json").read_text(encoding="utf-8")
            )
            archive_totals = archive_manifest["totals"]
            run_notes = (
                f"Loaded complete local archive {archive_manifest['import_run_id']}: "
                f"{archive_totals['jobs']} jobs and {archive_totals['job_skills']} job-skill links. "
                "Listing activity and redistribution rights are not verified by this import."
            )
        else:
            run_notes = (
                "Loaded from complete local normalized staging files. Original source files remain unchanged; "
                "listing activity and redistribution permissions are not established by the import."
            )
        import_run_id = None
        loaded_metadata = {}
        started_at = timestamp_utc()
        try:
            connection.execute("BEGIN IMMEDIATE")
            if replace_existing:
                clear_domain_data(connection)
            import_run_id, started_at = create_import_run(
                connection,
                pipeline_version,
                source_fingerprint,
                run_notes,
            )
            if selected_source == "archive":
                loaded_metadata = load_parquet_archive(
                    connection,
                    import_run_id,
                    archive_directory,
                )
            else:
                processed_job_paths = sorted(Path(processed_directory).expanduser().resolve().glob("jobs_*.csv.gz"))
                loaded_metadata = load_processed_dataset(
                    connection,
                    import_run_id,
                    Path(processed_directory).expanduser().resolve(),
                    processed_job_paths,
                )
            refresh_api_rollups(connection)
            validate_database(connection)
            quality_report = complete_import_run(
                connection,
                import_run_id,
                pipeline_version,
                source_fingerprint,
                run_notes,
            )
            connection.commit()
            return {
                "database": str(resolved_path),
                "source_mode": selected_source,
                "skipped": False,
                "import_run_id": import_run_id,
                "source_archive_run_id": loaded_metadata.get("source_archive_run_id"),
                "row_counts": quality_report["row_counts"],
                "job_rows_by_source": quality_report["job_rows_by_source"],
                "loaded_details": loaded_metadata,
            }
        except Exception as error:
            if connection.in_transaction:
                connection.rollback()
            if import_run_id is not None:
                record_failed_import(
                    connection,
                    pipeline_version,
                    source_fingerprint,
                    started_at,
                    error,
                )
            raise
    finally:
        connection.close()


def check_database(database_path=None):
    resolved_path = resolve_database_path(database_path)
    connection = connect_to_database(resolved_path)
    try:
        applied_migrations = connection.execute(
            "SELECT migration_version, migration_name, applied_at "
            "FROM schema_migrations ORDER BY migration_version"
        ).fetchall()
        validate_database(connection)
        return {
            "database": str(resolved_path),
            "engine": "SQLite",
            "foreign_key_violations": 0,
            "migrations": [dict(row) for row in applied_migrations],
            "row_counts": query_table_counts(connection),
        }
    finally:
        connection.close()
