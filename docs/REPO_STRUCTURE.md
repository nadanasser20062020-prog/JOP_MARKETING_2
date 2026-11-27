# Repository Structure and Workflow-to-Folder Map

This repository separates project stages. The reproducible data-preparation pipeline and reviewed skill/learning-resource references are documented. The local SQLite schema, archive-provenance migrations, full 775,155-job/4,026,953-link importer, and integrity checks are implemented; the frontend/backend application is still planned. Generated data remains local and Git-ignored. Re-audit any new source refresh.

## End-to-End Step-to-Folder Map

| Project step | Folder path | What belongs there |
|---|---|---|
| Project requirements, feature definitions, and planning | `docs/` and `docs/software-engineering/` | Project plan, requirements, user stories, acceptance criteria, architecture, security, testing, and operations documentation |
| System and data diagrams | `docs/diagrams/` | Mermaid ERD, architecture, DFD, workflow, sequence, deployment, and user-flow diagrams |
| Original collected data | `data/raw/` | Read-only raw CSV/ZIP copies if permitted. Contents are Git-ignored; do not edit original Drive files or commit raw data. |
| Data audit and data dictionary | `docs/data/` | Audit reports, data dictionary, dataset provenance, coverage, quality findings, and data-use restrictions |
| Temporary cleaning outputs | `data/interim/` | Local intermediate files produced during cleaning; contents are Git-ignored |
| Python data-cleaning scripts | `scripts/data_cleaning/` | Reproducible Python cleaning, normalization, and deduplication scripts |
| Final cleaned and normalized data | `data/processed/` | Local analysis-ready outputs; contents are Git-ignored and must not be committed as large datasets |
| Database model and ERD material | `database/erd/` and `docs/diagrams/` | Database design references and the version-controlled logical ERD |
| Database schema changes | `database/migrations/` | Ordered, reviewable SQLite migrations applied to the local database file |
| Python database-loading script | `scripts/database_loading/` | Local SQLite loader, migration runner, sample/staging imports, and relationship checks |
| SQL analysis | `analysis/sql/` | Reproducible SQL queries for market and skills analysis |
| Python exploratory analysis | `analysis/notebooks/` | Jupyter notebooks using Pandas, NumPy, Matplotlib, and Seaborn |
| Charts and analysis reports | `analysis/reports/` | Reviewed visualizations, result summaries, and analytical limitations |
| Skill taxonomy and reference catalogues | `data/reference/` | Reviewed aliases, role mappings, and approved learning-resource metadata; only shareable reference data may be committed |
| Skill-matching work | `ml/skill_matching/` | Explainable matching baseline, input/output definitions, and evaluation cases |
| Clustering | `ml/clustering/` | Experiments that group job advertisements by skill or text similarity |
| Classification | `ml/classification/` | Label definitions, training experiments, evaluation, and error analysis |
| Salary regression | `ml/regression/` | Salary parsing assumptions, experiments, and evaluation; only if sufficient comparable salary data exists |
| Shared model evaluation | `ml/evaluation/` | Baselines, metrics, model cards, and review evidence for all model tasks |
| Backend database helper, API, and services | `backend/database.py`, `backend/api/`, and `backend/services/` | Local SQLite path resolution and access; planned API request handling, validation, search, analytics, and matching |
| Website interface and design | `frontend/` and `frontend/design/` | Website pages and design specifications for English/Arabic and RTL flows |
| Unit, integration, data-quality, and end-to-end tests | `tests/` | Test suites grouped by validation level |
| Local operation and delivery | `deployment/` | Local SQLite setup, release, migration, backup, rollback, and recovery instructions; no hosted database configuration |

## Proposed Folder Tree

- `data/`
  - `raw/`
  - `interim/`
  - `processed/`
  - `reference/`
- `scripts/`
  - `data_cleaning/`
  - `database_loading/`
- `database/`
  - `erd/`
  - `migrations/`
  - `seeds/`
- `analysis/`
  - `sql/`
  - `notebooks/`
  - `reports/`
- `ml/`
  - `skill_matching/`
  - `clustering/`
  - `classification/`
  - `regression/`
  - `evaluation/`
- `backend/`
  - `api/`
  - `services/`
- `frontend/`
  - `design/`
- `tests/`
  - `unit/`
  - `integration/`
  - `data_quality/`
  - `e2e/`
- `deployment/`
- `docs/`
  - `data/`
  - `diagrams/`
  - `software-engineering/`

## Data and Security Rules

- `data/raw/`, `data/interim/`, and `data/processed/` are local working areas. Their data contents are excluded from Git; only the folder README files are tracked.
- Keep the generated SQLite file and any local backups out of Git; use `JOP_DATABASE_PATH` only as a local filesystem path, not a connection URL.
- Keep original source data unchanged. Cleaning scripts should read raw input and write separate outputs.
- The initial data audit is complete; keep schema and loader decisions aligned with `docs/data/DATA_AUDIT.md` and `docs/data/DATA_DICTIONARY.md`, and re-audit any changed source files.
- The Python database loader exists at `scripts/database_loading/load_to_database.py`; it uses local SQLite, records source fingerprints and import counts, is idempotent for unchanged inputs, requires explicit `--replace` for a different snapshot, and validates foreign keys.
