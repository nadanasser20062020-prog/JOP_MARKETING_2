# Software Requirements Specification (SRS)

**Product:** JOP Marketing Intelligence
**Document ID:** SRS-001
**Version:** 1.0 Draft
**Status:** For team review; data-dependent and technology-dependent details remain provisional.
**Audience:** Project team, reviewers, and implementation contributors.

## 1. Introduction

### 1.1 Purpose

This SRS defines the problem, objectives, scope, users, functional requirements, quality requirements, data rules, external interfaces, constraints, and acceptance conditions for JOP Marketing Intelligence. It is the baseline against which the project design and implementation should be reviewed.

### 1.2 Product Summary

JOP Marketing Intelligence is a bilingual web application for exploring the team's collected job advertisements. It is intended to help engineers in Egypt and the wider Arab region understand the roles, skills, locations, salaries, and work arrangements represented in the collected sample and identify roles related to their current skills.

The project also demonstrates a complete data-science workflow: data auditing and cleaning, relational database design and ERD, SQL analysis, Python analysis and visualizations, and evaluated clustering, classification, regression, and skill-matching experiments where the data supports them.

### 1.3 Document Conventions

- **Must:** required for the agreed initial release.
- **Should:** preferred if data and project capacity permit.
- **Conditional:** required only after the stated data-quality or feasibility gate passes.
- **Proposed:** recommended design pending approval by the project team.
- Missing or unavailable data must not be represented as zero or as an inferred fact.

### 1.4 References

- [Project Plan](../PROJECT_PLAN.md)
- [Feature Specification](../FEATURE_SPEC.md)
- [Use Cases and User Flows](USE_CASES.md)
- [Architecture](ARCHITECTURE.md)
- [Database Specification](DATABASE_SPECIFICATION.md)
- [SQLite Physical Schema](PHYSICAL_SCHEMA_PROPOSAL.md)
- [API Specification](API_SPECIFICATION.md)
- [Test Strategy](TEST_STRATEGY.md)
- [Diagram Pack](../diagrams/README.md)

## 2. Problem Statement and Objectives

### 2.1 Problem Statement

Job-market information is distributed across individual advertisements and can be difficult for engineers to compare consistently. Job titles, skill names, locations, work arrangements, and salary disclosures may use different formats, and advertisements may omit important fields. A person who knows their current skills may also find it difficult to identify relevant roles and the skill gaps that appear in those roles.

The project will organize and analyze the job advertisements already collected by the team, then present evidence-based market insights and explainable skill-to-job matches through a website. The product must describe the limits of its sample and must not imply that collected advertisements represent every opportunity in a market.

### 2.2 Project Objectives

1. Make the available job-advertisement sample searchable and understandable.
2. Show supported patterns in roles, skills, companies, countries, salaries, work arrangements, and dates.
3. Enable comparisons between markets using consistent definitions and visible sample sizes.
4. Let a visitor enter skills and see relevant roles or advertisements, matched skills, and evidence-based gaps.
5. Link skill gaps to reviewed learning resources with clearly stated access status.
6. Demonstrate relational database design, an ERD, SQL, Python analysis, visualizations, and appropriately evaluated machine-learning experiments.
7. Deliver a bilingual website with understandable methodology, source provenance, and limitations.

### 2.3 Success Criteria

The project is acceptable when:

- A visitor can complete the primary browse, compare, and skill-matching journeys described in this SRS.
- Displayed metrics can be traced to documented SQL queries or reproducible analysis.
- The database model and data dictionary correspond to the audited data and approved ERD.
- Skill matching explains its results and does not claim to estimate a person's probability of being hired.
- Any model exposed to users has passed a task-specific evaluation gate; otherwise it remains report-only.
- The application displays data coverage and limitations rather than inventing missing information.
- Critical English and Arabic flows, including RTL behavior, have been reviewed.
- Numeric coverage, performance, and model-quality thresholds are set after the data audit and before release testing; they must not be invented before measurement.

## 3. Scope

### 3.1 In Scope

- Data audit, data dictionary, cleaning and standardization, deduplication, and provenance.
- An implemented local SQLite schema and ERD, with ordered migrations and a Python loader for the complete checksum-verified archive or other complete local normalized files.
- SQL analyses and Python exploratory analysis using NumPy, Pandas, Matplotlib, and Seaborn.
- A market overview, job search and filtering, advertisement details, and source links where available.
- Skill-demand views, market comparison, supported trends, and skill co-occurrence.
- Explainable skill matching, skill-gap presentation, and curated learning resources.
- Experiments with clustering, classification, and salary regression subject to data and evaluation gates.
- English and Arabic website experiences, including RTL support.
- API, testing, security, deployment, and methodology documentation.

### 3.2 Out of Scope for the Initial Release

- Saving jobs or saved searches.
- New-job alerts or notifications.
- User accounts, candidate profiles, or persistent storage of submitted skills unless separately approved.
- Automated or continuous job scraping unless separately approved.
- Claims that the application provides a complete labor-market census, guarantees salary accuracy, or predicts hiring success.

### 3.3 System Boundary

The system includes data preparation, the relational database, analysis and evaluated model workflows, backend services, and the website. The original source files in shared storage, job-board websites, and external learning platforms are outside the system boundary. The project may link to those sources but does not control their availability or content.

## 4. Stakeholders and User Classes

| User class | Description | Primary needs |
|---|---|---|
| Engineer / job seeker | Visitor exploring job markets or entering skills | Search, compare, understand role requirements, discover learning resources |
| Project team member | Maintains data, taxonomy, analyses, models, and application | Reproducible workflows, data quality, traceable decisions, secure operations |
| Project reviewer | Evaluates the graduation project | Clear requirements, diagrams, methodology, results, and limitations |
| External job-source provider | Publishes an advertisement linked from the site | Accurate attribution and a valid outbound link where available |
| Learning-resource provider | Hosts an external educational resource | Accurate description and access-status attribution |

The initial release is public and read-oriented. No authenticated administrator or user account is required by the agreed scope.

## 5. Product Perspective and Architecture

### 5.1 Implemented Architecture Baseline

The selected style is a **layered three-tier web application**: presentation layer, a Node.js 22 API/application process, and a local SQLite data file opened read-only by the API. Data preparation, migrations/loading, and Python analysis remain separate reproducible workflows; the Node API does not invoke Python. This single-process design keeps service boundaries understandable and protects local-file access. A Vercel function adapter is configured, but full-data hosted deployment is conditional on packaging the ignored local SQLite file within platform limits.

### 5.2 Major System Components

- Data-preparation scripts read source files, validate and transform records, and produce separate processed outputs.
- A local SQLite file stores job/source provenance, skills, aliases, observations, job-skill links, and learning-resource records using the implemented schema.
- SQL and Python workflows produce analysis, charts, and evaluated model outputs.
- A backend API validates requests and serves data and approved application operations.
- A frontend provides the bilingual market-exploration and skill-matching experience.
- External job and learning providers are reached through outbound links; they are not application-controlled services.

See the [system context](../diagrams/01_SYSTEM_CONTEXT.md), [container architecture](../diagrams/02_CONTAINER_ARCHITECTURE.md), [component diagram](../diagrams/03_BACKEND_COMPONENTS.md), and [deployment diagram](../diagrams/12_DEPLOYMENT_VIEW.md).

## 6. Operating Environment and Technology Stack

The website targets current desktop and mobile browsers selected for the project demonstration. Data preparation, migrations/loading, and offline analysis run in Python. The implemented Node.js API opens the local SQLite file read-only; no external database service or connection URL is used. A Vercel function adapter is configured, but a full-data deployment requires a private/packageable SQLite file and has not been verified.

| Area | Status | Requirement or current direction |
|---|---|---|
| Data analysis | Required by course | Python, SQL, NumPy, Pandas, Matplotlib, and Seaborn |
| Data-loading utility | Implemented | Python loader writes to local SQLite with `sqlite3`; DuckDB reads the verified full Parquet archive locally; complete normalized files are also supported |
| Relational database | Resolved and implemented | Local SQLite file only; default `data/processed/job_market.sqlite3`; Node API access is read-only; no external database service or connection URL |
| Backend runtime | Implemented | Node.js `>=22.13 <23`, built-in `node:sqlite`, one process for HTTP, SQL analytics, and deterministic skill matching; no runtime npm dependencies |
| Frontend framework | TBD | Select after UX and team-capability review |
| Web charting library | TBD | Select after chart requirements and accessibility review |
| Hosting | Conditional | Local full-data demonstration is supported; Vercel function code is configured but requires the SQLite file to be included and fit platform limits |
| API format | Implemented | Versioned JSON HTTP API at `/api/v1`; exact contract in API Specification |

## 7. Assumptions, Dependencies, and Constraints

- The complete local SQLite dataset is loaded from the checksum-verified archive: 775,155 jobs and 4,026,953 job-skill links. Re-audit any changed source refresh before importing it or enabling dependent product features; the legacy small seed is reserved for tests only.
- The dataset consists of collected job advertisements and may contain duplicates, expired listings, inconsistent terms, missing values, and market-coverage bias.
- A feature may be enabled only when its required fields and sample size pass a documented gate.
- Salary comparisons require compatible currency and pay-period definitions. Salary regression requires enough disclosed, comparable salary records.
- Classification requires reliable labels or a reviewed labelled sample. Clustering does not require labels but requires human interpretation.
- Source terms, redistribution rights, attribution, and any personal information must be reviewed before public release.
- Original Drive data remains unchanged. Raw and processed data files must not be committed to GitHub.
- Skill-input retention is a proposed privacy decision under D-015 and must be confirmed before implementation.

## 8. Data Requirements and Business Rules

### 8.1 Candidate Data Entities

The implemented local model includes sources, source files, import runs, jobs, skills, aliases, job-skill associations, source-specific skill observations, learning resources, resource-skill links, and resource language labels. Company and location values remain on job rows rather than being normalized into separate tables. See the [logical ERD](../diagrams/04_LOGICAL_ERD.md) and [SQLite physical schema](PHYSICAL_SCHEMA_PROPOSAL.md).

### 8.2 Business Rules

- Keep source values and normalized values distinguishable where normalization is performed.
- A missing salary, skill, employer, location, date, or work arrangement is unavailable, not zero.
- Distinguish posting date from collection date.
- Count advertisements separately from unique employers, roles, and companies.
- A skill mention is not automatically a mandatory qualification; label required/preferred only when the source supports that interpretation.
- Show salary values with currency, pay period, sample size, and the distinction between advertised salary and model estimate.
- Do not compare salaries with incompatible units or time periods.
- Show market results as findings about the collected sample, not the entire labor market.
- Preserve provenance for source files, transformation steps, and published metrics.

## 9. Functional Requirements

Priority definitions are specified in Section 1.3. Requirements marked Conditional must pass their stated data-quality gate before being exposed to visitors. These are target-system requirements, not proof of completed UI behavior: the current checkout has no frontend entry point, the API supports aggregate role-profile matching but not individual-ad scoring, and browser/localization/accessibility acceptance remains pending.

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| FR-001 | The default landing page shall show archive-scope KPI cards, a Top 10 reviewed-skill chart, a country-label/count table, and an Arab-versus-other-represented-markets skill comparison restricted to `merged_tech_jobs`; a map is conditional on a reviewed country-to-geometry mapping. | Must | Functional test, metric-definition review, and reconciliation against source queries; do not imply global-market coverage |
| FR-002 | The system shall allow users to search job advertisements by supported text fields. | Must | Search tests |
| FR-003 | The system shall provide filters only for fields present and usable in the audited dataset. | Must | Filter tests against the data dictionary |
| FR-004 | The system shall show a detail view for each available job advertisement. | Must | Detail-page test |
| FR-005 | The detail view shall link to the original advertisement when a valid source URL exists. | Must | Link validation |
| FR-006 | The system shall show skill demand by role or market where the data supports the comparison. | Must | Query-to-UI reconciliation |
| FR-007 | The system shall allow comparison of selected markets using comparable metric definitions and visible sample sizes. | Should | Comparison test and review |
| FR-008 | The system shall show time trends only when dates are reliable and sufficiently covered. | Conditional | Data-quality gate and chart review |
| FR-009 | The system shall accept a temporary set of user-entered or selected skills for matching. | Must | Input-validation and flow test |
| FR-010 | The system shall rank relevant roles or advertisements and explain the basis of each result. | Must | Reviewed test cases |
| FR-011 | The system shall identify missing skills using evidence from relevant advertisements. | Must | Recommendation review |
| FR-012 | The system shall provide learning-resource links whose access status has been reviewed. | Must | Resource-catalogue audit |
| FR-013 | The user interface shall support English and Arabic, including right-to-left presentation for Arabic. | Must | Localization and RTL tests |
| FR-014 | The system shall explain data sources, definitions, methods, and limitations. | Must | Documentation review |
| FR-015 | The system shall distinguish salaries disclosed in advertisements from model-generated estimates. | Must | UI and API contract test |
| FR-016 | The system should process user-entered skill lists transiently and not persist them in the initial release, subject to team approval. | Proposed | Confirm D-015 and review storage/logging behavior |
| FR-017 | The system shall show clear loading, empty, unavailable-data, validation, and error states. | Must | UI state tests |
| FR-018 | The system may show skill co-occurrence or related-skill views when the data is sufficiently complete. | Conditional | Data-quality gate and analysis review |
| FR-019 | Data preparation shall read source files without modifying them and shall retain traceable source and transformation metadata. | Must | Pipeline review and provenance audit |
| FR-020 | Cleaning and normalization shall produce separate interim or processed outputs and shall not silently discard records or fabricate fields. | Must | Data-quality tests and before/after reconciliation |
| FR-021 | The database-loading process shall validate the input schema, record counts, keys, and relationships before reporting a successful load. | Must | Loader integration tests |
| FR-022 | SQL analyses and Python notebooks shall be reproducible and document their metric definitions, filters, data version, and limitations. | Must | Reproducibility and review checklist |
| FR-023 | The project shall evaluate clustering of job advertisements using supported skill or text features and document cluster interpretation. | Conditional | Clustering evaluation and human review |
| FR-024 | The project shall evaluate classification of job families only when reliable categories or reviewed labels are available. | Conditional | Per-class metrics and error analysis |
| FR-025 | The project shall evaluate salary regression only when disclosed salaries are sufficient and comparable. | Conditional | Baseline comparison and held-out evaluation |
| FR-026 | The system shall not expose model output that fails its task-specific quality gate. | Must | Model release review and UI/API test |
| FR-027 | The system shall identify unsupported filters, comparisons, or model outputs as unavailable rather than infer missing facts. | Must | Data-coverage tests and UI review |
| FR-028 | The backend shall provide documented, validated operations for website search, details, market metrics, skills, resources, and matching. | Must | API contract and integration tests |
| FR-029 | Selecting a normalized job title shall open a role-analysis view showing country counts/shares and skill demand overall and by country; related advertisements shall be a secondary option. | Must | Role-search flow and metric reconciliation tests |
| FR-030 | The system shall show arithmetic average salary by country only when disclosed salary values are comparable, accompanied by median, record count, currency, and pay period. | Conditional | Salary data-quality gate and country-level reconciliation |
| FR-031 | Analytical charts shall expose values and definitions on hover/tap and support click-to-filter where applicable, with keyboard-accessible alternatives. | Must | Interaction, keyboard, and chart-accessibility tests |

## 10. External Interface Requirements

### 10.1 User Interface

The user interface must support the pages and behavior in the [Feature Specification](../FEATURE_SPEC.md), [UX and accessibility requirements](UX_ACCESSIBILITY_I18N.md), and [low-fidelity wireframes](UI_UX_GUIDELINES_AND_WIREFRAMES.md). It must support keyboard use, responsive layouts, clear empty/error states, and English/Arabic directionality.

### 10.2 Software Interfaces

- The frontend communicates with the backend API over HTTPS in deployed environments.
- The backend communicates with the local SQLite file using parameterized queries; the database path and contents stay on the trusted backend host.
- Python scripts and analytics notebooks use the standard-library `sqlite3` module to open only a local file path; no network database configuration or credentials are used.
- Analytics notebooks retrieve approved results or suitable samples and must not expose private data.
- Exact request and response fields are defined in the [API Specification](API_SPECIFICATION.md) and finalized after the data audit.

### 10.3 External Services

The application may open original job-advertisement links and learning-resource URLs. It must identify these as external destinations and must not guarantee that the destination remains available.

### 10.4 Hardware Interfaces

No specialized hardware interface is required. Standard devices with a supported web browser are sufficient for the initial release.

## 11. Non-Functional Requirements

| ID | Requirement | Verification |
|---|---|---|
| NFR-001 | **Performance:** Common read operations should meet an agreed response-time target at the agreed demonstration data volume. An initial target of 2 seconds at the 95th percentile is proposed for review, not committed. | Load test after stack and data-volume decisions |
| NFR-002 | **Reliability:** Database or model failures must produce a clear recoverable message; the interface must not present stale or invented results as current. | Failure-injection and UI-state tests |
| NFR-003 | **Data integrity:** Displayed metrics must be traceable to documented queries or model outputs and must respect the data dictionary. | Reconciliation tests and review |
| NFR-004 | **Security:** The local SQLite file and path must remain server-side; inputs must be validated; database queries must be parameterized. | Security checklist and code review |
| NFR-005 | **Privacy:** Under the proposed D-015 baseline, user-entered skills are not retained and sensitive request contents are not logged. | Storage and logging review |
| NFR-006 | **Accessibility:** Target WCAG 2.2 Level AA for key user flows, subject to project capacity and verification. | Automated and manual accessibility review |
| NFR-007 | **Usability:** Search, filters, comparisons, and matching must have understandable labels and feedback. | User walkthroughs and acceptance tests |
| NFR-008 | **Localization:** English and Arabic content must preserve correct language direction, layout, numbers, and links. | Locale-specific testing |
| NFR-009 | **Maintainability:** Data rules, database changes, metric definitions, and model experiments must be documented and reproducible. | Repository and review checklist |
| NFR-010 | **Compatibility:** The application should work on current major desktop and mobile browsers selected for the demonstration. | Browser smoke tests |
| NFR-011 | **Observability:** Service health and failures must be diagnosable without logging user skill inputs or credentials. | Operational review |
| NFR-012 | **Data provenance:** Important results must identify sample size, source coverage, and relevant dates where available. | UI and report review |
| NFR-013 | **Recoverability:** Local SQLite migrations, data reloads, and application changes must have a documented local backup or rebuild procedure. | Migration, restore, and release-readiness tests |
| NFR-014 | **Portability:** Data transformations and analytical definitions should be reproducible outside a single developer's machine where feasible. | Re-run workflow in a clean environment |
| NFR-015 | **Legal and ethical use:** Source terms, attribution, privacy, and redistribution limits must be reviewed before public deployment. | Data-use approval checklist |
| NFR-016 | **Usability and visual density:** The Overview and role-analysis views should present a small number of clear visual sections, use progressive disclosure, and avoid requiring users to scan dense text or numbers. Every chart interaction must also work by touch and keyboard. | Responsive user walkthrough and accessibility review |

## 12. Data, API, and Database Design References

- **Logical model:** See [Database Specification](DATABASE_SPECIFICATION.md) and [Logical ERD](../diagrams/04_LOGICAL_ERD.md).
- **Physical model:** See [SQLite Physical Schema](PHYSICAL_SCHEMA_PROPOSAL.md) and the executable migration. The SQLite tables and integrity rules are implemented; newly added source fields must be re-audited and migrated explicitly.
- **Data flow:** See [DFD Level 0](../diagrams/16_DFD_LEVEL_0.md), [DFD Level 1](../diagrams/17_DFD_LEVEL_1.md), and [Data Pipeline](../diagrams/05_DATA_PIPELINE.md).
- **System behavior:** See [Use Cases](USE_CASES.md), [Job Search Sequence](../diagrams/19_JOB_SEARCH_SEQUENCE.md), [Skill Matching Sequence](../diagrams/09_SKILL_MATCHING_SEQUENCE.md), [Matching Request State](../diagrams/20_MATCH_REQUEST_STATE.md), and [Job Record State](../diagrams/21_DATA_RECORD_STATE.md).
- **External API contract:** See [API Specification](API_SPECIFICATION.md).

## 13. Verification and Acceptance

Each requirement must have a verification method. The [Traceability Matrix](TRACEABILITY_MATRIX.md) maps requirements to stories, project tasks, and planned tests. Acceptance requires:

- Every Must requirement has passing verification evidence or an explicitly approved exception.
- Conditional features pass their data-quality gates or are disabled and described as unsupported.
- SQL/Python results and website metrics reconcile for reviewed examples.
- Primary user journeys pass end-to-end review in both supported languages.
- Security, privacy, data-use, and release checklists have been reviewed.
- No unsupported model or salary estimate is exposed to visitors.

## 14. Open Decisions and Change Control

The following remain open and must be recorded in [Risks and Open Decisions](RISKS_AND_OPEN_DECISIONS.md) or an ADR: source refreshes and coverage, source-use permissions, frontend framework, chart library, numeric performance thresholds, salary-conversion policy, job-family labels, data refresh cadence, and full-data hosting feasibility. The Node.js backend runtime and local SQLite-only database are resolved. Jaccard matching is a deterministic, non-ML role-profile baseline; separately, a Node-served Naive Bayes model ranks exact observed titles for limited-scope review only. Individual-ad scoring, UI integration, and skill-input retention are out of scope or not implemented; submitted skills are transient in the current API.

Changes to scope or requirement wording must update this SRS, the relevant user stories/use cases, the traceability matrix, diagrams, and project tasks. No proposed design is considered implemented until verified against the running system.
