# Repository Structure and Workflow-to-Folder Map

This repository separates project stages. A reproducible data-preparation pipeline and reviewed skill/learning-resource references now exist; generated data remains local and Git-ignored. There is still no running frontend, backend, database loader, or production application. Source-specific fields and limitations are documented in the completed first audit; re-audit any new source refresh.

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
| Database schema changes | `database/migrations/` | Ordered, reviewable database migration files when implementation begins |
| Python database-loading script | `scripts/database_loading/` | Python scripts that load validated processed data into PostgreSQL/Neon and verify counts and relationships |
| SQL analysis | `analysis/sql/` | Reproducible SQL queries for market and skills analysis |
| Python exploratory analysis | `analysis/notebooks/` | Jupyter notebooks using Pandas, NumPy, Matplotlib, and Seaborn |
| Charts and analysis reports | `analysis/reports/` | Reviewed visualizations, result summaries, and analytical limitations |
| Skill taxonomy and reference catalogues | `data/reference/` | Reviewed aliases, role mappings, and approved learning-resource metadata; only shareable reference data may be committed |
| Skill-matching work | `ml/skill_matching/` | Explainable matching baseline, input/output definitions, and evaluation cases |
| Clustering | `ml/clustering/` | Experiments that group job advertisements by skill or text similarity |
| Classification | `ml/classification/` | Label definitions, training experiments, evaluation, and error analysis |
| Salary regression | `ml/regression/` | Salary parsing assumptions, experiments, and evaluation; only if sufficient comparable salary data exists |
| Shared model evaluation | `ml/evaluation/` | Baselines, metrics, model cards, and review evidence for all model tasks |
| Backend API and services | `backend/api/` and `backend/services/` | API request handling, validation, search, analytics, matching, and database access |
| Website interface and design | `frontend/` and `frontend/design/` | Website pages and design specifications for English/Arabic and RTL flows |
| Unit, integration, data-quality, and end-to-end tests | `tests/` | Test suites grouped by validation level |
| Deployment and operations | `deployment/` | Environment, release, migration, rollback, and operating instructions specific to the chosen platform |

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
- Store connection credentials outside the repository.
- Keep original source data unchanged. Cleaning scripts should read raw input and write separate outputs.
- The initial data audit is complete; keep schema and loader decisions aligned with `docs/data/DATA_AUDIT.md` and `docs/data/DATA_DICTIONARY.md`, and re-audit any changed source files.
- No Python database loader exists yet. When added, it must read the processed dataset, use secure credentials, support safe repeat runs, and validate inserted record counts and relationships.
