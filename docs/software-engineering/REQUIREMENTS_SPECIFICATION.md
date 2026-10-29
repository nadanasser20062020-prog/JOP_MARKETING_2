# Software Requirements Specification

**Product:** JOP Marketing Intelligence
**Document status:** Baseline for team review; data-dependent requirements remain conditional.

## 1. Purpose

Specify the user-visible and engineering requirements for a web application that helps engineers explore job-market advertisements and understand the skills associated with relevant roles. The application will present analysis of the team's collected sample, not claim to represent every job in a market.

## 2. Product Goals

- Make collected job advertisements searchable and understandable.
- Summarize role, skill, location, salary, and work-arrangement patterns where supported by the dataset.
- Enable evidence-based comparison between covered markets.
- Help users compare their skills with job advertisements and discover learning resources for gaps.
- Demonstrate an end-to-end data-science workflow supported by sound software-engineering practices.

## 3. Stakeholders and User Classes

- **Job seeker:** Explores markets, roles, skills, and resources.
- **Project team:** Audits data, maintains definitions, builds analyses and the application, and reviews results.
- **Project reviewer:** Evaluates the product, methods, model quality, and limitations.
- **External source/provider:** Publishes job advertisements or learning resources linked from the application.

The current product does not require a user account or an administrative interface.

## 4. Scope Boundaries

### In Scope

- Market overview and job-advertisement exploration.
- Search, filtering, and job details with source links where available.
- Skill-demand exploration, market comparison, and supported time trends.
- Explainable skill matching, skill-gap presentation, and curated learning links.
- English and Arabic interfaces.
- Analysis and model outputs only when data quality supports them.
- Methodology, source coverage, and limitations information.

### Out of Scope

- Saving jobs or searches.
- Notifications or alerts for new jobs.
- User profiles, accounts, or persistent storage of user-entered skills in the initial release.
- Claims that a match guarantees an interview or job offer.
- Automated job scraping or continuous data refresh unless separately approved.

## 5. Functional Requirements

Priority meanings: **Must** is required for the agreed product; **Should** is desirable if data and capacity permit; **Conditional** requires an explicit data-quality gate.

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| FR-001 | The system shall show a market overview based on the available advertisement sample, including sample size and covered markets where known. | Must | Functional test and metric reconciliation |
| FR-002 | The system shall allow users to search job advertisements by supported text fields. | Must | Search tests |
| FR-003 | The system shall provide filters only for fields present and usable in the audited dataset. | Must | Filter tests against the data dictionary |
| FR-004 | The system shall show a detail view for each available job advertisement. | Must | Detail-page test |
| FR-005 | The detail view shall link to the original advertisement when a valid source URL exists. | Must | Link validation |
| FR-006 | The system shall show skill demand by role or market where the data supports the comparison. | Must | Query-to-UI reconciliation |
| FR-007 | The system shall allow comparison of selected markets using comparable metric definitions. | Should | Comparison test and review |
| FR-008 | The system shall show time trends only when the relevant dates are reliable and sufficiently covered. | Conditional | Data-quality gate and chart review |
| FR-009 | The system shall accept a temporary set of user-entered or selected skills for matching. | Must | Input validation and flow test |
| FR-010 | The system shall rank relevant roles or advertisements and explain the basis of each result. | Must | Reviewed test cases |
| FR-011 | The system shall identify missing skills using evidence from relevant advertisements. | Must | Recommendation review |
| FR-012 | The system shall provide links to learning resources whose access status has been reviewed. | Must | Resource-catalogue audit |
| FR-013 | The user interface shall support English and Arabic, including right-to-left presentation for Arabic. | Must | Localization and RTL tests |
| FR-014 | The system shall explain data sources, definitions, methods, and limitations. | Must | Documentation review |
| FR-015 | The system shall distinguish salaries disclosed in advertisements from model-generated estimates. | Must | UI and API contract test |
| FR-016 | The system should process user-entered skill lists transiently and not persist them in the initial release, subject to team approval. | Proposed | Confirm D-015 and review storage/logging behavior |
| FR-017 | The system shall show clear loading, empty, unavailable-data, and error states. | Must | UI state tests |
| FR-018 | The system may show skill co-occurrence or related-skill views when the data is sufficiently complete. | Conditional | Data-quality gate and analysis review |

## 6. Non-Functional Requirements

| ID | Requirement | Proposed verification |
|---|---|---|
| NFR-001 | **Performance:** Common read operations should meet an agreed response-time target at the agreed demonstration data volume. An initial target of 2 seconds at the 95th percentile is proposed for review, not yet committed. | Load test after stack and data-volume decisions |
| NFR-002 | **Reliability:** Database or model failures must produce a clear recoverable message; the interface must not present stale or invented results as current. | Failure-injection and UI-state tests |
| NFR-003 | **Data integrity:** Displayed metrics must be traceable to documented queries or model outputs and must respect the data dictionary. | Reconciliation tests and review |
| NFR-004 | **Security:** Credentials must remain server-side; inputs must be validated; database queries must be parameterized. | Security checklist and code review |
| NFR-005 | **Privacy:** User-entered skills must not be retained in the initial release; logs must not capture sensitive request contents. | Storage and logging review |
| NFR-006 | **Accessibility:** Target WCAG 2.2 Level AA for key user flows, subject to project capacity and verification. | Automated and manual accessibility review |
| NFR-007 | **Usability:** Search, filters, comparisons, and matching must have understandable labels and feedback. | User walkthroughs and acceptance tests |
| NFR-008 | **Localization:** English and Arabic content must preserve correct language direction, layout, numbers, and links. | Locale-specific testing |
| NFR-009 | **Maintainability:** Data rules, database changes, metric definitions, and model experiments must be documented and reproducible. | Repository and review checklist |
| NFR-010 | **Compatibility:** The application should work on current major desktop and mobile browsers selected for the demonstration. | Browser smoke tests |
| NFR-011 | **Observability:** Service health and failures must be diagnosable without logging user skill inputs or credentials. | Operational review |
| NFR-012 | **Data provenance:** Important results must identify sample size, source coverage, and relevant dates where available. | UI and report review |

## 7. Assumptions and Constraints

- The only completed project activity is data collection; actual fields and quality are unknown until T01.
- The source consists of job advertisements; advertisements may be duplicated, expired, incomplete, or biased toward certain markets.
- PostgreSQL/Neon is under consideration for the relational data store; the final database and hosting configuration are not yet approved.
- Salary prediction, time trends, market comparisons, and some filters depend on field coverage and record counts.
- Data source terms, permitted use, and redistribution requirements must be reviewed before public deployment.
- No authentication, saved state, or notification infrastructure is required for the initial release.

## 8. Acceptance and Change Control

A requirement is complete when it has an agreed verification method and the related test or review evidence is recorded. Changes to scope must update this specification, the traceability matrix, relevant user stories, and the project task plan.
