# JOP Marketing Intelligence

A job-market intelligence platform designed to help engineers in Egypt and the wider Arab region explore opportunities across regional and international markets. The platform will analyze collected job advertisements, highlight in-demand skills, compare markets, and help users identify relevant roles and learning opportunities.

## Project Status

- The initial audit and reproducible staging pass are complete for the source files currently available in `data/raw/`. Data-preparation scripts and reviewed skill/learning-resource references are now included.
- Generated job files remain local and Git-ignored. The initial audit does not verify redistribution rights or prove that any listing is active.
- Analytics, database loading, model implementation, and the frontend/backend application have not been implemented. Current data field coverage is documented in the audit and dictionary.

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
- [Web application plan](docs/WEB_APP_PLAN.md)
- [Contribution guidelines](CONTRIBUTING.md)

## Data Principles

Every result must be presented as an analysis of the job advertisements available to the team, not as a complete representation of an entire labor market. Keep the International 2023 sample separate from the newest export snapshots and other uncertain snapshots. Show the sample size, source, and relevant dates wherever available; do not treat `updated` as a posting date or claim listings are active without verification. Missing salary or skill information must not be treated as zero or inferred without evidence, and research-derived salary ranges must not be presented as employer-offered pay.
