# Deployment and Operations

**Status:** Implemented local Node.js API backed by read-only SQLite, with in-process Jaccard matching and a limited-scope Naive Bayes exact-title ranker. The last full-data validation run passed database integrity checks and selected HTTP smoke tests. The ignored database/archive are not tracked and are absent from the current snapshot. A Vercel-compatible function route exists, but full-dataset Vercel deployment is not verified and requires the database to be explicitly included in the function deployment package. No remote database is configured or permitted by this architecture.

## Local Environment

- Node.js `>=22.13 <23`; built-in `node:sqlite`; no runtime npm dependencies.
- Python loader/data tools are separate from the Node request process.
- Default local database: `data/processed/job_market.sqlite3` (Git-ignored).
- Default app origin: `http://localhost:3000`; configurable with `APP_URL`.
- Default listener: `0.0.0.0:3000`; configurable with `HOST` and `PORT`.

### Restore the full local dataset

The complete `full_archive_parquet_v1_20261028` package is stored in the preserved Google Drive archive. Download the package into `data/processed/full_archive_parquet_v1_20261028/`, then use the existing loader. Do not change the original Drive files or raw source files.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r scripts/database_loading/requirements.txt
python scripts/database_loading/load_to_database.py load --source archive
python scripts/database_loading/load_to_database.py check
```

The loader applies all ordered SQLite migrations, including API rollups and role-skill lookup indexes in migrations 004–005. Existing data is not replaced unless an intentional rebuild is requested with the loader's documented `--replace` option. The API itself never migrates, initializes, or writes to the database.

### Start and verify the API

```bash
node --version
npm test
npm run check
npm start
```

Smoke checks:

```bash
curl -i http://localhost:3000/health
curl -i http://localhost:3000/api/v1/metadata
curl -i 'http://localhost:3000/api/v1/overview'
```

In the last full-data run, the ignored local database and Parquet archive were restored. `load_to_database.py check` reported 775,155 jobs, 4,026,953 stored job-skill links, migrations 001–005, and zero foreign-key violations. Selected routes (health, overview, role analysis, Jaccard matching, Naive Bayes prediction/status) were exercised over HTTP against that database. The current snapshot no longer contains those ignored files; until restored locally, data-dependent endpoints correctly return `503 DATA_UNAVAILABLE`. Automated API tests also use an isolated synthetic SQLite fixture.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `APP_URL` | `http://localhost:3000` | Application/frontend origin and exact CORS allow-origin |
| `JOP_DATABASE_PATH` | `data/processed/job_market.sqlite3` | Local SQLite file path; connection URLs are rejected |
| `HOST` | `0.0.0.0` | Local listener bind address |
| `PORT` | `3000` | Local listener port |
| `VERCEL_URL` | Platform-provided | HTTPS origin fallback only when `APP_URL` is unset |

`backend/config/app_url.js` is the separate editable app URL configuration. Environment configuration may override it without changing database configuration.

## Vercel Compatibility and Limits

- `api/[...path].js` exports the same Node.js API handler; `vercel.json` configures the route and includes the expected SQLite file path when the file exists in the deployment context.
- A Vercel function is hosted separately from a developer's PC. It cannot read an absolute local path on that PC. `data/processed/*` is Git-ignored, so an ordinary Git-based Vercel build will not contain the local database.
- To serve data on Vercel without a database service, the SQLite file must be explicitly available as part of the deployment artifact and fit Vercel's function/package limits. This project has not measured a full database bundle here; do not claim a full-data Vercel deployment works until a deployment build confirms it.
- The function filesystem is not a persistent writable database volume. The API uses read-only SQLite and requires no writes. Updates require rebuilding/redeploying the bundled file.
- If the complete database does not fit or cannot be included under the permitted deployment setup, use the full-data local demonstration or a host with attached local storage. Do not add Neon, Supabase, a hosted database, or a remote database URL as an automatic fallback.

## Security, Privacy, and Logging

- SQLite stays server-side and read-only in application requests; no DB path is returned to the browser.
- Skill input is not persisted, cached, or logged; the request body is capped at 32 KiB and at 50 skills.
- Logs contain only a request ID and error category for unexpected errors. Do not add request URLs, SQL, stack traces, source descriptions, skill lists, or credentials to logs.
- CORS allows only the configured `APP_URL` origin. Same-origin frontend requests should use relative `/api/v1` URLs.
- Job descriptions and other source text are untrusted. The client must render them as text, not HTML.
- The source listing status is unverified; external URL availability and dataset redistribution rights are not certified by deployment.

## Backup and Recovery

1. Keep a known-good local copy of `job_market.sqlite3` and the verified Parquet archive in approved local storage.
2. Back up SQLite consistently (or stop the local API before copying); preserve WAL sidecars if present.
3. Apply new migrations and loader changes against a temporary copy first.
4. Run the loader integrity check and API contract tests before replacing a demonstration database.
5. Do not use the API to write, migrate, or repair the database. Rebuild from the verified archive with the Python loader if necessary.

## Monitoring and Release Readiness

Before a complete-data demo, verify archive checksum, migration versions 001–005, 775,155 jobs, 4,026,953 stored links, foreign keys, and reconciled eligible-skill counts; those checks passed in the last full-data run. Selected API paths were smoke-tested, but release readiness still requires a full per-route reconciliation including job details, compare, historical trends, resources, and validation/empty/error states. Browser-locale checks cannot be run until a frontend exists. Measure read-query latency/concurrency against the full local database. Before any public Vercel release, confirm source redistribution permissions and independently validate the full database bundle size and cold-start behavior.
