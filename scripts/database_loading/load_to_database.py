import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_DIRECTORY))

from backend.database import DEFAULT_DATABASE_PATH
from scripts.database_loading.sqlite_database import check_database, initialize_database, load_database


def build_argument_parser():
    argument_parser = argparse.ArgumentParser(
        description="Initialize, load, and validate the project's local SQLite database."
    )
    argument_parser.add_argument(
        "command",
        nargs="?",
        choices=("init", "load", "check"),
        default="load",
        help="init applies schema migrations, load imports local data, and check validates an existing file.",
    )
    argument_parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help=(
            "Local SQLite file path; defaults to "
            f"{DEFAULT_DATABASE_PATH.relative_to(PROJECT_ROOT_DIRECTORY)} or JOP_DATABASE_PATH."
        ),
    )
    argument_parser.add_argument(
        "--source",
        choices=("auto", "archive", "processed"),
        default="auto",
        help="Prefer the complete Parquet archive; otherwise use complete normalized files. The unit-test fixture is not available as a CLI data source.",
    )
    argument_parser.add_argument(
        "--archive-directory",
        type=Path,
        default=PROJECT_ROOT_DIRECTORY / "data" / "processed" / "full_archive_parquet_v1_20261028",
        help="Directory containing the verified full_archive_parquet_v1 package.",
    )
    argument_parser.add_argument(
        "--processed-directory",
        type=Path,
        default=PROJECT_ROOT_DIRECTORY / "data" / "processed",
        help="Directory containing complete normalized jobs_*.csv.gz, job_skills.csv.gz, and skill_observations.csv.gz files.",
    )
    argument_parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing local data only when an intentional rebuild is requested.",
    )
    return argument_parser


def main(arguments=None):
    argument_parser = build_argument_parser()
    command_line_arguments = argument_parser.parse_args(arguments)
    try:
        if command_line_arguments.command == "init":
            database_path = initialize_database(command_line_arguments.database)
            result = {
                "database": str(database_path),
                "engine": "SQLite",
                "status": "schema_ready",
            }
        elif command_line_arguments.command == "check":
            result = check_database(command_line_arguments.database)
        else:
            result = load_database(
                database_path=command_line_arguments.database,
                source_mode=command_line_arguments.source,
                processed_directory=command_line_arguments.processed_directory,
                archive_directory=command_line_arguments.archive_directory,
                replace_existing=command_line_arguments.replace,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
