# System Analysis and Design Deliverables Coverage

This matrix checks the project documentation against the System Analysis and Design items supplied by the project team. **Present** means a documented artifact exists; **Provisional** means it exists but depends on the data audit or a team decision; **Pending** means it cannot be finalized from current information.

| Requested deliverable | Current artifact | Status and remaining action |
|---|---|---|
| Problem statement and project objectives | [SRS, Sections 2–3](REQUIREMENTS_SPECIFICATION.md) | Present; review with the team and refine success thresholds after the data audit |
| Use case diagram and descriptions | [Use Case Diagram](../diagrams/06_USE_CASE_DIAGRAM.md) and [Use Cases](USE_CASES.md) | Present; validate flows against the approved feature scope |
| Functional requirements | [SRS, Section 9](REQUIREMENTS_SPECIFICATION.md) | Present; traceable IDs and verification criteria included |
| Non-functional requirements | [SRS, Section 11](REQUIREMENTS_SPECIFICATION.md) | Present; proposed performance target must be confirmed after profiling |
| Feature-to-data field mapping | [Feature-to-Data Field Mapping](FEATURE_DATA_FIELD_MAPPING.md) and [Data Dictionary](../data/DATA_DICTIONARY.md) | Mapped to measured SQLite coverage, field relationships, readiness gates, and denominators |
| Software architecture | [Architecture](ARCHITECTURE.md), [System Context](../diagrams/01_SYSTEM_CONTEXT.md), [Container](../diagrams/02_CONTAINER_ARCHITECTURE.md) | Node.js API/local SQLite boundary and in-process limited-scope title ranking implemented; frontend framework and full-data hosted deployment remain open |
| ER diagram | [Logical ERD](../diagrams/04_LOGICAL_ERD.md) | Provisional; candidate entities and fields must be checked against the actual dataset |
| Logical schema | [Database Specification](DATABASE_SPECIFICATION.md) and [Logical ERD](../diagrams/04_LOGICAL_ERD.md) | Provisional; finalize after the data dictionary and ERD review |
| Physical schema, attributes, keys, constraints, and normalization | [SQLite Physical Schema](PHYSICAL_SCHEMA_PROPOSAL.md) and executable migration | Implemented locally; add new migrations for future schema changes |
| DFD context level | [DFD Level 0](../diagrams/16_DFD_LEVEL_0.md) | Present; review external data flows with the team |
| Detailed DFD | [DFD Level 1](../diagrams/17_DFD_LEVEL_1.md) and [Data Pipeline](../diagrams/05_DATA_PIPELINE.md) | Present; align with the final ingestion and API design |
| Sequence diagrams | [Job Search Sequence](../diagrams/19_JOB_SEARCH_SEQUENCE.md) and [Skill Matching Sequence](../diagrams/09_SKILL_MATCHING_SEQUENCE.md) | Present; update after API contracts are implemented |
| Activity diagrams | [Job Discovery Flow](../diagrams/07_JOB_DISCOVERY_FLOW.md) and [Skill Matching Activity](../diagrams/08_SKILL_MATCHING_ACTIVITY.md) | Present; verify all alternate and error flows during implementation |
| State diagram | [Matching Request State](../diagrams/20_MATCH_REQUEST_STATE.md) and [Job Record State](../diagrams/21_DATA_RECORD_STATE.md) | Present; conceptual states may map to logs or UI behavior rather than database columns |
| Class diagram | [Conceptual Domain Class Diagram](../diagrams/18_DOMAIN_CLASS_DIAGRAM.md) | Provisional; attributes are subject to the data audit |
| Wireframes and mockups | [User Journeys and Wireframes](USER_JOURNEYS_AND_WIREFRAMES.md) and [UI/UX Guidelines](UI_UX_GUIDELINES_AND_WIREFRAMES.md) | Evidence-aware low-fidelity flows present; high-fidelity mockups await team review |
| UI/UX guidelines | [UX, Accessibility, and Localization](UX_ACCESSIBILITY_I18N.md) and [UI/UX Guidelines](UI_UX_GUIDELINES_AND_WIREFRAMES.md) | Present as a proposal; approve palette, typography, and final responsive layouts with the team |
| Technology stack | [SRS, Section 6](REQUIREMENTS_SPECIFICATION.md) and [Open Decisions](RISKS_AND_OPEN_DECISIONS.md) | Node.js 22 API, built-in SQLite runtime, and Python loader are implemented; frontend framework remains TBD; full-data Vercel packaging is unverified |
| Deployment diagram | [Deployment View](../diagrams/12_DEPLOYMENT_VIEW.md) | Present; platform-neutral until hosting is selected |
| Component diagram | [Backend Components](../diagrams/03_BACKEND_COMPONENTS.md) | Present; proposed backend boundaries, framework-independent |
| API documentation | [API Specification](API_SPECIFICATION.md) | Implemented Node.js contract, inputs, outputs, validation, empty/errors, privacy, and examples; selected endpoints reconcile in full-data HTTP smoke checks. Comprehensive per-route reconciliation remains pending |
| Testing and validation plan | [Test Strategy](TEST_STRATEGY.md) and [Release Checklist](RELEASE_CHECKLIST.md) | 16 Node fixture tests, 26 Python tests, 6 matching-baseline tests, and full DB integrity check pass; selected routes work over HTTP on the full local DB. Latency/load and end-to-end UI checks remain pending |
| Deployment strategy | [Deployment and Operations](DEPLOYMENT_OPERATIONS.md) | Local Node/SQLite steps and Vercel file-bundling caveat documented; full-dataset Vercel deployment not verified |
| Analytics, ML, and data-flow diagrams | [Pre-Backend Analysis](../../analysis/reports/pre_backend/PRE_BACKEND_ANALYSIS.md), [Metrics and Model Method](METRICS_AND_MODEL_METHOD.md), [ML Lifecycle](../diagrams/11_ML_LIFECYCLE.md), [Data Pipeline](../diagrams/05_DATA_PIPELINE.md) | Reproducible 19-query descriptive analysis, sampled held-out Naive Bayes evaluation for exact-title ranking, and exploratory clustering evaluation are present; reviewed skill-pair eligibility is enforced; production occupational classification, salary prediction, and activity prediction remain no-go |

## Overall Assessment

The requested analysis-and-design artifact types are represented. The SRS, logical model, and diagram set form a reviewable design baseline; the physical SQLite schema, provenance/Node-query migrations, full-archive loader, descriptive analysis, and Node.js API are implemented. In the last full-data run the ignored database had 775,155 jobs and 4,026,953 stored job-skill links; `check` reported migrations 001–005 and zero foreign-key violations, and selected routes passed HTTP smoke checks. The ignored archive/database are absent from the current snapshot, so these full-data checks cannot be repeated until restored. Remaining evidence includes complete endpoint reconciliation, performance/load profiling, frontend implementation and browser/accessibility tests, high-fidelity mockups, public-data permissions, and Vercel bundle feasibility.
