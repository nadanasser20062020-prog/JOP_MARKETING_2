# Project Plan and Task Breakdown

This document is the central execution plan. Each task has a stable identifier that can be used in GitHub Issues. No owners or dates are assumed; the team should assign them after reviewing the dataset and agreeing on workload. The sequence reflects dependencies, not time estimates.

## Task Format

- **Objective:** Why the task is needed.
- **Approach:** How the team should complete it.
- **Deliverable and completion criteria:** What must be reviewable before the task is closed.

## Current Verified State

The following describes this workspace only; ignored archive/database files are not committed and must be restored locally from the approved archive in a fresh checkout. The source files in Google Drive were not edited, no hosted database was introduced, and application requests use Node.js only.

| Area | Current state | What remains / caveat |
|---|---|---|
| Collection and scope | Seven source datasets are retained in a checksum-verified archive; source dates, listing activity, and exact duplicates are documented. | The archive is a collected sample, not the full labor market; redistribution permissions are not assessed. |
| Cleaning and data model | Reproducible staging rules, 12 related Parquet tables, SQLite schema, migrations 001–005, loader and rollups exist. | Fresh checkouts need the ignored Parquet archive restored before loading. |
| Local database | In the last full-data run, `data/processed/job_market.sqlite3` held 775,155 jobs and 4,026,953 skill links; `check` reported migrations 001–005 and zero FK violations. | The ignored SQLite file and Parquet archive are absent from the current snapshot and must be restored before repeating full-data validation; no external DB. |
| Analysis | 19 SQL queries generate a report, aggregate CSVs and charts; role×country, role skills, role-country skills, and salary comparability are included. | Salary means/medians are not defensible; some notebooks and UI-specific visualizations are still planned. |
| ML | Node.js serves deterministic Jaccard matching separately from a trained Naive Bayes exact-title ranker; Python trains offline. The latter improved sampled held-out Top-1/Top-5 over prior-only but remains review-only. | Not a stable job-family classifier; 47.2943% test coverage; no salary/activity prediction; clustering remains report-only. |
| Backend | Read-only Node.js SQLite API and Vercel-compatible route exist; API schemas and limitations are documented. | Vercel deployment and concurrent load testing are not verified. |
| Frontend | User journeys and wireframes describe overview, role analysis, ads, matching, learning resources, and Arabic/RTL. | No frontend entry point was found in this checkout; end-user UI integration is not complete. |
| Tests | Python/Node fixture tests and full-database loader/API smoke checks are run during implementation. | Automated UI, accessibility, browser, deployment, and load tests are not present. |

## Phase 0 — Dataset Discovery and Scope Definition

### T01 — Inventory and audit the dataset
- **Objective:** Understand the actual files and fields before finalizing the data model or selecting machine-learning tasks.
- **Approach:** Inventory file formats, encodings, and sizes; inspect headers and representative records; document record counts, languages, dates, countries, missing values, duplicates, and job-ad sources. Treat the source files as read-only and do not modify the originals in Drive.
- **Deliverable and completion criteria:** A Data Audit report describing the files, fields, data quality, and feasible analyses. Large raw data files are not committed to GitHub.
- **Priority/dependency:** First task; no prior task required.

### T02 — Create the data dictionary and confirm feature feasibility
- **Objective:** Map each proposed feature to fields that actually exist in the dataset.
- **Approach:** Define each field, unit, and source; establish canonical values and naming conventions; identify features that require salary, date, work-mode, or other fields.
- **Deliverable and completion criteria:** A Data Dictionary and a feature-feasibility matrix marking each requirement as available, requiring cleaning, or unavailable. Confirm the project scope using the T01 findings.
- **Dependency:** T01.

## Phase 1 — Data Preparation and Database Design

### T03 — Clean and standardize the data
- **Objective:** Create analysis-ready data without changing the original source files.
- **Approach:** Standardize column names and values; detect duplicate job advertisements; normalize role titles, skills, countries, and work arrangements; retain original values where needed. Do not fabricate missing information.
- **Deliverable and completion criteria:** Documented, reproducible cleaning rules and a structured dataset, with a before-and-after comparison explaining changes.
- **Dependencies:** T01 and T02.

### T04 — Design the relational model and ERD
- **Objective:** Organize the collected data into a relational structure suitable for analysis and application use.
- **Approach:** Define entities, relationships, keys, and optional fields after reviewing the actual columns. Represent the many-to-many relationship between jobs and skills with a junction table. Draw and review the ERD with the team.
- **Deliverable and completion criteria:** An approved ERD and data dictionary showing relationships, keys, and nullable fields.
- **Dependencies:** T01 and T02.

### T05 — Build the database, load data, and validate it
- **Objective:** Make cleaned data available for queries and the application.
- **Approach:** Apply ordered SQLite migrations to the local file; load the complete checksum-verified Parquet archive (775,155 jobs and 4,026,953 job-skill links); verify source provenance, table counts, and foreign-key relationships. Automatic loading must fail rather than accept incomplete data. The database and archive remain under the existing ignored `data/processed/` path; no external database service is used.
- **Deliverable and completion criteria:** A rebuildable full-data SQLite database, repeatable full-archive loading instructions, archive import-run provenance, and integrity checks. Schema, loader, and full archive validation are implemented.
- **Dependencies:** T03 and T04.

## Phase 2 — Analytics and Reporting

### T06 — Build SQL analyses
- **Objective:** Produce reproducible answers to job-market questions from the relational database.
- **Approach:** Create aggregations by country, role, company, skill, work arrangement, salary, and time where supported. Use medians and sample counts for salary reporting.
- **Deliverable and completion criteria:** Documented SQL analyses with a clear metric definition, filters, and sample size for each result.
- **Dependency:** T05.

### T07 — Conduct exploratory analysis in Python
- **Objective:** Understand data quality, distributions, and patterns before modeling.
- **Approach:** Use NumPy and Pandas for inspection, transformations, and analysis; use Matplotlib and Seaborn for charts. Query the local SQLite file through Python and retrieve suitable aggregates or samples instead of loading a large raw file into memory unnecessarily.
- **Deliverable and completion criteria:** Organized, reproducible notebooks that explain the questions, transformations, results, and limitations.
- **Dependency:** T05.

### T08 — Produce charts and an analytical report
- **Objective:** Turn analytical findings into a clear narrative for users and reviewers.
- **Approach:** Select an appropriate chart for each question; show units, time period, source, and sample size; compare SQL and Python results where useful.
- **Deliverable and completion criteria:** A set of reviewed charts, an initial dashboard, and a report describing findings and what the data cannot establish.
- **Dependencies:** T06 and T07.

## Phase 3 — Skills and Machine Learning

### T09 — Build a skill taxonomy and learning-resource catalogue
- **Objective:** Normalize skills for matching and connect skill gaps to useful learning resources.
- **Approach:** Map aliases and spelling variants to canonical skill names while retaining original text. Review learning resources and record the skill, language, URL, free-access status, and verification date.
- **Deliverable and completion criteria:** A reviewable skill taxonomy and resource catalogue. Resources must not be labelled free unless that status has been checked.
- **Dependencies:** T01 and T03.

### T10 — Implement an explainable skill-matching baseline
- **Objective:** Recommend relevant jobs or role profiles before introducing more complex models.
- **Approach:** Normalize user-entered skills, compare them with reviewed skill profiles, rank the closest matches, and show matched and missing skills with reasons. Review results against team-created test cases.
- **Current implementation:** `POST /api/v1/matches` ranks aggregate exact-title role profiles with deterministic Jaccard and returns matched, missing, user-only skills, and evidence counts. It does not score individual advertisements; the separate related-ad route has no per-ad score. Do not retry the previously slow full-table matching approach; per-ad ranking needs an indexed/capped design and measured performance.
- **Deliverable and completion criteria:** The role-profile baseline is implemented and covered by Node/Python tests. No reviewed relevance labels exist, so ranking usefulness is not established. Its score is described as skill overlap, not a probability of being hired.
- **Dependencies:** T03 and T09.

### T11 — Cluster job advertisements
- **Objective:** Discover groups of advertisements with similar skill profiles.
- **Approach:** Build an appropriate representation of skills or job text, test a limited set of clustering approaches, assess quality, and manually review representative examples and top skills in each cluster.
- **Deliverable and completion criteria:** A report describing clusters, representative examples, and limitations. Cluster names are not treated as authoritative job categories until reviewed.
- **Dependencies:** T03, T05, and T09. Dataset size and quality are a go/no-go condition.

### T12 — Classify job families
- **Objective:** Test whether job advertisements can be assigned to useful categories such as Data, Backend, or Frontend.
- **Approach:** Define categories, prepare and review a labelled sample, train a simple text-classification baseline using titles and descriptions when available, and inspect errors.
- **Deliverable and completion criteria:** A report with per-class metrics, error examples, and a conclusion about whether the model is reliable enough to use—or why the data does not support a trustworthy model.
- **Current decision:** Stable job-family classification remains no-go because no reviewed taxonomy or labeled set exists. A separate Naive Bayes model ranks exact observed title strings from reviewed skills; it is served only for limited-scope review and is not an occupational classifier. See [`ROLE_TITLE_NAIVE_BAYES_EVALUATION.md`](../ml/evaluation/results/ROLE_TITLE_NAIVE_BAYES_EVALUATION.md).
- **Dependencies:** T01 and T03. Requires reliable labels or a reviewed labelled sample.

### T13 — Model salary estimates with regression
- **Objective:** Test whether salary can be estimated from job-advertisement attributes.
- **Approach:** Use only advertisements with disclosed salaries; standardize currency, pay period, and ranges under a documented policy; compare with a simple baseline; evaluate errors and check for data leakage.
- **Deliverable and completion criteria:** A model-quality report and usage limitations. The application must not display estimates when salary coverage or comparability is inadequate.
- **Dependencies:** T01, T03, and T05. Data sufficiency is a go/no-go condition.

## Phase 4 — Website and User Experience

### T14 — Implement the data-access and service layer
- **Objective:** Provide the user interface with secure access to data and analytics.
- **Approach:** The implemented Node.js 22 API opens the configured local SQLite file read-only and handles search, filtering, aggregation, resources, Jaccard matching, and in-process Naive Bayes title ranking. Keep database access in trusted server-side code; the browser has no direct SQLite access. Do not add a network database fallback or separate ML service.
- **Deliverable and completion criteria:** A documented `/api/v1` service interface, fixture tests, and full-local-database smoke checks; the SQLite path and database access remain server-side. Frontend use is still pending.
- **Dependency:** T05. Backend runtime and API contract are implemented.

### T15 — Build role analysis and related advertisement pages
- **Objective:** Help users understand a selected job role across countries, skills, and comparable salaries; individual advertisements are secondary.
- **Approach:** Make normalized role search open a role-analysis page. Show country counts and shares, skill demand overall and by country, and average salary by country only when disclosed values are comparable; include denominators, sample counts, currency, and pay period. Add a secondary link or tab to related advertisements and retain a separate filtered explorer and detail view.
- **Deliverable and completion criteria:** Users can search a role and first see its market analysis, then optionally open related advertisements. Missing or incomparable values are not invented or combined.
- **Dependencies:** T05 and T14.

### T16 — Build the Overview dashboard, comparisons, trends, and skill visualizations
- **Objective:** Make the default page a simple, interactive overview of the collected job market.
- **Approach:** Connect documented queries to a country distribution/table (a map only after a reviewed name-to-geometry mapping), KPI cards for job records/distinct eligible skills/represented countries, a Top 10 reviewed-skill chart, and an Arab-versus-other-represented-markets comparison within `merged_tech_jobs`. Add hover/tap details and cross-filtering only where implemented; show sample sizes and metric definitions. Add supported market comparisons, historical counts, and skill relationships. The comparison is not global and the frontend is not built.
- **Deliverable and completion criteria:** The default Overview contains the four agreed visual sections; selecting a country or chart value filters related views; all metrics reconcile to documented queries and show only supported comparisons.
- **Dependencies:** T08 and T14.

### T17 — Build skill matching, learning resources, and bilingual interface
- **Objective:** Turn a user's skills into understandable recommendations and next steps.
- **Approach:** Accept user-entered skills and optional market preferences; show the current role-profile Jaccard results with matched/missing skills and evidence; keep the separate Naive Bayes exact-title suggestion clearly experimental; display learning links; support English and Arabic, including correct RTL layout.
- **Current status:** No frontend entry point is present. The API does not rank individual job advertisements by match score; exposing related ads is possible through role ads but individual-ad ordering remains an open feature.
- **Deliverable and completion criteria:** Future users can enter skills, understand the role-profile evidence, open a related job or learning resource, and switch languages. UI, per-ad match scoring, accessibility, and RTL need implementation and tests.
- **Dependencies:** T09, T10, and T14.

## Phase 5 — Quality and Delivery

### T18 — Test integration, data quality, and security
- **Objective:** Verify the accuracy of displayed results and the safety and usability of the application.
- **Approach:** Test data rules, relationships, queries, models, and interfaces; check empty and unknown values; review RTL and keyboard accessibility; inspect local database-file access and external links.
- **Deliverable and completion criteria:** A test checklist with critical issues resolved and sampled UI figures reconciled against source queries.
- **Dependencies:** T14–T17.

### T19 — Deploy and prepare the final presentation
- **Objective:** Deliver a usable demonstration and explain the methodology and findings.
- **Approach:** Prepare local operating and recovery instructions, rebuild the demonstration SQLite file from the complete verified archive or another approved complete local input set, document technology choices, model metrics, and limitations, and rehearse a user-focused walkthrough. Do not use the test fixture or depend on a hosted database.
- **Deliverable and completion criteria:** A working local demonstration environment, operating documentation, and a presentation covering the problem, dataset, analysis, models, product, and limitations.
- **Dependency:** T18.

## Dependency Summary

- T01 → T02 → T03 → T04/T05 → T06/T07 → T08.
- T03 and T09 → T10; T10 can then be integrated into T17.
- T03 and T05 → T11/T12/T13, subject to data-quality gates.
- T05 → T14 → T15/T16/T17 → T18 → T19.

## Decision Gates

1. The current local schema is based on the audited fields; re-audit new/changed inputs before adding or altering database fields.
2. Do not display salary estimates unless there are enough comparable disclosed salaries.
3. Do not claim classification quality without reviewed labels and separate evaluation.
4. If dates, country, or work-mode fields are unavailable or unreliable, show only supported results and document the gap instead of guessing.
