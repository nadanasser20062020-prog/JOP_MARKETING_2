# Scripts

- [`data_cleaning/`](data_cleaning/README.md) contains the reproducible data preparation and reference-catalog builders.
- [`database_loading/`](database_loading/README.md) contains the local SQLite migrations runner, importer, and integrity checks.

The database uses Python's standard-library `sqlite3` and the local file `data/processed/job_market.sqlite3` by default. Generated data remains local and is covered by existing ignore rules; do not edit original source files or add raw exports to Git.
