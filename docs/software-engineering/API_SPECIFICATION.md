# API Specification — Node.js Local SQLite Backend

**Status:** Node.js HTTP API at `/api/v1` and a Vercel-compatible function entry point are implemented. In the last full-data validation run, the checksum-verified archive was loaded and reconciled: all 775,155 job rows, 4,026,953 job-skill links, 3,701,019 eligible links, rollup totals, and zero foreign-key violations were checked. Selected endpoints also passed HTTP smoke tests against that full local SQLite file. The SQLite file and archive are ignored local artifacts and are absent from the current snapshot; restore them using the documented loader before repeating full-data checks. Synthetic API tests pass. The served title-association model is limited-scope/review-only, not an approved production occupational classifier.

## 1. Runtime and Data Boundary

- Node.js `>=22.13 <23`; the API uses the built-in `node:sqlite` module and no runtime npm dependencies.
- The only application data source is a local SQLite file. The API opens it read-only and rejects connection URLs; it never falls back to a network database or a partial sample.
- Default path: `data/processed/job_market.sqlite3`. An override through `JOP_DATABASE_PATH` or the loader's `--database` option must resolve inside the repository root; absolute, traversal, and symlink-resolved paths outside the root are rejected. No external or hosted database is supported.
- Migrations `001`–`005` create the relational schema, query indexes, API rollups, and a role-skill lookup index. The Python loader populates and validates derived rollups transactionally; the API requires those tables and always opens the local SQLite file read-only.
- `APP_URL` is configured independently in `backend/config/app_url.js` and is also used as the exact browser CORS origin. The deployment platform's `VERCEL_URL` is a fallback when `APP_URL` is unset.
- Skill-match request bodies are processed for the current request only. They are not written to the database, cached, or logged.
- On Vercel, a function can read only files included in its deployment package. It cannot access a developer's computer. The SQLite file is Git-ignored, and large local SQLite packages may exceed a serverless deployment's limits; see [Deployment Operations](DEPLOYMENT_OPERATIONS.md). No hosted database is introduced as a workaround.

## 2. HTTP and Response Conventions

Base path: `/api/v1`. JSON uses UTF-8 and camelCase field names.

### Success

```json
{
  "data": { "...": "endpoint-specific result" },
  "meta": {
    "apiVersion": "v1",
    "requestId": "correlation-id",
    "snapshot": {
      "importRunId": 1,
      "archiveRunId": "full_archive_parquet_v1_20261028",
      "generatedOnUtc": "2026-10-28"
    },
    "servedAt": "2026-10-28T12:00:00.000Z"
  }
}
```

`snapshot` is `null` if no successful import run is recorded. Each list response includes `items` and `pagination`:

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "totalItems": 0,
    "totalPages": 0,
    "hasNextPage": false,
    "hasPreviousPage": false
  }
}
```

A well-formed search with no matches returns **200** and an empty `items` or `series` array. Missing fields are `null` or absent only where documented; they are never converted to zero. Every percentage includes its count and denominator.

### Errors

```json
{
  "error": {
    "code": "INVALID_QUERY_PARAMETER",
    "message": "The 'pageSize' value must be between 1 and 100.",
    "requestId": "correlation-id",
    "details": { "field": "pageSize" }
  }
}
```

| Status | Meaning |
|---|---|
| `400` | Malformed JSON, invalid value, duplicate or unknown parameter |
| `404` | Unknown job, skill, role, or route |
| `405` | Method not allowed; includes `Allow` |
| `413` | Request body exceeds 32 KiB |
| `415` | Match request is not `application/json` |
| `422` | Valid request uses a disabled metric/filter, or no entered skill resolves to the reviewed catalogue |
| `503` | Local SQLite file or required schema is missing/unavailable |
| `500` | Unexpected error; generic message only |

Unexpected errors are logged with request ID and error category only. SQL, filesystem paths, request URLs, stack traces, credentials, and submitted skill text are not logged or returned.

## 3. Endpoint Catalogue

| Method and path | Purpose | Query/body |
|---|---|---|
| `GET /health` or `GET /api/health` | Readiness check; verifies required SQLite tables and returns a record count | None |
| `GET /api/v1` | API index | None |
| `GET /api/v1/metadata` | Snapshot, source totals, field coverage, supported filters, and data limitations | None |
| `GET /api/v1/overview` | Dashboard KPIs, country counts, top 10 eligible skills, and fixed Arab/other-market comparison | `sourceDataset`, `country` optional |
| `GET /api/v1/jobs` | Paginated secondary advertisement explorer | Job search/filter contract below |
| `GET /api/v1/jobs/{recordId}` | One source record with raw details and reviewed skill links | Stable `record_id` |
| `GET /api/v1/roles` | Exact-normalized title suggestions ranked by source-row count | `q`, `sourceDataset`, `country`, pagination |
| `GET /api/v1/roles/{roleId}/analysis` | Role counts, country distribution, eligible-skill demand overall/by country, and salary-field/provenance coverage overall/by country (no salary average is currently available) | `sourceDataset`, `country` optional |
| `GET /api/v1/roles/{roleId}/ads` | Optional related-advertisement view | Job explorer filters and pagination |
| `GET /api/v1/markets/compare` | Arab markets vs other represented markets in `merged_tech_jobs` | `limit` (1–50, default 10) |
| `GET /api/v1/markets/trends` | Historical monthly records only | `metric=jobRecords`, `year=2023`, `period=month`, optional `country`; source is fixed to `international_jobs` |
| `GET /api/v1/skills` | Reviewed skill catalogue and within-scope demand counts | `q`, `sourceDataset`, `country`, `roleId`, `workModeRaw`, `experienceRaw`, pagination |
| `GET /api/v1/skills/co-occurrence` | Related-skill counts and Jaccard co-occurrence | Required `skillId`; optional scope filters and `limit` |
| `GET /api/v1/skills/{skillId}/resources` | Linked curated resources | `language`, `freeOnly`, pagination |
| `POST /api/v1/matches` | Temporary, explainable deterministic role matching by Jaccard skill overlap (not ML) | JSON body below |
| `POST /api/v1/models/role-title/predict` | In-process Naive Bayes ranking of sufficiently supported observed title strings from reviewed skill inputs | JSON body below |
| `GET /api/v1/models/status` | Model, deterministic baseline, offline experiment, and disabled-task inventory | None |
| `GET /api/v1/methodology` | Metric definitions, eligibility policy, and limitations | None |

## 4. Search, Filter, and Pagination Rules

### Job explorer and related advertisements

Supported query parameters:

- `q`: 2–120 characters; case-insensitive literal substring in title, company, city, or country. `%` and `_` are treated literally, not as wildcards.
- `sourceDataset`: exact source key returned by metadata.
- `country`: exact normalized label (case and surrounding whitespace ignored); no ISO country-code inference.
- `roleId`: exact title after lowercase/case normalization and outer whitespace trimming; punctuation and seniority variants stay distinct.
- `skillId`: reviewed eligible skill ID only.
- `workModeRaw`, `experienceRaw`: exact normalized comparison against the preserved source value. These are not standardized taxonomies.
- `page`: positive integer, default `1`.
- `pageSize`: integer `1–100`, default `20`.
- `sort`: `title`, `company`, `country`, or `sourceDataset`; default `title`.
- `order`: `asc` or `desc`; default `asc`.

Salary filters (`minSalary`, `maxSalary`, `salaryMin`, `salaryMax`) return **422 `UNSUPPORTED_FILTER`**. Salary currencies, periods, and provenance do not support a safe cross-record filter. Active/open status is not a supported filter because all source listing statuses are unverified.

List items omit the full description. Job details may include the original description as untrusted source text; the frontend must render it as text, not executable HTML. External URLs are returned only for `http`/`https` schemes and must still be opened safely by the client.

### Role suggestions and analysis

`roles?q=...` uses a normalized title prefix, not fuzzy or semantic title matching. `roleId` is the normalized title returned by `/roles`. Role analysis denominator for a country share is role records with a usable country label. Skill shares use only role records with at least one eligible reviewed skill.

A role that exists but has no records in the selected `sourceDataset`/`country` scope returns a successful empty analysis. An unknown title returns `404`.

### Skill eligibility and percentages

The API includes a job-skill link only when both `job_skills` and `skills` agree on one of these pairs:

1. `(match_policy='approved_aliases', review_status='curated')`
2. `(match_policy='exact_only', review_status='curated_exact_only')`

All `needs_review`, `needs_owner_review`, `exclude_pending_review`, and mismatched policy/status links remain stored but do not enter product metrics, co-occurrence, or matching. Alias lookup is explicit and conservative; no fuzzy synonyms are guessed.

For a skill, `sharePercent = 100 × distinct records linked to that skill / distinct records with at least one eligible reviewed skill` within the same cohort. This is an observed sample share, not hiring probability or proof of a mandatory requirement.

## 5. Endpoint Details and Examples

### Overview

```http
GET /api/v1/overview?sourceDataset=merged_tech_jobs
```

`data.kpis` contains `totalJobs`, `totalSkills`, `totalCountries`, and `recordsWithEligibleSkills`. `countryMap` contains `countryKey`, display label, and `jobRecordCount`. `topSkills` contains `skillId`, `name`, `category`, `jobRecordCount`, `denominator`, and `sharePercent`. The market comparison is intentionally fixed to `merged_tech_jobs` even when overview filters are applied; it is labelled separately in the response.

The comparison cohorts are labelled **Arab markets** and **Other represented markets**, not “global market”. The grouping uses the documented 22 country-name allowlist and excludes `Remote (anywhere)`, `Worldwide`, and `Other/Unknown`. A missing Arab-country label is reported as unrepresented coverage, never as zero jobs.

### Job search

```http
GET /api/v1/jobs?q=data%20engineer&country=Egypt&page=1&pageSize=20&sort=company&order=asc
```

Job list records include source, location, raw work/experience values, raw salary fields with provenance, separately identified source dates, safe source URL, and `listingStatus`. They do not claim a record is active.

### Role analysis

```http
GET /api/v1/roles/data%20engineer/analysis?sourceDataset=merged_tech_jobs
```

The `salary` object always explains availability. In the current archive it is `available:false`; no arithmetic mean, median, currency conversion, or regression estimate is returned. It includes `recordsWithAnySalaryField`, annual/hourly field counts, explicit-currency and provenance counts, annual/hourly values with matching currency/pay-period counts, and `byCountryCoverage`. Each country row includes `roleCountryRecordCount`, salary-field count, field-coverage percent, currency/provenance counts, and a denominator. A zero salary-field count means no such field was present in that sample, not a zero salary amount. `relatedAdsPath` links to the secondary job list.

### Market comparison and historical trends

```http
GET /api/v1/markets/compare?limit=10
GET /api/v1/markets/trends?metric=jobRecords&year=2023&period=month&country=Egypt
```

Trends are limited to explicit `posted_at` fields in `international_jobs` during 2023. Mixed `source_updated_at` values are not used as posting dates. Other years, metrics, periods, or sources return `422 UNSUPPORTED_TREND`.

### Learning resources

```http
GET /api/v1/skills/skill%3Apython/resources?language=English&freeOnly=true&page=1&pageSize=20
```

Only `costStatus=free_verified` qualifies for `freeOnly=true`. Every returned record preserves cost, access, account, credential, verification date, and notes as recorded. These fields may be stale and do not imply a current availability check.

### Skill matching (no persistence)

Request:

```http
POST /api/v1/matches
Content-Type: application/json
```

```json
{
  "skills": ["Python", "SQL"],
  "country": "Egypt",
  "workMode": "Remote",
  "sourceDataset": "merged_tech_jobs",
  "limit": 10
}
```

- `skills`: required array of 1–50 strings, each 1–80 characters.
- `country`, `workMode`, `sourceDataset`: optional filters. `workMode` compares to the exact preserved raw source value.
- `limit`: optional integer 1–25, default `10`.
- Unknown or ambiguous skill labels are returned in `input.unrecognizedSkills`. If no label resolves to a reviewed skill, return `422 NO_SUPPORTED_SKILLS`.
- A recognized input with no matching records is a valid `200` with `results: []`.

The current implementation ranks role profiles using the deterministic Jaccard set overlap:

`J(U,J) = |U ∩ J| / |U ∪ J|`

Results include matched, missing, and user-only skills; directional coverage; and the number of records supporting each role profile. Missing skill lists are ranked by observed record count. No score is calibrated as probability, suitability, or employment success. Inputs are not logged or stored.

### Trained title-ranking model (separate from Jaccard)

```http
POST /api/v1/models/role-title/predict
Content-Type: application/json
```

```json
{
  "skills": ["Python", "SQL"],
  "limit": 5
}
```

- `skills` is required and must contain 2–50 non-empty labels (at most 80 characters each); `limit` is optional, 1–25, default `5`.
- Input labels are resolved only through the reviewed skill catalogue. Ambiguous or unrecognized labels are returned separately. At least two recognized skills must also exist in the trained vocabulary; otherwise the endpoint returns `422 INSUFFICIENT_MODEL_SKILLS`.
- The response ranks supported exact `lower(trim(title))` strings with a positive-evidence Bernoulli Naive Bayes model. Each prediction includes supporting training-record count, relative uncalibrated score, and per-input-skill evidence. Missing input skills are not treated as absent/negative evidence.
- The API loads `ml/models/role_title_nb_v1.json` in-process. Python is used for offline training only; no separate ML server is called.

The default artifact uses prior weight `2.5`. On a salted 1-in-25 sample of **1,259 supported held-out records**, Top-1 is **0.289118** versus **0.181096** for the prior-only baseline; Top-5 is **0.590151** versus **0.521048**. Only **47.2943%** of all held-out rows are covered by the 910 supported title classes. The sample, record-level split, uncalibrated score, and exact-title target are limitations; the model is explicitly `limited_scope_review_only_not_production_approved`, not a stable occupational classifier. See the [separate evaluation report](../../ml/evaluation/results/ROLE_TITLE_NAIVE_BAYES_EVALUATION.md).

### Models and ML status

`GET /api/v1/models/status` reports `productionModels: []` and distinguishes the served, limited-scope Naive Bayes title ranker from the deterministic Jaccard baseline. Jaccard is not ML. Python clustering remains exploratory/report-only and is not served. Salary regression, stable job-family classification, and active-listing prediction remain disabled by data-quality gates. All online inference runs in the single Node.js backend process.

## 6. Frontend Integration

No frontend entry point or framework is present in the current checkout. The following items are integration requirements for the planned client; they do not mean that API-to-UI wiring is complete.

- Use relative URLs such as `/api/v1/overview`; in local development configure the frontend dev server to proxy `/api` to the Node server. Do not put `localhost` calls in browser code for a deployed site.
- `/api/v1/matches` ranks aggregate exact-title role profiles and includes skill gaps; it does not score individual advertisements. `/api/v1/roles/{roleId}/ads` is a separate unscored ad list. Do not label this as per-ad matching until that feature is implemented and evaluated.
- Job-list items omit reviewed skill associations; `/api/v1/jobs/{recordId}` returns the eligible `reviewedSkills` for each record. The future UI should load and display those with the job detail view.
- The backend does not return a database path or connection details.
- Show `pagination` metadata, denominator/sample counts, source labels, null/missing values, and each endpoint's limitations.
- Distinguish validation errors from empty results. A 200 with an empty array is a legitimate no-match state; a 503 means the local data file is unavailable.
- Match requests are transient. Do not persist them in frontend storage or third-party analytics.
- Present Jaccard overlap and the Naive Bayes exact-title ranker as separate methods; do not label Jaccard as ML or the Naive Bayes relative score as a probability.
- Render descriptions and other source text with normal text escaping; do not use `innerHTML` for raw description values.
- Follow source and learning-resource links as external destinations and do not promise their continued availability.

## 7. Operational Limits

- Maximum JSON body: 32 KiB; maximum list page: 100; maximum match input: 50 skills; maximum match result limit: 25.
- API requests are read-only. No user accounts, saved searches, write endpoints, remote database, or model-service network call are implemented.
- Node's built-in SQLite interface is synchronous; expensive aggregate operations should be measured against the full local database before public multi-user deployment.
- A local SQLite deployment must be backed up and rebuilt/updated through the existing Python loader and migrations, not modified by the API.
- The API passes 16 Node fixture tests. In the last full-data run, selected endpoints were exercised over HTTP against the restored archive-backed SQLite file; the read-only check reported 775,155 jobs, 4,026,953 job-skill links, migrations 001–005, and zero foreign-key violations. Those ignored data files are absent from the current snapshot, so this result cannot be rerun until they are restored. Concurrent-load/performance testing, browser/UI integration, and an actual Vercel data bundle remain pending.
