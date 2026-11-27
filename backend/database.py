import os
import sqlite3
from pathlib import Path


PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_PATH = PROJECT_ROOT_DIRECTORY / "data" / "processed" / "job_market.sqlite3"


def resolve_database_path(database_path=None):
    configured_path = database_path
    if configured_path is None:
        configured_path = os.environ.get("JOP_DATABASE_PATH")
    if configured_path is None or not str(configured_path).strip():
        configured_path = DEFAULT_DATABASE_PATH

    configured_value = str(configured_path).strip()
    if "://" in configured_value or configured_value.startswith("file:"):
        raise ValueError("JOP_DATABASE_PATH must be a local file path, not a connection URL.")
    if configured_value == ":memory:":
        return configured_value

    resolved_path = Path(configured_value).expanduser()
    if not resolved_path.is_absolute():
        resolved_path = PROJECT_ROOT_DIRECTORY / resolved_path
    resolved_path = resolved_path.resolve()
    try:
        resolved_path.relative_to(PROJECT_ROOT_DIRECTORY)
    except ValueError as error:
        raise ValueError("JOP_DATABASE_PATH must stay inside the project root.") from error
    return resolved_path


def connect_to_database(database_path=None, create_if_missing=False):
    resolved_path = resolve_database_path(database_path)
    if resolved_path != ":memory:":
        if not resolved_path.exists() and not create_if_missing:
            raise FileNotFoundError(
                f"Local SQLite database not found: {resolved_path}. "
                "Initialize it with scripts/database_loading/load_to_database.py."
            )
        if create_if_missing:
            resolved_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(resolved_path), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection
