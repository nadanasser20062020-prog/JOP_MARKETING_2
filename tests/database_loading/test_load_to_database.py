import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from backend.database import PROJECT_ROOT_DIRECTORY
from scripts.database_loading import load_to_database


class SQLiteLoaderCommandTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory(
            dir=PROJECT_ROOT_DIRECTORY,
            prefix=".sqlite-loader-test-",
        )
        self.addCleanup(self.temporary_directory.cleanup)
        self.database_path = Path(self.temporary_directory.name) / "test.sqlite3"

    def run_cli(self, arguments):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = load_to_database.main(arguments)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_default_command_and_source_are_local_auto_load(self):
        args = load_to_database.build_argument_parser().parse_args([])
        self.assertEqual(args.command, "load")
        self.assertEqual(args.source, "auto")

    def test_init_then_check_reports_migrations_and_empty_tables(self):
        exit_code, stdout, stderr = self.run_cli(
            ["init", "--database", str(self.database_path)]
        )
        self.assertEqual(exit_code, 0, stderr)
        initialized = json.loads(stdout)
        self.assertEqual(initialized["engine"], "SQLite")
        self.assertEqual(initialized["status"], "schema_ready")
        self.assertTrue(self.database_path.is_file())

        exit_code, stdout, stderr = self.run_cli(
            ["check", "--database", str(self.database_path)]
        )
        self.assertEqual(exit_code, 0, stderr)
        checked = json.loads(stdout)
        self.assertEqual(checked["foreign_key_violations"], 0)
        self.assertEqual(len(checked["migrations"]), 6)
        self.assertEqual(checked["row_counts"]["jobs"], 0)
        self.assertEqual(checked["row_counts"]["job_cleaning_audit"], 0)

    def test_database_paths_outside_the_project_are_rejected(self):
        outside_path = PROJECT_ROOT_DIRECTORY.parent / "outside-jop-test.sqlite3"
        exit_code, stdout, stderr = self.run_cli(
            ["init", "--database", str(outside_path)]
        )
        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("inside the project root", stderr)
        self.assertFalse(outside_path.exists())


if __name__ == "__main__":
    unittest.main()
