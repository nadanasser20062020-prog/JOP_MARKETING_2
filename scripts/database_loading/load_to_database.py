import argparse
import csv
import gzip
import json
import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
DEFAULT_PROCESSED_DATA_DIRECTORY = PROJECT_ROOT_DIRECTORY / "data" / "processed"
DEFAULT_REFERENCE_DATA_DIRECTORY = PROJECT_ROOT_DIRECTORY / "data" / "reference"
QUALITY_REPORT_FILE_NAME = "data_quality_report.json"
PIPELINE_VERSION = "site_data_import_v1"
ADVISORY_LOCK_IDENTIFIER = 791263542018
COPY_CHUNK_SIZE = 1024 * 1024
MANAGED_TABLE_NAMES = (
    "skills",
    "skill_aliases",
    "jobs",
    "job_skills",
    "skill_observations",
    "learning_resources",
    "learning_resource_skills",
    "learning_resource_languages",
)
TABLE_PRIMARY_KEY_COLUMNS = {
    "skills": ("skill_id",),
    "skill_aliases": ("alias_normalized",),
    "jobs": ("record_id",),
    "job_skills": ("record_id", "skill_id"),
    "skill_observations": ("source_dataset", "skill_normalized"),
    "learning_resources": ("resource_id",),
}


@dataclass(frozen=True)
class LoadFileSpecification:
    table_name: str
    file_path: Path


def build_load_file_plan(
    processed_data_directory: Path,
    reference_data_directory: Path,
) -> tuple[LoadFileSpecification, ...]:
    return (
        LoadFileSpecification("skills", reference_data_directory / "skill_catalog.csv"),
        LoadFileSpecification("skill_aliases", reference_data_directory / "skill_aliases.csv"),
        LoadFileSpecification("jobs", processed_data_directory / "jobs_historical_2023_sample.csv.gz"),
        LoadFileSpecification("jobs", processed_data_directory / "jobs_latest_export_unverified.csv.gz"),
        LoadFileSpecification("jobs", processed_data_directory / "jobs_other_snapshots_unverified.csv.gz"),
        LoadFileSpecification("job_skills", processed_data_directory / "job_skills.csv.gz"),
        LoadFileSpecification("skill_observations", processed_data_directory / "skill_observations.csv.gz"),
        LoadFileSpecification("learning_resources", reference_data_directory / "learning_resources.csv"),
    )


def open_text_data_file(file_path: Path):
    if file_path.suffix == ".gz":
        return gzip.open(file_path, "rt", encoding="utf-8-sig", newline="")
    return file_path.open("r", encoding="utf-8-sig", newline="")


def read_csv_header(file_path: Path) -> list[str]:
    with open_text_data_file(file_path) as data_file:
        return next(csv.reader(data_file), [])


def validate_local_files(
    load_file_plan: tuple[LoadFileSpecification, ...],
    quality_report_file_path: Path,
) -> dict[str, object]:
    for file_specification in load_file_plan:
        if not file_specification.file_path.is_file():
            raise FileNotFoundError(f"Required data file does not exist: {file_specification.file_path}")
        csv_header = read_csv_header(file_specification.file_path)
        if not csv_header:
            raise ValueError(f"Data file has no CSV header: {file_specification.file_path}")
        if any(not column_name for column_name in csv_header):
            raise ValueError(f"Data file has an empty column name: {file_specification.file_path}")
        if len(csv_header) != len(set(csv_header)):
            raise ValueError(f"Data file has duplicate column names: {file_specification.file_path}")
        required_primary_key_columns = TABLE_PRIMARY_KEY_COLUMNS[file_specification.table_name]
        missing_primary_key_columns = [
            column_name
            for column_name in required_primary_key_columns
            if column_name not in csv_header
        ]
        if missing_primary_key_columns:
            raise ValueError(
                f"Data file {file_specification.file_path.name} is missing key columns: "
                f"{missing_primary_key_columns}"
            )
    if not quality_report_file_path.is_file():
        raise FileNotFoundError(f"Quality report does not exist: {quality_report_file_path}")
    quality_report = json.loads(quality_report_file_path.read_text(encoding="utf-8"))
    if not isinstance(quality_report, dict):
        raise ValueError("The data-quality report must contain a JSON object")
    return quality_report


def get_table_column_names(database_cursor, table_name: str) -> list[str]:
    database_cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
    )
    return [result_row[0] for result_row in database_cursor.fetchall()]


def copy_file_into_table(database_cursor, postgres_sql, file_specification: LoadFileSpecification) -> int:
    csv_header = read_csv_header(file_specification.file_path)
    database_column_names = get_table_column_names(database_cursor, file_specification.table_name)
    if not database_column_names:
        raise ValueError(
            f"Table public.{file_specification.table_name} was not found. "
            "Run neon_schema.sql first."
        )
    if csv_header != database_column_names:
        raise ValueError(
            f"CSV columns do not match public.{file_specification.table_name} in order. "
            f"File columns: {csv_header}; database columns: {database_column_names}"
        )

    copy_statement = postgres_sql.SQL(
        "COPY {} ({}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')"
    ).format(
        postgres_sql.Identifier("public", file_specification.table_name),
        postgres_sql.SQL(", ").join(
            postgres_sql.Identifier(column_name) for column_name in csv_header
        ),
    )
    with open_text_data_file(file_specification.file_path) as data_file:
        with database_cursor.copy(copy_statement) as copy_operation:
            while True:
                data_chunk = data_file.read(COPY_CHUNK_SIZE)
                if not data_chunk:
                    break
                copy_operation.write(data_chunk)

    return database_cursor.rowcount


def get_existing_managed_table_names(database_cursor, postgres_sql) -> list[str]:
    tables_with_existing_rows = []
    for table_name in MANAGED_TABLE_NAMES:
        database_cursor.execute(
            postgres_sql.SQL("SELECT EXISTS (SELECT 1 FROM {} LIMIT 1)").format(
                postgres_sql.Identifier("public", table_name)
            )
        )
        if database_cursor.fetchone()[0]:
            tables_with_existing_rows.append(table_name)
    return tables_with_existing_rows


def get_managed_table_counts(database_cursor, postgres_sql) -> dict[str, int]:
    table_counts = {}
    for table_name in MANAGED_TABLE_NAMES:
        database_cursor.execute(
            postgres_sql.SQL("SELECT COUNT(*) FROM {} ").format(
                postgres_sql.Identifier("public", table_name)
            )
        )
        table_counts[table_name] = database_cursor.fetchone()[0]
    return table_counts


def add_learning_resource_relationships(database_cursor) -> None:
    database_cursor.execute(
        """
        INSERT INTO public.learning_resource_skills (resource_id, skill_id)
        SELECT learning_resource.resource_id, BTRIM(skill_item.skill_id)
        FROM public.learning_resources AS learning_resource
        CROSS JOIN LATERAL UNNEST(STRING_TO_ARRAY(learning_resource.skill_ids, ';'))
            AS skill_item(skill_id)
        WHERE BTRIM(skill_item.skill_id) <> ''
        ON CONFLICT (resource_id, skill_id) DO NOTHING
        """
    )
    database_cursor.execute(
        """
        INSERT INTO public.learning_resource_languages (resource_id, language)
        SELECT learning_resource.resource_id, BTRIM(language_item.language)
        FROM public.learning_resources AS learning_resource
        CROSS JOIN LATERAL UNNEST(STRING_TO_ARRAY(learning_resource.languages, ';'))
            AS language_item(language)
        WHERE BTRIM(language_item.language) <> ''
        ON CONFLICT (resource_id, language) DO NOTHING
        """
    )


def record_source_file_counts(database_cursor, import_run_identifier: int) -> None:
    database_cursor.execute(
        """
        SELECT source_dataset, source_file, COUNT(*)
        FROM public.jobs
        GROUP BY source_dataset, source_file
        ORDER BY source_dataset, source_file
        """
    )
    for source_dataset, source_file, row_count in database_cursor.fetchall():
        database_cursor.execute(
            """
            INSERT INTO public.import_run_files (
                import_run_id,
                source_dataset,
                source_file,
                rows_read,
                rows_loaded,
                rows_rejected,
                import_status,
                notes
            )
            VALUES (%s, %s, %s, %s, %s, 0, 'succeeded', %s)
            ON CONFLICT (import_run_id, source_dataset, source_file)
            DO UPDATE SET
                rows_read = EXCLUDED.rows_read,
                rows_loaded = EXCLUDED.rows_loaded,
                rows_rejected = EXCLUDED.rows_rejected,
                import_status = EXCLUDED.import_status,
                notes = EXCLUDED.notes
            """,
            (
                import_run_identifier,
                source_dataset,
                source_file,
                row_count,
                row_count,
                "Count of retained normalized job rows from this source file.",
            ),
        )


def create_import_run(database_connection, quality_report: dict[str, object]) -> int:
    with database_connection.transaction():
        with database_connection.cursor() as database_cursor:
            database_cursor.execute(
                """
                INSERT INTO public.import_runs (
                    run_status,
                    pipeline_version,
                    quality_report,
                    notes
                )
                VALUES ('running', %s, %s::jsonb, %s)
                RETURNING import_run_id
                """,
                (
                    PIPELINE_VERSION,
                    json.dumps(quality_report, ensure_ascii=False),
                    "Import started by scripts/database_loading/load_to_database.py.",
                ),
            )
            return database_cursor.fetchone()[0]


def update_failed_import_run(database_connection, import_run_identifier: int, failure: Exception) -> None:
    failure_message = f"{type(failure).__name__}: {failure}"[:1800]
    database_url = os.environ.get("DATABASE_URL", "")
    if database_url:
        failure_message = failure_message.replace(database_url, "[redacted database connection]")
    try:
        with database_connection.transaction():
            with database_connection.cursor() as database_cursor:
                database_cursor.execute(
                    """
                    UPDATE public.import_runs
                    SET run_status = 'failed',
                        finished_at = NOW(),
                        notes = %s
                    WHERE import_run_id = %s
                    """,
                    (failure_message, import_run_identifier),
                )
    except Exception:
        return


def perform_database_import(
    database_connection,
    postgres_sql,
    load_file_plan: tuple[LoadFileSpecification, ...],
    quality_report: dict[str, object],
    replace_existing_data: bool,
) -> tuple[int, dict[str, int]]:
    import_run_identifier = create_import_run(database_connection, quality_report)
    try:
        with database_connection.transaction():
            with database_connection.cursor() as database_cursor:
                database_cursor.execute("SELECT pg_advisory_xact_lock(%s)", (ADVISORY_LOCK_IDENTIFIER,))
                tables_with_existing_rows = get_existing_managed_table_names(
                    database_cursor,
                    postgres_sql,
                )
                if tables_with_existing_rows and not replace_existing_data:
                    raise RuntimeError(
                        "Managed data already exists in Neon. Re-run with "
                        "--replace-existing-data only if these tables may be replaced. "
                        f"Tables containing rows: {tables_with_existing_rows}"
                    )

                if replace_existing_data:
                    database_cursor.execute(
                        """
                        TRUNCATE TABLE
                            public.learning_resource_languages,
                            public.learning_resource_skills,
                            public.learning_resources,
                            public.skill_observations,
                            public.job_skills,
                            public.jobs,
                            public.skill_aliases,
                            public.skills
                        RESTART IDENTITY
                        """
                    )

                for file_specification in load_file_plan:
                    file_rows_loaded = copy_file_into_table(
                        database_cursor,
                        postgres_sql,
                        file_specification,
                    )
                    print(
                        f"Loaded {file_rows_loaded} rows from {file_specification.file_path.name} "
                        f"into public.{file_specification.table_name}."
                    )

                add_learning_resource_relationships(database_cursor)
                record_source_file_counts(database_cursor, import_run_identifier)
                loaded_table_counts = get_managed_table_counts(database_cursor, postgres_sql)
                quality_report["database_load"] = {
                    "import_run_id": import_run_identifier,
                    "pipeline_version": PIPELINE_VERSION,
                    "replace_existing_data": replace_existing_data,
                    "table_row_counts": loaded_table_counts,
                }
                database_cursor.execute(
                    """
                    UPDATE public.import_runs
                    SET run_status = 'succeeded',
                        finished_at = NOW(),
                        quality_report = %s::jsonb,
                        notes = %s
                    WHERE import_run_id = %s
                    """,
                    (
                        json.dumps(quality_report, ensure_ascii=False),
                        "Data files loaded and relationship constraints passed.",
                        import_run_identifier,
                    ),
                )
        return import_run_identifier, loaded_table_counts
    except Exception as failure:
        update_failed_import_run(database_connection, import_run_identifier, failure)
        raise


def build_connection_information(psycopg, database_url: str) -> str:
    connection_parameters = psycopg.conninfo.conninfo_to_dict(database_url)
    current_ssl_mode = connection_parameters.get("sslmode", "")
    if current_ssl_mode not in {"require", "verify-ca", "verify-full"}:
        connection_parameters["sslmode"] = "require"
    connection_parameters.setdefault("connect_timeout", "15")
    return psycopg.conninfo.make_conninfo(**connection_parameters)


def main() -> int:
    command_line_parser = argparse.ArgumentParser(
        description="Load the cleaned job data and reference tables into Neon PostgreSQL"
    )
    command_line_parser.add_argument(
        "--processed-data-directory",
        type=Path,
        default=DEFAULT_PROCESSED_DATA_DIRECTORY,
    )
    command_line_parser.add_argument(
        "--reference-data-directory",
        type=Path,
        default=DEFAULT_REFERENCE_DATA_DIRECTORY,
    )
    command_line_parser.add_argument(
        "--replace-existing-data",
        action="store_true",
        help="Truncate and reload the managed data tables inside one transaction",
    )
    command_line_parser.add_argument(
        "--validate-files-only",
        action="store_true",
        help="Check local input files and their primary-key columns without connecting to Neon",
    )
    command_line_arguments = command_line_parser.parse_args()

    processed_data_directory = command_line_arguments.processed_data_directory.resolve()
    reference_data_directory = command_line_arguments.reference_data_directory.resolve()
    load_file_plan = build_load_file_plan(processed_data_directory, reference_data_directory)
    quality_report_file_path = processed_data_directory / QUALITY_REPORT_FILE_NAME
    try:
        quality_report = validate_local_files(load_file_plan, quality_report_file_path)
    except (OSError, UnicodeError, csv.Error, ValueError) as validation_failure:
        raise SystemExit(f"Local input validation failed: {validation_failure}") from None

    if command_line_arguments.validate_files_only:
        print(
            json.dumps(
                {
                    "validated_input_files": len(load_file_plan),
                    "quality_report": str(quality_report_file_path),
                    "tables": [file_specification.table_name for file_specification in load_file_plan],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit(
            "DATABASE_URL is not set. Set it in your shell environment; do not put the Neon connection string in this file."
        )

    try:
        import psycopg
        from psycopg import sql as postgres_sql
    except ImportError as import_failure:
        raise SystemExit(
            "The PostgreSQL driver is not installed. Run "
            "python -m pip install -r scripts/database_loading/requirements.txt."
        ) from import_failure

    connection_information = build_connection_information(psycopg, database_url)
    try:
        with psycopg.connect(connection_information) as database_connection:
            import_run_identifier, loaded_table_counts = perform_database_import(
                database_connection,
                postgres_sql,
                load_file_plan,
                quality_report,
                command_line_arguments.replace_existing_data,
            )
    except Exception as database_failure:
        failure_message = f"{type(database_failure).__name__}: {database_failure}"
        failure_message = failure_message.replace(database_url, "[redacted database connection]")
        raise SystemExit(f"Neon data loading failed: {failure_message}") from None

    print(
        json.dumps(
            {
                "import_run_id": import_run_identifier,
                "run_status": "succeeded",
                "table_row_counts": loaded_table_counts,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
