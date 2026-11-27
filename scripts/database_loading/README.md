# Full Local SQLite Loading

## Cleaned-audit relational SQLite

For a separate loss-preserving database built directly from the cleaned CSV, use `build_cleaned_relational_sqlite.py`. It keeps all 123 source columns in `job_cleaning_audit`, alongside the application's normalized relational tables and derived API rollups. This output is distinct from the application database `job_market.sqlite3` and does not replace it.

```bash
python scripts/database_loading/build_cleaned_relational_sqlite.py
```

The selected cleaning summary under `analysis/reports/data_cleaning/` matches the complete Drive CSV's SHA-256. The builder refuses a mismatch, imports all 775,155 rows and their skill-ID links, and validates row counts, foreign keys, rollups, and SQLite integrity before publishing `data/processed/jobs_cleaned_audited.sqlite3`. The database and CSV are Git-ignored; the rebuilt SQLite file is large (about 7.65 GB in this snapshot). Do not use `--replace` unless intentionally rebuilding it.

The operational database uses the complete `full_archive_parquet_v1_20261028` package. The verified archive contains 775,155 job rows, 4,026,953 job-skill links, all seven job datasets, and the complete skill, alias, observation, learning-resource, and source-provenance tables. The 439 Arab-tech rows are retained. Listing activity and redistribution permissions remain unverified.

## Prepare and load

Keep the complete archive package in `data/processed/full_archive_parquet_v1_20261028/`. Verify or restore that package from the preserved Google Drive archive before loading. Then run from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r scripts/database_loading/requirements.txt
python scripts/database_loading/load_to_database.py load --source archive
python scripts/database_loading/load_to_database.py check
```

The default SQLite file is `data/processed/job_market.sqlite3`. Automatic mode prefers the complete checksum-verified archive and uses complete normalized local staging files only when the archive is absent; without either complete input, loading stops with an error. No sample source is available. Existing data is not overwritten unless `--replace` is explicitly supplied.

## Commands

```bash
python scripts/database_loading/load_to_database.py init
python scripts/database_loading/load_to_database.py load --source archive
python scripts/database_loading/load_to_database.py load --source processed
python scripts/database_loading/load_to_database.py load --replace
python scripts/database_loading/load_to_database.py check
```

Use `--archive-directory` or `--processed-directory` to select another local input folder. `JOP_DATABASE_PATH` or `--database` changes only the local SQLite file path, which must resolve inside the repository root; paths outside it and URL-style/network database connections are rejected. DuckDB is used only as a local Parquet reader during import; application data and queries use SQLite. The Node API opens that SQLite file read-only.

Migration `004_node_api_rollups.sql` defines pre-aggregates for API overview, role and skill analysis, source-field coverage, and explicitly dated 2023 months. After a new load—or when the same input fingerprint is already present but rollups are absent or incomplete—the loader rebuilds them transactionally from the local jobs, eligible skill links, and reviewed skill catalogue. These are derived tables, not additional source data. Eligible rollups require the link and catalogue policy/status pair to agree: `(approved_aliases, curated)` or `(exact_only, curated_exact_only)`.

The archive loader validates every package checksum and Parquet table count, records the original archive run and file provenance, imports the full jobs and job-skill tables in batches, and checks the resource JSON/CSV data against the archive. It validates foreign keys before committing. Repeating a load with an unchanged input fingerprint is a no-op apart from rebuilding missing rollups. A different existing snapshot requires `--replace`. Original source files and Drive originals are not modified.
