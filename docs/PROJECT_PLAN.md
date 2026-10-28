# Project Plan and Task Breakdown

This document is the central execution plan. Each task has a stable identifier that can be used in GitHub Issues. No owners or dates are assumed; the team should assign them after reviewing the dataset and agreeing on workload. The sequence reflects dependencies, not time estimates.

## Task Format

- **Objective:** Why the task is needed.
- **Approach:** How the team should complete it.
- **Deliverable and completion criteria:** What must be reviewable before the task is closed.

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
- **Approach:** Create the approved schema in PostgreSQL/Neon; load data in controlled stages; keep connection credentials in environment variables outside GitHub; validate record counts, relationships, and orphan records.
- **Deliverable and completion criteria:** A queryable database, repeatable loading instructions, and validation checks explaining any discrepancies.
- **Dependencies:** T03 and T04.

## Phase 2 — Analytics and Reporting

### T06 — Build SQL analyses
- **Objective:** Produce reproducible answers to job-market questions from the relational database.
- **Approach:** Create aggregations by country, role, company, skill, work arrangement, salary, and time where supported. Use medians and sample counts for salary reporting.
- **Deliverable and completion criteria:** Documented SQL analyses with a clear metric definition, filters, and sample size for each result.
- **Dependency:** T05.

### T07 — Conduct exploratory analysis in Python
- **Objective:** Understand data quality, distributions, and patterns before modeling.
- **Approach:** Use NumPy and Pandas for inspection, transformations, and analysis; use Matplotlib and Seaborn for charts. Connect to the database securely and retrieve suitable aggregates or samples instead of loading a large raw file into memory unnecessarily.
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
- **Approach:** Normalize user-entered skills, compare them with skills in job advertisements, rank the closest matches, and show matched and missing skills with reasons. Review results against team-created test cases.
- **Deliverable and completion criteria:** An explainable matching method. Its score is described as skill coverage, not as a probability of being hired.
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
- **Dependencies:** T01 and T03. Requires reliable labels or a reviewed labelled sample.

### T13 — Model salary estimates with regression
- **Objective:** Test whether salary can be estimated from job-advertisement attributes.
- **Approach:** Use only advertisements with disclosed salaries; standardize currency, pay period, and ranges under a documented policy; compare with a simple baseline; evaluate errors and check for data leakage.
- **Deliverable and completion criteria:** A model-quality report and usage limitations. The application must not display estimates when salary coverage or comparability is inadequate.
- **Dependencies:** T01, T03, and T05. Data sufficiency is a go/no-go condition.

## Phase 4 — Website and User Experience

### T14 — Implement the data-access and service layer
- **Objective:** Provide the user interface with secure access to data and analytics.
- **Approach:** Build a backend layer that connects to Neon and handles search, filtering, aggregation, and matching. Never expose database credentials in browser code.
- **Deliverable and completion criteria:** A documented service interface used by the frontend, with credentials kept outside the client.
- **Dependency:** T05. Technology details are decided by the team before implementation.

### T15 — Build job search and detail pages
- **Objective:** Help users find and understand individual job advertisements.
- **Approach:** Build searchable results and filters based on verified dataset fields; show the available posting details and source; clearly label missing information.
- **Deliverable and completion criteria:** Users can search, filter, open a posting, and follow its source link when available. Missing values are not invented.
- **Dependencies:** T05 and T14.

### T16 — Build the market dashboard, comparisons, trends, and skill map
- **Objective:** Present analytical findings visually and enable market comparison.
- **Approach:** Connect charts to documented queries; show sample sizes and time periods; suppress or qualify visuals that are not supported by the dataset.
- **Deliverable and completion criteria:** A market dashboard, market-comparison views, supported time trends, and a skill-relationship view where data coverage permits.
- **Dependencies:** T08 and T14.

### T17 — Build skill matching, learning resources, and bilingual interface
- **Objective:** Turn a user's skills into understandable recommendations and next steps.
- **Approach:** Accept user-entered skills and optional market preferences; show ranked matches with explanations; display gaps and learning links; support English and Arabic, including correct RTL layout.
- **Deliverable and completion criteria:** Users can enter skills, understand why results were recommended, open a relevant job or learning resource, and switch languages.
- **Dependencies:** T09, T10, and T14.

## Phase 5 — Quality and Delivery

### T18 — Test integration, data quality, and security
- **Objective:** Verify the accuracy of displayed results and the safety and usability of the application.
- **Approach:** Test data rules, relationships, queries, models, and interfaces; check empty and unknown values; review RTL and keyboard accessibility; inspect credentials and links.
- **Deliverable and completion criteria:** A test checklist with critical issues resolved and sampled UI figures reconciled against source queries.
- **Dependencies:** T14–T17.

### T19 — Deploy and prepare the final presentation
- **Objective:** Deliver a usable demonstration and explain the methodology and findings.
- **Approach:** Prepare operating and deployment instructions, use safe demonstration data if needed, document technology choices, model metrics, and limitations, and rehearse a user-focused walkthrough.
- **Deliverable and completion criteria:** A working demonstration environment, operating documentation, and a presentation covering the problem, dataset, analysis, models, product, and limitations.
- **Dependency:** T18.

## Dependency Summary

- T01 → T02 → T03 → T04/T05 → T06/T07 → T08.
- T03 and T09 → T10; T10 can then be integrated into T17.
- T03 and T05 → T11/T12/T13, subject to data-quality gates.
- T05 → T14 → T15/T16/T17 → T18 → T19.

## Decision Gates

1. Do not finalize the database schema before inspecting the actual columns and duplicates.
2. Do not display salary estimates unless there are enough comparable disclosed salaries.
3. Do not claim classification quality without reviewed labels and separate evaluation.
4. If dates, country, or work-mode fields are unavailable or unreliable, show only supported results and document the gap instead of guessing.
