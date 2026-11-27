# Local SQLite Database

This directory contains the executable local SQLite schema, migration history, and design references. The project has two separate local SQLite outputs: `job_market.sqlite3` for the application/archive workflow, and `jobs_cleaned_audited.sqlite3` for the full cleaned CSV with its 123-column audit table. No external or hosted database is configured.

- [`migrations/`](migrations/README.md): ordered SQLite DDL migrations and checksums applied by the local runner.
- [`docs/software-engineering/PHYSICAL_SCHEMA_PROPOSAL.md`](../docs/software-engineering/PHYSICAL_SCHEMA_PROPOSAL.md): implemented tables, keys, constraints, local path, and full-archive load behavior.
- [`docs/software-engineering/DATABASE_SPECIFICATION.md`](../docs/software-engineering/DATABASE_SPECIFICATION.md): logical model and integrity rules.
- [`docs/DATA_AND_DATABASE.md`](../docs/DATA_AND_DATABASE.md): source coverage and end-to-end local workflow.

The generated database defaults to `data/processed/job_market.sqlite3`, which is covered by the repository's existing ignore rule. Set `JOP_DATABASE_PATH` or pass `--database` to use a different local file. Do not point either option at a URL.

Run from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r scripts/database_loading/requirements.txt
python scripts/database_loading/load_to_database.py init
python scripts/database_loading/load_to_database.py load --source archive
python scripts/database_loading/load_to_database.py check
```

The default loader selects the verified full Parquet archive in `data/processed/full_archive_parquet_v1_20261028/`; if it is absent, complete normalized local files may be selected, and loading stops if neither complete input exists. No sample data source is available. Use `--replace` only when intentionally rebuilding the local snapshot. Original source files and the preserved Google Drive package are not modified by database loading.
