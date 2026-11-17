# Neon PostgreSQL Schema and Loader

The schema and loader are implemented, but this repository has not been loaded into a live Neon database. The loader defaults to the smaller `neon-free` profile; it does not modify any existing full processed files or raw source files.

## Prepare and validate the reduced profile

The generated upload profile is under `data/processed/neon_free/`. Rebuild it from the existing full processed exports and references with:

```bash
python scripts/data_cleaning/build_neon_free_dataset.py
```

The current profile contains all 22,958 country-labeled Arab job rows from the available processed exports and every associated job-skill row. To avoid dropping possible Arab-region listings with ambiguous locations, it also retains all 6,050 rows with blank, `Other/Unknown`, `Remote (Anywhere)`, or `Worldwide` geography. It samples up to 5 named non-Arab rows per `(source_dataset, country)` stratum, retaining 925 rows across 192 strata. All seven source datasets are represented. The current profile has 29,933 jobs and 256,549 job-skill rows, including all 194,673 associations for the country-labeled Arab jobs. The builder writes a quality report with country/source counts and a planning-only storage estimate. It adds new outputs; it does not replace the older processed files.

The new profile consists of:

- `jobs_neon_free.csv.gz` → `jobs`
- `job_skills_neon_free.csv.gz` → `job_skills`
- `skill_observations_neon_free.csv.gz` → `skill_observations`

The loader also imports the existing skill catalog, skill aliases, and learning-resource reference CSV. The full data profile remains available only when requested with `--dataset-profile full`; it uses the original full exports and may exceed a free-plan limit.

Run local preflight without connecting to Neon:

```bash
python scripts/database_loading/load_to_database.py --validate-files-only
```

Preflight checks the selected files, CSV headers and primary-key columns, the profile-specific quality report, and the planning estimate against the default load guard. It does not test PostgreSQL constraints or establish that the data fits Neon storage.

## Create the schema and load into Neon

Run `neon_schema.sql` once against the intended PostgreSQL database using the Neon SQL Editor. Then install the driver:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r scripts/database_loading/requirements.txt
```

In a POSIX shell, set the connection string outside the repository and run the loader:

```bash
export DATABASE_URL='postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require'
python scripts/database_loading/load_to_database.py
```

In Windows PowerShell:

```powershell
$env:DATABASE_URL = 'postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require'
python scripts/database_loading/load_to_database.py
```

The loader enforces SSL when the connection string does not specify a secure `sslmode`. It streams CSV content with PostgreSQL `COPY FROM STDIN`; it does not upload files to object storage. By default it stops if managed tables already contain data. To intentionally replace those managed rows and reload atomically:

```bash
python scripts/database_loading/load_to_database.py --replace-existing-data
```

This truncates managed data tables inside the load transaction. If a load or storage check fails, the data-table changes are rolled back. Credentials must never be stored in Git or shared in logs/chat.

## Storage guard and verification

The builder's current planning proxy is 762,994,614 bytes (about 762.99 MB decimal): five times the uncompressed COPY inputs, plus 64 MiB for fixed overhead. This is **not** an observed database size or a guaranteed upper bound. Actual storage depends on PostgreSQL row layout, TOAST, indexes, page use, existing data, and the Neon project configuration.

The loader measures `pg_database_size(current_database())` and the managed tables' heap, index, and total (including TOAST) sizes after import. It rolls back if the current database exceeds 800,000,000 bytes, leaving nominal headroom below the user's 1 GB target. That measurement covers only the connected database, not every Neon project branch or the whole project quota. Do not raise the guard based only on the planning estimate.

After a successful load, run `neon_storage_report.sql` and verify actual project usage and the applicable free-plan quota in the Neon dashboard. No successful Neon upload or quota fit is claimed until those checks have been performed.

## Data-use and interpretation caveats

The reduced data artifacts are included in this PR by explicit request; that does not establish general redistribution rights. Confirm rights before production or broader publication. Job listing status remains `unknown_not_verified`; source exports do not prove that any listing is active. Keep snapshot and skill-provenance fields intact, and do not infer posting dates from update fields.
