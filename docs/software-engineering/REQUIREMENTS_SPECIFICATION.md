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
- [Proposed PostgreSQL Physical Schema](PHYSICAL_SCHEMA_PROPOSAL.md)
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
- A relational schema and ERD, with a Python data-loading process for a PostgreSQL-compatible database selected by the team.
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

### 5.1 Proposed Architecture Style

The proposed style is a **layered three-tier web application**: presentation layer, backend/API and application services, and relational data layer. Data preparation and analysis remain separate, reproducible workflows. This is preferred over a microservices design for the current project scale because it keeps service boundaries understandable while protecting database access. Final approval is recorded through an Architecture Decision Record before implementation.

### 5.2 Major System Components

- Data-preparation scripts read source files, validate and transform records, and produce separate processed outputs.
- A relational database stores approved job, source, company, location, skill, and learning-resource records.
- SQL and Python workflows produce analysis, charts, and evaluated model outputs.
- A backend API validates requests and serves data and approved application operations.
- A frontend provides the bilingual market-exploration and skill-matching experience.
- External job and learning providers are reached through outbound links; they are not application-controlled services.

See the [system context](../diagrams/01_SYSTEM_CONTEXT.md), [container architecture](../diagrams/02_CONTAINER_ARCHITECTURE.md), [component diagram](../diagrams/03_BACKEND_COMPONENTS.md), and [deployment diagram](../diagrams/12_DEPLOYMENT_VIEW.md).

## 6. Operating Environment and Technology Stack

The website is intended to run in current desktop and mobile browsers selected for the project demonstration. Data preparation and analysis run in a Python environment. The production hosting provider and exact application frameworks have not been selected.

| Area | Status | Requirement or current direction |
|---|---|---|
| Data analysis | Required by course | Python, SQL, NumPy, Pandas, Matplotlib, and Seaborn |
| Data-loading utility | Planned | Python script; exact database driver and packaging are TBD |
| Relational database | Proposed | PostgreSQL-compatible database; Neon is under consideration, not yet a final decision |
| Backend framework | TBD | Select based on team experience, security, API needs, and hosting support |
| Frontend framework | TBD | Select after UX and team-capability review |
| Web charting library | TBD | Select after chart requirements and accessibility review |
| Deployment provider | TBD | Define after hosting, cost, and demonstration requirements are reviewed |
| API format | Proposed | Versioned HTTP API as described in the API Specification |

## 7. Assumptions, Dependencies, and Constraints

- The team reports that data collection is the only completed project activity. Dataset fields and quality must be confirmed in T01.
- The dataset consists of collected job advertisements and may contain duplicates, expired listings, inconsistent terms, missing values, and market-coverage bias.
- A feature may be enabled only when its required fields and sample size pass a documented gate.
- Salary comparisons require compatible currency and pay-period definitions. Salary regression requires enough disclosed, comparable salary records.
- Classification requires reliable labels or a reviewed labelled sample. Clustering does not require labels but requires human interpretation.
- Source terms, redistribution rights, attribution, and any personal information must be reviewed before public release.
- Original Drive data remains unchanged. Raw and processed data files must not be committed to GitHub.
- Skill-input retention is a proposed privacy decision under D-015 and must be confirmed before implementation.

## 8. Data Requirements and Business Rules

### 8.1 Candidate Data Entities

The logical model contains candidate entities for job posts, companies, locations, sources, skills, job-skill associations, and learning resources. The actual entities and attributes must be validated against the data audit. See the [logical ERD](../diagrams/04_LOGICAL_ERD.md) and [physical schema proposal](PHYSICAL_SCHEMA_PROPOSAL.md).

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

Priority definitions are specified in Section 1.3. Requirements marked Conditional must pass their stated data-quality gate before being exposed to visitors.

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| FR-001 | The system shall show a market overview based on the available advertisement sample, including sample size and covered markets where known. | Must | Functional test and metric reconciliation |
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

## 10. External Interface Requirements

### 10.1 User Interface

The user interface must support the pages and behavior in the [Feature Specification](../FEATURE_SPEC.md), [UX and accessibility requirements](UX_ACCESSIBILITY_I18N.md), and [low-fidelity wireframes](UI_UX_GUIDELINES_AND_WIREFRAMES.md). It must support keyboard use, responsive layouts, clear empty/error states, and English/Arabic directionality.

### 10.2 Software Interfaces

- The frontend communicates with the backend API over HTTPS in deployed environments.
- The backend communicates with the relational database using server-side credentials and parameterized queries.
- Python scripts communicate with the selected database through a reviewed driver and secured environment configuration.
- Analytics notebooks query approved database views or result sets and must not contain credentials.
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
| NFR-004 | **Security:** Credentials must remain server-side; inputs must be validated; database queries must be parameterized. | Security checklist and code review |
| NFR-005 | **Privacy:** Under the proposed D-015 baseline, user-entered skills are not retained and sensitive request contents are not logged. | Storage and logging review |
| NFR-006 | **Accessibility:** Target WCAG 2.2 Level AA for key user flows, subject to project capacity and verification. | Automated and manual accessibility review |
| NFR-007 | **Usability:** Search, filters, comparisons, and matching must have understandable labels and feedback. | User walkthroughs and acceptance tests |
| NFR-008 | **Localization:** English and Arabic content must preserve correct language direction, layout, numbers, and links. | Locale-specific testing |
| NFR-009 | **Maintainability:** Data rules, database changes, metric definitions, and model experiments must be documented and reproducible. | Repository and review checklist |
| NFR-010 | **Compatibility:** The application should work on current major desktop and mobile browsers selected for the demonstration. | Browser smoke tests |
| NFR-011 | **Observability:** Service health and failures must be diagnosable without logging user skill inputs or credentials. | Operational review |
| NFR-012 | **Data provenance:** Important results must identify sample size, source coverage, and relevant dates where available. | UI and report review |
| NFR-013 | **Recoverability:** Database migrations and deployment changes must have a documented recovery or rollback approach appropriate to the selected hosting plan. | Release-readiness review |
| NFR-014 | **Portability:** Data transformations and analytical definitions should be reproducible outside a single developer's machine where feasible. | Re-run workflow in a clean environment |
| NFR-015 | **Legal and ethical use:** Source terms, attribution, privacy, and redistribution limits must be reviewed before public deployment. | Data-use approval checklist |

## 12. Data, API, and Database Design References

- **Logical model:** See [Database Specification](DATABASE_SPECIFICATION.md) and [Logical ERD](../diagrams/04_LOGICAL_ERD.md).
- **Physical model:** See [Proposed PostgreSQL Physical Schema](PHYSICAL_SCHEMA_PROPOSAL.md). It remains provisional until the audit confirms source fields.
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

The following remain open and must be recorded in [Risks and Open Decisions](RISKS_AND_OPEN_DECISIONS.md) or an ADR: actual dataset fields and coverage, source-use permissions, final database provider, backend and frontend frameworks, hosting provider, chart library, numeric performance thresholds, salary-conversion policy, job-family labels, matching-score definition, data refresh cadence, and final skill-input retention policy.

Changes to scope or requirement wording must update this SRS, the relevant user stories/use cases, the traceability matrix, diagrams, and project tasks. No proposed design is considered implemented until verified against the running system.
