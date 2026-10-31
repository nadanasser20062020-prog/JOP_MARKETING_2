# Neon Database Schema and Data Loader

`neon_schema.sql` creates the PostgreSQL tables, constraints, indexes, and seed rows required by the site-data pipeline. Run the complete file once in the Neon SQL Editor after selecting the intended database. The schema creates 12 tables; it does not upload the CSV files or create a Neon project.

## Install the loader dependency

From the repository root, create and activate a virtual environment, then install the PostgreSQL driver declared for this loader:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r scripts/database_loading/requirements.txt
```

For Windows PowerShell, activate with `.\.venv\Scripts\Activate.ps1` instead of the `source` command.

## Check local inputs

Run the preflight check before connecting. It verifies that the expected files and quality report exist, each CSV has a header, and each CSV contains the target table's primary-key columns. It does not connect to Neon or validate every data row against PostgreSQL constraints.

```bash
python scripts/database_loading/load_to_database.py --validate-files-only
```

## Load into Neon

Copy the connection string for the intended Neon database from the Neon dashboard and set it in the shell environment. Do not place it in source code, a committed file, or a chat message.

Bash or other POSIX shells:

```bash
export DATABASE_URL='postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require'
python scripts/database_loading/load_to_database.py
```

Windows PowerShell:

```powershell
$env:DATABASE_URL = 'postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require'
python scripts/database_loading/load_to_database.py
```

The loader enforces SSL if the connection string does not specify `sslmode=require`, `verify-ca`, or `verify-full`. It uses PostgreSQL `COPY FROM STDIN` to stream data from the local files; the files are not uploaded to object storage.

The loader imports these eight inputs:

- `data/reference/skill_catalog.csv` into `skills`.
- `data/reference/skill_aliases.csv` into `skill_aliases`.
- `data/processed/jobs_historical_2023_sample.csv.gz`, `jobs_latest_export_unverified.csv.gz`, and `jobs_other_snapshots_unverified.csv.gz` into `jobs`.
- `data/processed/job_skills.csv.gz` into `job_skills`.
- `data/processed/skill_observations.csv.gz` into `skill_observations`.
- `data/reference/learning_resources.csv` into `learning_resources`; its semicolon-separated skill IDs and languages are also inserted into the two relationship tables.

`jobs_archive.csv.gz` is intentionally not included. The historical and unverified snapshot groups remain separate; latest-export records are not verified as active listings, and source update fields are not assumed to be posting dates.

## Existing data and repeat runs

By default, the loader stops if any managed data table already contains rows. This prevents accidental duplicate imports. To deliberately replace the managed rows and reload, run:

```bash
python scripts/database_loading/load_to_database.py --replace-existing-data
```

**This option truncates the managed data tables before reloading.** The replacement and load happen in one transaction: if a load fails, PostgreSQL rolls back the data-table changes. The failed attempt remains recorded in `import_runs` when the schema permits. Existing `data_sources`, `source_files`, and earlier import-run audit records are retained. A PostgreSQL advisory lock serializes concurrent runs of this loader.

On success, the command prints the import-run ID and row counts for the managed tables. The loader also records run status, the local quality report, and retained job-row counts per source file in `import_runs` and `import_run_files`.

## Tables and data-use caveats

- `data_sources` has many `source_files`; each `jobs` row points to its source file and snapshot type.
- `jobs` has many `job_skills`; each assignment references a row in `skills`.
- `skills` has many `skill_aliases` and may be linked to learning resources through `learning_resource_skills`.
- `skill_observations` references a source dataset and normalized alias.
- `learning_resources` has language rows in `learning_resource_languages`.
- `import_runs` and `source_files` are associated through `import_run_files`, which stores per-file counts and status.

Keep matching conservative: honor each skill's match policy and review status; do not match ambiguous terms pending review. Course prices, language, account requirements, and credentials may vary; use the recorded verification caveats. Redistribution rights for the job data have not been established, and listing activity is unverified. Confirm data-use rights before production or broader public release.
