# Proposed Repository Structure

This structure separates analysis, database work, models, and the website. The repository currently contains documentation and planning scaffolding only; implementation files should be added after the dataset audit and technology choices.

- **`docs/`** — Project scope, task plan, data and database design, analytics, ML, web application, and workflow documentation; `docs/software-engineering/` contains requirements, architecture, API, UX, security, testing, operations, and governance specifications.
- **`data/`** — Readme, data dictionaries, and only small samples that are approved for sharing. Large raw or processed files remain outside Git.
- **`database/`** — ERD, schema definitions, Neon setup instructions, and data-loading decisions.
- **`analysis/`** — SQL analyses, exploratory analysis notebooks, charts, and analytical reports.
- **`ml/`** — Modeling data preparation, experiments, evaluation, and model interpretation.
- **`backend/`** — Services that access the database and provide secure data to the frontend.
- **`frontend/`** — Website pages, search and filters, charts, and English/Arabic user experience.
- **`tests/`** — Data-cleaning, relationship, query, model, and interface tests.
- **`.github/`** — Task and pull-request templates.

## Organization Rules

- Do not put all analysis into one notebook. Separate notebooks by analytical question and keep them reproducible.
- Do not commit Neon credentials, user data, or raw data files.
- Keep analytical SQL separate from database schema definitions when implementation begins.
- Do not publish chart values in the interface before documenting their source and metric definition.
- Select frontend and backend frameworks based on team familiarity and deployment needs; this plan does not mandate an unapproved stack.
