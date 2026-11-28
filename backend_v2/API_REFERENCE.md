# JOP Marketing Intelligence API v2 — Reference

This is the complete API reference for the standalone Node.js backend in `backend_v2/`. It is also served as Markdown at `GET /api/v2/docs`.

## 1. Run the service and configure the database

- **Node.js:** 22.x, version 22.13 or later. The service uses the built-in `node:sqlite`; no Python runtime or separate ML service is required.
- **Start locally:** from the `backend_v2` directory, run `npm start`. The default port is `4000`; the server binds to `0.0.0.0`. Set `PORT` or `HOST` to override these values.
- **Default local database:** `../data/processed/jobs_cleaned_audited.sqlite3`, relative to the `backend_v2/` directory. Override it with `DATASET_DB_PATH`. A valid SQLite database is required for health and analytics endpoints.
- **Database files are not included in the Git repository** because of their size. If the configured file is absent, health and analytics requests return HTTP `503` with `DATABASE_NOT_FOUND`; analytics cannot return results without a database. `DATASET_DB_PATH` may point to a complete `.sqlite3` file or a `.sqlite3.gz` file that decompresses to no more than 512 MiB and has the required schema. Use the uncompressed `.sqlite3` for the full 7.65 GB source; the compact projection is suitable for gzip materialization.
- **Performance:** the full local source database is about 7.65 GB. In the recorded Node.js 22 test run, a dashboard calculation on the compact projection took about 33 seconds when no matching dashboard snapshot was available, and a Data Engineer role report on the full source database took about 43 seconds. These are environment-specific observations, not timing guarantees. A valid database can therefore produce slow cold analytics queries.
- **Faster dashboard startup:** when provisioned, the compact deployment database is `backend_v2/data/jobs_analytics.sqlite3.gz` (about 79.5 MB), and `backend_v2/reports/dashboard-data.json` provides a precomputed dashboard snapshot. If you have the full source database, build both with `npm run analytics:build-deploy-db`. The snapshot is used only when its dataset timestamp matches the database; an absent or stale snapshot triggers live calculations. Neither database file is committed to Git.
- **Vercel:** when `VERCEL=1`, the default database path is `backend_v2/data/jobs_analytics.sqlite3.gz`. The function materializes the gzip file in a temporary directory and opens SQLite read-only. Before packaging, provide the database file, model artifact, reports, dashboard, and API reference listed in `vercel.json`.

Windows Command Prompt example, assuming the database is stored at the default repository path:

```cmd
cd /d D:\project_depi\backend_v2
set "DATASET_DB_PATH=D:\project_depi\data\processed\jobs_cleaned_audited.sqlite3"
npm start
```

If the database is elsewhere, set `DATASET_DB_PATH` to its actual full path. The value must point to an existing database file; setting a path alone does not download or create the database. The `DATABASE_NOT_FOUND` message reports the path the running process actually tried to open.

After obtaining the full source database, you can build and run against the compact projection from Command Prompt:

```cmd
cd /d D:\project_depi\backend_v2
set "DATASET_DB_PATH=D:\project_depi\data\processed\jobs_cleaned_audited.sqlite3"
npm run analytics:build-deploy-db
set "DATASET_DB_PATH=D:\project_depi\backend_v2\data\jobs_analytics.sqlite3.gz"
npm start
```

This build requires the source SQLite file to exist first. The gzip projection is a Node.js SQLite database, not a replacement download for the missing source file.

The source database was reconstructed from the 11 authorized SQLite parts in the `NADA` Drive folder. Its 775,155 source records were checked against the cleaned-data manifest and summary. The CSV parts were not downloaded for a row-by-row comparison; validation limits and provenance details are documented in `TESTING_NOTEBOOK.md`.

### Main routes

| Method | Full path | Purpose |
|---|---|---|
| `GET` | `/` or `/dashboard` | Arabic dashboard HTML |
| `GET` | `/health` or `/api/v2/health` | Database connection and schema check |
| `GET` | `/api/v2` | API name, version, and links |
| `GET` | `/api/v2/docs` | This English Markdown reference |
| `GET` | `/api/v2/analytics/overview` | Overall job, role, country, salary, and work-mode summary |
| `GET` | `/api/v2/analytics/dashboard` | Dashboard-ready analytics JSON |
| `GET` | `/api/v2/analytics/roles` | Search job titles |
| `GET` | `/api/v2/analytics/role` | Full report for a job title |
| `GET` | `/api/v2/analytics/role/countries` | Country distribution for a job title |
| `GET` | `/api/v2/analytics/role/skills` | Skills associated with a job title |
| `GET` | `/api/v2/analytics/role/technology-combinations` | Co-occurring skills for a job title |
| `GET` | `/api/v2/analytics/role/salaries` | Annual salary data for a job title |
| `GET` | `/api/v2/analytics/role/work-mode` | Work-mode data for a job title |
| `GET` | `/api/v2/analytics/skills` | Most common skills across all jobs |
| `GET` | `/api/v2/analytics/work-mode` | Overall or title-specific work-mode summary |
| `GET` | `/api/v2/analytics/markets/arab-vs-international` | Arab, international, and unknown market comparison |
| `POST` | `/api/v2/ml/skill-to-job-match` | Explainable skill-to-job matching |
| `GET` | `/api/v2/ml/job-family/status` | Model status and non-blocking label-quality audit |
| `POST` | `/api/v2/ml/job-family/predict` | Predict a stored `role_family` class from job text |

All API routes use the `/api/v2` prefix unless noted otherwise. The API has no built-in authentication; add an access-control layer before exposing it publicly if needed.

## 2. Response format and errors

### Successful JSON response

```json
{
  "success": true,
  "data": {},
  "meta": { "requestId": "..." }
}
```

The same request ID is returned in the `X-Request-Id` header. Clients may send `x-request-id`; values are truncated to 80 characters.

### Error response

```json
{
  "success": false,
  "error": { "code": "BAD_REQUEST", "message": "..." },
  "meta": { "requestId": "..." }
}
```

| HTTP | Example codes | Meaning |
|---:|---|---|
| `400` | `BAD_REQUEST` | Invalid parameter, request body, or JSON |
| `404` | `NOT_FOUND` | Unknown route or a requested role was not found |
| `413` | `BODY_TOO_LARGE` | Request body exceeds the configured limit (64 KiB by default) |
| `503` | `DATABASE_*`, `MODEL_NOT_BUILT`, `MODEL_ARTIFACT_INVALID` | Database unavailable or model artifact missing/invalid |
| `500` | `INTERNAL_ERROR` or an underlying error code | Unexpected server error; details are hidden in production |

The service accepts `OPTIONS` and responds with `204` and `Allow: GET, POST, OPTIONS`. It does not enable public CORS; the bundled dashboard uses same-origin requests.

## 3. Health, API information, and dashboard

### `GET /api/v2/health` and `GET /health`

Opens the database in read-only mode, verifies the required schema, and runs a lightweight query. It does not run a full `quick_check` on every request.

Healthy response example:

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "database": "read-only-connected",
    "apiVersion": "v2"
  },
  "meta": { "requestId": "..." }
}
```

If the database is missing, the response is HTTP `503`, for example:

```json
{
  "success": false,
  "error": {
    "code": "DATABASE_NOT_FOUND",
    "message": "SQLite database not found at ..."
  },
  "meta": { "requestId": "..." }
}
```

A `DATABASE_NOT_FOUND` response means the configured file is absent; analytics routes require that file as well. Verify `DATASET_DB_PATH` and the file itself before testing analytics.

### `GET /api/v2`

Returns the service name, version, and links to documentation and health. It does not need to open the database.

### `GET /api/v2/docs`

Returns this file with `Content-Type: text/markdown; charset=utf-8`.

### `GET /`, `GET /dashboard`, and `GET /api/v2/dashboard`

Return the responsive Arabic dashboard HTML. The dashboard includes charts for roles, countries, skills, work modes, and market comparisons, plus a job-title search. Vercel rewrites `/` and `/dashboard` to `/api/v2/dashboard`.

## 4. General analytics

### `GET /api/v2/analytics/overview`

No parameters are required. Important response fields include:

- `totalJobs`: total job advertisements.
- `distinctRoles`: distinct non-empty `title_key` values; this is not the number of occupational families.
- `distinctCountries`: distinct non-empty standardized country values.
- `sourceCount`: number of source datasets.
- `topRole`: the most frequent role, including `roleKey`, `title`, and `advertisementCount`.
- `workModes`: counts by stored work-mode category.
- `salaryCoverage`: records with a usable annual value for USD, EGP, and SAR (the center value, or the midpoint of both bounds when the center is missing).
- `generatedAt` and `salaryBasis`.

### `GET /api/v2/analytics/dashboard`

Returns chart-ready JSON: `overview`, `topRoles`, `topCountries`, `topSkills`, `marketComparison`, `workModes`, and `charts`. The service uses a prebuilt dashboard snapshot when its dataset timestamp matches the database metadata. If the snapshot is missing or stale, it calculates the response from SQLite. In the recorded Node.js 22 run, this cold calculation took about 33 seconds on the compact projection; use a matching snapshot for a faster first dashboard load.

Each chart payload contains a chart type, unit, labels, and values. Clients may render these with SVG, Canvas, or a chart library; the backend does not depend on an external chart service. The bundled browser dashboard aborts a pending request after 60 seconds and displays an error rather than leaving its status message in a loading state. This is a client-side timeout only: it does not cancel a synchronous SQLite query already running in Node.js. Other API clients should set their own request timeout.

### `GET /api/v2/analytics/roles?q={prefix}&limit={n}`

- `q` is optional. When supplied, it performs a normalized prefix search over `title_key`.
- `limit` is optional; default `25`, range `1–100` (or the configured `MAX_API_LIMIT`).
- Returns `{ query, roles }`. Each role contains `roleKey`, `title`, and `advertisementCount`.

Example:

```bash
curl "http://localhost:4000/api/v2/analytics/roles?q=data%20eng&limit=10"
```

### `GET /api/v2/analytics/skills?limit={n}`

The default limit is `25`; valid range is `1–100`. Returns `denominatorAdvertisements` and ranked skills. Each skill includes `skillId`, `skill`, `category`, `advertisementCount`, and `appearancePctOfAllAds`. The percentage denominator is all job advertisements, not the total number of job-skill links.

### `GET /api/v2/analytics/work-mode[?title={role}]`

Without `title`, summarizes the entire database; with `title`, summarizes the normalized role. Response fields include `role`, `denominatorAdvertisements`, `categories`, `remotePct`, `nonRemotePct`, `hybridPct`, `unknownPct`, and `interpretation`.

Stored categories are `remote`, `not_remote_explicit`, `hybrid`, and `unknown_or_unmapped`. **`not_remote_explicit` means the advertisement was not explicitly classified as remote; it does not prove that the job is office-based.**

## 5. Full role report and role-specific routes

### `GET /api/v2/analytics/role?title={role}`

The `title` parameter is required. Matching uses normalized `title_key`, not a partial search. If the title is absent from the database, the API returns `404 NOT_FOUND`.

Example:

```bash
curl --get "http://localhost:4000/api/v2/analytics/role" \
  --data-urlencode "title=Data Engineer"
```

Important fields in `data`:

- `role`: normalized role key and display title.
- `advertisementCount`, `sourceCount`, and `roleFamilyLabelsPresent`.
- `countryDemand`: per-country `roleAdvertisements`, `totalAdvertisementsInCountry`, `roleShareOfItsAdvertisementsPct`, and `roleDemandWithinCountryPct`.
  - `roleShareOfItsAdvertisementsPct` = role advertisements in the country ÷ all advertisements for this role.
  - `roleDemandWithinCountryPct` = role advertisements in the country ÷ all advertisements in that country.
- `mostDemandCountries`: the top 10 countries by role advertisement count.
- `skills`: `skillId`, `skill`, `category`, `advertisementCount`, and `appearancePctOfRoleAds`. The denominator is all advertisements for the role.
- `technologyCombinations`: skill pairs appearing in the same advertisement, with co-occurrence counts and percentages. Co-occurrence does not imply order or causality.
- `annualSalaryByCountry`: advertisement counts and annual `USD`, `EGP`, and `SAR` salary summaries per country.
- `workMode`: categories, percentages, denominators, and an interpretation of non-remote labels.
- `storedFamilyLabelDistribution`: a descriptive distribution of stored `role_family` values; it is not a model prediction or independently reviewed ground truth.
- `charts`: chart-ready country, skill, salary, work-mode, and skill-combination data.

### Role-specific subroutes

Every route below requires `?title=...` and returns `{ role, data }`:

| Route | `data` |
|---|---|
| `/api/v2/analytics/role/countries` | Country distribution and demand percentages |
| `/api/v2/analytics/role/skills` | Role skills and appearance percentages |
| `/api/v2/analytics/role/technology-combinations` | Co-occurring skill pairs |
| `/api/v2/analytics/role/salaries` | Annual salary means, ranges, and coverage by currency/country |
| `/api/v2/analytics/role/work-mode` | Work-mode counts and percentages |

Example:

```bash
curl --get "http://localhost:4000/api/v2/analytics/role/salaries" \
  --data-urlencode "title=Data Engineer"
```

## 6. Annual salaries

The API uses the populated annual columns `salary_annual_min_*`, `salary_annual_salary_*`, and `salary_annual_max_*` for USD, EGP, and SAR. It does not use the older raw salary columns, which may be empty. Each currency is reported independently. Example values for the United States Data Engineer group in the recorded test dataset:

```json
{
  "currency": "USD",
  "period": "annual",
  "records": 9659,
  "mean": 156858.22,
  "range": { "minimum": 90000, "maximum": 156862.5 },
  "estimateStatusCounts": { "estimated": 9658, "actual": 1, "unverified": 0 }
}
```

- `mean`: average of the usable annual values; if the center is missing, the midpoint of both bounds is used when available.
- `range.minimum` / `range.maximum`: smallest available lower bound and largest upper bound in the group; a center value is used when the corresponding bound is missing.
- `averageAdvertisedLowerBound` / `averageAdvertisedUpperBound`: mean of the per-row annual lower/upper values, falling back to the center value when that bound is missing.
- `records`: rows with a usable annual value (the center value, or the midpoint of both bounds when the center is missing).
- `estimateStatusCounts`: known estimate statuses among included rows. `Not disclosed` and `Unparseable` rows normally do not enter the salary denominator.
- Do not combine USD, EGP, and SAR into one average. `Estimated` values are derived estimates, not confirmed offers or financial advice.

## 7. Arab vs. international markets

### `GET /api/v2/analytics/markets/arab-vs-international?limit={n}`

`limit` is optional; default `15`, range `1–100`. The response includes:

- `counts`: advertisement and distinct-role counts for each market.
- `salaries`: annual salary means, ranges, record counts, and estimate statuses per currency/market.
- `topSkillsByMarket`: top skills and each skill's share of advertisements in that market.
- `topRolesByMarket`: most frequent roles per market.
- `marketDefinitions`, `salaryBasis`, and chart payloads.

Market groups are `arab` (standardized Arab countries plus configured UAE/KSA aliases), `international` (a non-empty, non-Arab country value), and `unknown` (empty location or non-geographic scopes such as `worldwide`, `remote`, or `anywhere`). Unknown values are not forced into either market.

## 8. Skill-to-job matching — `POST /api/v2/ml/skill-to-job-match`

Send a JSON body. Example:

```bash
curl -X POST "http://localhost:4000/api/v2/ml/skill-to-job-match" \
  -H "content-type: application/json" \
  -d '{"skills":["Python","SQL"],"country":"Egypt","workMode":"remote","limit":5}'
```

| Field | Type | Default / limits |
|---|---|---|
| `skills` | Array of skill names or IDs | Required; 1–40 items |
| `country` | Optional country string | Exact match after normalization |
| `workMode` | Optional string | `remote`, `hybrid`, `non_remote`, or `unknown`; aliases include `onsite` and `not_remote_explicit` |
| `roleFamily` | Optional string | Matches a stored role-family key after normalization |
| `limit` | Optional integer | Default `10`; clamped to `1–20` |

The response includes `scoringMethod`, `inputSkillCount`, `matchedCanonicalSkills`, `unknownSkills`, `ambiguousSkills`, `filters`, `advertisements`, `roleProfiles`, and `limitations`. Each matched advertisement may include `matchedSkills`, `missingSkills`, `userSkillCoveragePct`, and `advertisementSkillCoveragePct`.

Skill matching uses exact canonical names and aliases after normalization; it does not silently use fuzzy matching. Ambiguous skills include `choices`. If no input skill resolves to the catalogue, the response explains the issue and returns no matches.

**Important:** Skill coverage is descriptive overlap, not a hiring probability or a complete measure of candidate suitability. Missing skills are based on frequency in the dataset, not a personalized learning recommendation.

## 9. Job-family classification — separate ML stage

The Node.js classifier targets stored `role_family` labels and uses `title_clean` plus `description_raw` as text inputs. It uses word unigram/bigram TF-IDF with Multinomial Naive Bayes. Training targets `role_family`, not `category_raw`, and does not require a label-review approval flag.

### Train and evaluate

From `backend_v2`:

```bash
DATASET_DB_PATH=../data/processed/jobs_cleaned_audited.sqlite3 npm run ml:train-family
# Evaluate without writing a model artifact:
DATASET_DB_PATH=../data/processed/jobs_cleaned_audited.sqlite3 npm run ml:evaluate-family
```

Training reads the full source database read-only and assigns identical normalized title/description text groups to one deterministic SHA-256 split. The model artifact is `models/job-family-model.json.gz`; the full evaluation, including per-class precision/recall/F1 and a confusion matrix, is `reports/job-family-model-evaluation.json`.

The current run used 775,155 labeled rows across 16 classes: 612,197 train, 58,010 reserved validation, and 104,948 test records across 19,699 distinct test text groups. Test metrics: **94.15% accuracy**, **76.70% macro-F1**, and **94.15% weighted-F1**. These measure agreement with stored `role_family` labels, not independently human-reviewed ground truth. Class support is imbalanced; for example, `ux_ui_design` has only 8 test examples (F1=0.50). The `description_raw` field is present on only 26,494 rows (3.4179%), so most training examples rely on job titles.

### `GET /api/v2/ml/job-family/status`

Returns `decision` (`MODEL_READY` or `MODEL_NOT_BUILT`), `predictionEnabled`, `targetField`, model metadata, evaluation metrics, and `labelQualityAudit`. The audit may still show `NO_GO` because review-provenance metadata is absent. This is an informational caveat, not a training or prediction gate. A missing model artifact—not the label audit—is what disables prediction.

### `POST /api/v2/ml/job-family/predict`

Send either a `text` field or a `title` and/or `description`:

```bash
curl -X POST "http://localhost:4000/api/v2/ml/job-family/predict" \
  -H "content-type: application/json" \
  -d '{"title":"Data Engineer","description":"Build Python and SQL pipelines"}'
```

A text-only body is also supported: `{ "text": "Data Engineer — Python, SQL, and data pipelines" }`. The combined input must not exceed 16,000 characters. The response includes `data.roleFamily`, `data.targetField` (`role_family`), `modelVersion`, `algorithm`, and `trainedAtUtc`. No uncalibrated confidence or probability is returned. Inference loads the model artifact only and does not open the analytics SQLite database. If the artifact is missing, the route returns `503 MODEL_NOT_BUILT`, not `409` for label quality.

## 10. Limits, normalization, and caching

- `title` is matched against normalized `title_key`, not partial text. Use `/analytics/roles?q=...` for prefix search before requesting a report.
- The general API limit is capped by `MAX_API_LIMIT` (default `100`). Invalid or out-of-range values return `400`; they are not silently coerced.
- JSON request bodies are limited by `MAX_BODY_BYTES` (default `64 KiB`, configurable up to `1 MiB`). The job-family text input has a separate 16,000-character limit.
- Analytics responses are cached in memory for `CACHE_TTL_MS` (default `30,000 ms`, maximum `300,000 ms`). Each serverless instance may have its own cache.
- SQLite is opened in read-only mode with `query_only`; requests do not write to source or deployment databases.
- Vercel requires `backend_v2/` as the project root and provisioned copies of `data/jobs_analytics.sqlite3.gz`, `models/job-family-model.json.gz`, `reports/job-family-model-evaluation.json`, `reports/job-family-readiness.json`, and `reports/dashboard-data.json`. See `README.md` and `TESTING_NOTEBOOK.md`. No Vercel deployment was performed for this release.
