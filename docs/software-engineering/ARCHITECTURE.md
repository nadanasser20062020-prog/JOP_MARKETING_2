# System Architecture

**Status:** Node.js 22 HTTP API, read-only local SQLite access, versioned JSON contract, and Vercel function entry point are implemented. In the last full-data validation run, the ignored SQLite database passed checks with 775,155 jobs, 4,026,953 job-skill links, migrations 001–005, and zero foreign-key violations; selected routes also passed HTTP smoke tests. The archive and database are absent from the current snapshot and are not Git/deployment artifacts. There is no frontend entry point; browser flow, concurrent load, and actual Vercel bundle verification remain pending.

## Architecture Goals

- Keep SQLite file access on the trusted server-side process and never expose its path or connection to the browser.
- Reuse the normalized local relational dataset for analysis and website queries.
- Make metric denominators, sources, data quality, and limitations explicit.
- Keep matching temporary and explainable; clearly separate the non-ML Jaccard baseline from the limited-scope, uncalibrated title ranker, and do not imply production approval.
- Keep local operation simple while allowing the Node API code to run as a Vercel function when the data file is available to that deployment.

## Selected Architecture

A layered application with a single Node.js backend process:

1. **Presentation:** future bilingual web frontend.
2. **API/application:** Node.js 22 (`node:http` locally, catch-all function on Vercel), request validation, response envelopes, domain rules, SQL queries, deterministic Jaccard role-profile matching, in-process Naive Bayes exact-title inference, and safe error handling.
3. **Data:** local SQLite file at `data/processed/job_market.sqlite3`, opened read-only by the API. The JSON title-model artifact is loaded by Node.js. Python remains responsible for data cleaning, migrations/loading, offline analysis, and model training/evaluation; it is not called by the API.

No hosted database or separate ML service is used. There are no Node runtime npm dependencies; the built-in `node:sqlite` module is used. The frontend framework and chart library are not selected by this backend change.

## Components and Responsibilities

| Component | Responsibility | Must not do |
|---|---|---|
| Web frontend | Render pages, submit temporary filters/skills, display evidence and errors, support English/Arabic | Open SQLite, receive its filesystem path, store submitted skills unnecessarily |
| Node.js API | Validate requests, run parameterized read queries, paginate, return safe JSON/error envelopes, run the bundled title model in-process | Write to SQLite, log match bodies, expose SQL/path/stack details, imply unsupported facts |
| Query/domain layer | Apply approved policy/status pairs, compute cohort-specific counts/denominators, explain Jaccard and title-model evidence | Include unreviewed links, infer missing values, present Jaccard or a relative model score as hiring probability |
| Local SQLite | Preserve source records/provenance, skills, links, references, and resources | Use network connection strings or become browser-accessible |
| Python data workflow | Validate source files, apply migrations, load complete local archive, produce offline analysis/experiments | Run automatically inside a Node request or use a remote database |
| Vercel adapter | Reuse the Node handler if the database is bundled with the function | Reach a developer's local computer or write durable files to ephemeral storage |

## Data Flow

1. Approved source files/full archive are prepared locally; source files remain unchanged.
2. The Python loader verifies checksums, applies ordered SQLite migrations, loads the full local database, and validates keys/counts.
3. Node opens that local database read-only. All application SQL and matching execute in the same Node process.
4. The API returns records/aggregates with source context, denominators, snapshot identity, and limitations.
5. The frontend renders those responses and safely opens external URLs.

## Data and Model Rules

- Primary record unit is one retained source `record_id`; it is not guaranteed to be one unique vacancy.
- Skill demand, co-occurrence, and matching include only policy/status-consistent `(approved_aliases, curated)` and `(exact_only, curated_exact_only)` pairs in both link and catalog tables.
- Titles are matched by case/outer-whitespace normalization only; no inferred occupation taxonomy.
- Arab-versus-other market comparison is restricted to `merged_tech_jobs`; the second cohort is named “other represented markets”, not global market.
- Time trends use explicit `posted_at` dates only from the International 2023 sample.
- Salary comparisons/predictions, active listing status, stable job-family classification, and clustering inference remain unavailable.
- Jaccard skill overlap is a deterministic role-profile baseline, not a trained model, per-ad score, hiring probability, or overall suitability judgment.
- A separate positive-evidence Naive Bayes model ranks 910 supported exact observed title strings from 173 reviewed-skill features. It runs in Node.js but is limited-scope/review-only, uncalibrated, and not a production occupational classifier; held-out coverage is 47.2943%. See the [evaluation](../../ml/evaluation/results/ROLE_TITLE_NAIVE_BAYES_EVALUATION.md).

## Deployment Boundary

Local run is the verified full-data mode when the ignored SQLite file is restored. Vercel supports the Node handler and function routing, but its hosted runtime cannot see a developer's local SQLite file. The database must be explicitly included with the deployment artifact and fit provider packaging/runtime limits; no checked-in or prepared deployment bundle exists, and the local file is absent from the current snapshot. SQLite is treated as read-only in a function. If a full local database cannot fit the Vercel bundle, use local demonstration or a host with attached local storage—do not introduce a hosted database as an unapproved workaround.

## Failure Behavior

- Missing/uninitialized SQLite: `503 DATA_UNAVAILABLE`, no sample fallback.
- Valid no-result search: `200` and an empty collection.
- Invalid/unknown query fields: `400`; disabled salary/trend inputs: `422`.
- Unknown job/role/skill detail: `404`.
- Unexpected errors: generic `500`, diagnostics omit request body, SQL, path, and stack.
- Missing values remain null/unavailable, never zero or inferred.

## Related Decisions

- [ADR-0001: backend API boundary](adr/0001-backend-api-boundary.md)
- [ADR-0002: In-process Node.js online inference, offline Python training](adr/0002-in-process-ml-execution.md)
- [API contract](API_SPECIFICATION.md)
- [Deployment operations](DEPLOYMENT_OPERATIONS.md)
