# Node.js Backend

The backend is a read-only Node.js HTTP API over the local SQLite database. It runs as one process; there is no external database or separate ML service. It uses Node.js `>=22.13 <23` and the built-in `node:sqlite` module, so no runtime npm packages are required.

## Local setup

1. Prepare the full archive under `data/processed/full_archive_parquet_v1_20261028/` and load it with the documented Python loader. The generated database is `data/processed/job_market.sqlite3` and remains Git-ignored.
2. Set `APP_URL` if the browser app is served from a different origin. Edit `backend/config/app_url.js` or set the `APP_URL` environment variable. Set `JOP_DATABASE_PATH` only when the SQLite file is at a different local path.
3. Start the API from the repository root:

```bash
node --version   # 22.13 or newer in the 22.x line
npm start
```

The server binds to `0.0.0.0` and defaults to port `3000`. `PORT` and `HOST` can be overridden. The API never creates, migrates, or writes to the database; migrations and imports stay in the Python loading tool.

If the local database is missing, the API returns `503 DATA_UNAVAILABLE`; it does not silently use a fixture or partial source. The last full-data validation run restored the checksum-verified archive and SQLite file and checked them; neither ignored artifact is present in the current snapshot, so restore/load them locally before expecting full-data responses.

## Configuration

- `APP_URL`: frontend/application origin for safe CORS; default `http://localhost:3000`, or `https://$VERCEL_URL` when running on Vercel and `APP_URL` is unset.
- `JOP_DATABASE_PATH`: local SQLite file path; default `data/processed/job_market.sqlite3`. URLs and remote DB paths are rejected.
- `HOST`: local listener bind address; default `0.0.0.0`.
- `PORT`: local listener port; default `3000`.

The standalone, editable `app_url` value is in [`config/app_url.js`](config/app_url.js). Never put the SQLite file or its path into frontend configuration.

## API and ML scope

- The route adapter is [`node/api.js`](node/api.js); SQL-backed application operations and metric definitions are in [`node/queries.js`](node/queries.js); SQLite opens read-only in [`node/database.js`](node/database.js).
- The same handler is exposed locally and through the Vercel function [`../api/[...path].js`](../api/%5B...path%5D.js).
- Endpoints, response schemas, inputs, examples, empty states, and errors are in [`docs/software-engineering/API_SPECIFICATION.md`](../docs/software-engineering/API_SPECIFICATION.md).
- `POST /api/v1/matches` is deterministic Jaccard skill-overlap matching, not ML. Separately, `POST /api/v1/models/role-title/predict` runs a positive-evidence Bernoulli Naive Bayes title ranker in Node.js using a bundled JSON artifact; Python training is offline only. The model ranks exact observed title strings, is uncalibrated and limited-scope/review-only, not a production occupational classifier. Offline clustering remains exploratory/report-only; salary regression and active-listing prediction are not served.

## Vercel compatibility boundary

The function entry point and Node 22 runtime are configured. A Vercel function cannot read a SQLite file from a developer's laptop. The database must be present in the deployment build and small enough for the selected serverless limits; Git-based deployments will not contain `data/processed/*` because those generated files are ignored. `vercel.json` includes the expected database path when it is available, but this repository does not contain a deployment copy of the database. If the full archive-backed SQLite file does not fit a Vercel function bundle, use the local demonstration or a host with attached local storage; do not add a network database as a fallback.

## Checks

```bash
npm run check
npm test
```

The API tests use a temporary synthetic SQLite fixture and do not alter the demonstration database. The full archive is not bundled with tests or committed to Git.
