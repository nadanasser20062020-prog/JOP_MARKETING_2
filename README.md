# JOP Marketing Intelligence

A job-market intelligence platform designed to help engineers in Egypt and the wider Arab region explore opportunities across regional and international markets. The platform will analyze collected job advertisements, highlight in-demand skills, compare markets, and help users identify relevant roles and learning opportunities.

## Project Status

- The team has collected job-market data; data auditing, cleaning, analysis, modeling, and application development have not started.
- This repository currently contains the project plan and documentation structure. No application or model implementation code has been added.
- The actual dataset schema and field coverage have not yet been verified. Features that depend on specific fields remain subject to the initial data audit.

## Agreed Scope

- A market overview dashboard and searchable, filterable job listings with detailed posting pages and source links.
- Analysis of roles, skills, companies, salaries, work arrangements, and market coverage where the dataset supports it.
- Market comparisons, time-based trends where reliable dates are available, and exploration of relationships between skills and roles.
- Skill-based role and job recommendations, with clear explanations of matched and missing skills.
- Curated links to verified free learning resources for identified skill gaps.
- Arabic and English user interfaces, including correct right-to-left support and normalized skill and role names.
- SQL and Python analysis, a relational data model and ERD, and experiments with clustering, classification, and regression when the data is suitable.

### Out of Scope for the Current Version

- Saving jobs or searches.
- Notifications or alerts for newly available jobs.

## Project Documentation

1. [Project plan and task breakdown](docs/PROJECT_PLAN.md)
2. [Feature specification](docs/FEATURE_SPEC.md)
3. [Data, database, and ERD plan](docs/DATA_AND_DATABASE.md)
4. [SQL and Python analytics plan](docs/ANALYTICS_PLAN.md)
5. [Machine learning plan](docs/ML_PLAN.md)
6. [Web application plan](docs/WEB_APP_PLAN.md)
7. [Repository structure](docs/REPO_STRUCTURE.md)
8. [GitHub workflow](docs/GITHUB_WORKFLOW.md)

## Data Principles

Every result must be presented as an analysis of the job advertisements available to the team, not as a complete representation of an entire labor market. Show the sample size, source, and relevant dates wherever available. Missing salary or skill information must not be treated as zero or inferred without evidence.
