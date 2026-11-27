# JOP Marketing Intelligence

A job-market intelligence platform designed to help engineers in Egypt and the wider Arab region explore opportunities across regional and international markets. The platform will analyze collected job advertisements, highlight in-demand skills, compare markets, and help users identify relevant roles and learning opportunities.

## Project Status

- The initial audit and reproducible staging pass are complete for the source files currently available in `data/raw/`. Data-preparation scripts and reviewed skill/learning-resource references are now included.
- Generated job files remain local and Git-ignored. The initial audit does not verify redistribution rights or prove that any listing is active.
- The local SQLite schema, ordered migrations, full-archive loader, and integrity checks are implemented. The verified archive contains 775,155 job records and 4,026,953 stored job-skill assignments; 3,701,019 reviewed links across 173 skills and 664,989 records passed the eligibility gate in the full-data run. The archive and SQLite file are Git-ignored; they were present for the last full-data validation but are absent from the current snapshot and must be restored before repeating full-data operation.
- A Node.js 22 API serves the local SQLite file read-only, with metadata, overview analytics, job/role search and analysis, market comparison, the historical-only trend series, skills/resources, and temporary Jaccard matching. Separately, it loads a trained Naive Bayes exact-title ranker in-process for limited-scope review; it is not a production occupational classifier. Python is used for offline training/evaluation only, while clustering remains report-only. The 16 Node API fixture tests, 26 Python tests, 6 matching-baseline tests, syntax checks, full database validation, and selected full-data HTTP smoke checks passed in the last validation run. See `docs/software-engineering/API_SPECIFICATION.md` and `ml/evaluation/results/ROLE_TITLE_NAIVE_BAYES_EVALUATION.md`.
- The backend and API contract are implemented, but this checkout contains no frontend entry point or framework. The user journeys and wireframes document the intended client; API-to-UI integration, browser, accessibility, and RTL checks remain pending.

## Local SQLite Quick Start

Place the verified `full_archive_parquet_v1_20261028` package in `data/processed/full_archive_parquet_v1_20261028/`, then run from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r scripts/database_loading/requirements.txt
python scripts/database_loading/load_to_database.py load --source archive
python scripts/database_loading/load_to_database.py check
```

The local database is `data/processed/job_market.sqlite3`, covered by the existing ignore rule. Automatic loading prefers the complete, checksum-verified Parquet archive and never falls back to a sample; without a full archive or complete normalized files, it stops with an error. Add `--replace` only when intentionally rebuilding an existing database. SQLite is the only configured database engine; no external database service is used.

## Node.js API Quick Start

Use Node.js 22.13 or newer in the 22.x line after the local SQLite file has been restored:

```bash
npm test
npm start
curl http://localhost:3000/health
curl http://localhost:3000/api/v1/metadata
```

The API opens SQLite read-only. `APP_URL` is configured separately in `backend/config/app_url.js`; `JOP_DATABASE_PATH` can point to another local file. Vercel can run the same handler only if the SQLite file is available in the deployment bundle; it cannot read a file from a developer's device. See the [API contract](docs/software-engineering/API_SPECIFICATION.md) and [deployment notes](docs/software-engineering/DEPLOYMENT_OPERATIONS.md).

## Agreed Scope

- A market overview dashboard and searchable, filterable job listings with detail pages and source links.
- Analysis of roles, skills, companies, salaries, work arrangements, and market coverage where the dataset supports it.
- Market comparisons, time-based trends where reliable dates are available, and exploration of relationships between skills and roles.
- Explainable skill-based role and job recommendations, including matched and missing skills.
- Curated, skill-linked learning resources for identified skill gaps; only `free_verified` items may be presented as free, with mixed or unverified costs clearly disclosed.
- English and Arabic user interfaces, including correct right-to-left support and normalized skill and role names.
- SQL and Python analysis, a relational data model and ERD, and experiments with clustering, classification, and regression when the data is suitable.

### Out of Scope for the Current Version

- Saving jobs or searches.
- Notifications or alerts for newly available jobs.

## Documentation

- [All project documentation](docs/README.md)
- [Software engineering documentation](docs/software-engineering/README.md)
- [Project diagram pack](docs/diagrams/README.md)
- [Project plan and task breakdown](docs/PROJECT_PLAN.md)
- [Feature specification](docs/FEATURE_SPEC.md)
- [Data and database plan](docs/DATA_AND_DATABASE.md)
- [Data audit](docs/data/DATA_AUDIT.md)
- [Data dictionary](docs/data/DATA_DICTIONARY.md)
- [Analytics plan](docs/ANALYTICS_PLAN.md)
- [Machine learning plan](docs/ML_PLAN.md)
- [Pre-backend analysis report](analysis/reports/pre_backend/PRE_BACKEND_ANALYSIS.md)
- [Pre-backend readiness and acceptance criteria](docs/software-engineering/PRE_BACKEND_READINESS.md)
- [Feature-to-data field mapping](docs/software-engineering/FEATURE_DATA_FIELD_MAPPING.md)
- [Arabic graduation defense guide](docs/software-engineering/PROJECT_DEFENSE_GUIDE_AR.md)
- [Metrics and model method](docs/software-engineering/METRICS_AND_MODEL_METHOD.md)
- [Skill-profile clustering evaluation](ml/evaluation/results/SKILL_PROFILE_CLUSTERING_EVALUATION.md)
- [Web application plan](docs/WEB_APP_PLAN.md)
- [Contribution guidelines](CONTRIBUTING.md)

## Data Principles

Every result must be presented as an analysis of the job advertisements available to the team, not as a complete representation of an entire labor market. Keep the International 2023 sample separate from the newest export snapshots and other uncertain snapshots. Show the sample size, source, and relevant dates wherever available; do not treat `updated` as a posting date or claim listings are active without verification. Missing salary or skill information must not be treated as zero or inferred without evidence, and research-derived salary ranges must not be presented as employer-offered pay.
