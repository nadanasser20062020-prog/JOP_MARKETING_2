# Software Engineering Documentation

This section defines the product and engineering baseline for JOP Marketing Intelligence. It covers requirements, user behavior, architecture, interfaces, data storage, security, quality, and delivery.

## Document Status

These documents combine implementation artifacts and design specifications. The local SQLite schema, provenance migrations, checksum-verified full-archive loader, 19-query analysis, and Node.js 22 read-only API are implemented. In the last full-data run, the Git-ignored SQLite file held 775,155 job rows, 4,026,953 stored job-skill links, and 3,701,019 eligible links across 173 reviewed skill IDs; `check` found zero foreign-key violations. Sixteen Node tests, 26 Python `unittest` tests, six matching-baseline tests, syntax checks, and selected full-data HTTP smoke routes passed. The ignored archive and database are absent from the current snapshot and must be restored to repeat full-data checks. Online Jaccard is a deterministic role-profile baseline; separately, a Naive Bayes exact-title ranker runs in Node for limited-scope review only, with training/evaluation in offline Python. Clustering remains report-only, and no separate ML server is used. There is no frontend entry point in this checkout; browser/UI work, concurrency/performance testing, and Vercel packaging remain open. The loader has no partial-sample source or fallback.

## Product Definition

- [Software Requirements Specification (SRS)](REQUIREMENTS_SPECIFICATION.md)
- [System Analysis and Design Deliverables Coverage](SYSTEM_ANALYSIS_DELIVERABLES.md)
- [Documentation Status and Roadmap](DOCUMENTATION_ROADMAP.md)
- [User Stories and Acceptance Criteria](USER_STORIES.md)
- [Use Cases and User Flows](USE_CASES.md)
- [Pre-Backend Product Scope and Acceptance Criteria](PRODUCT_SCOPE_AND_ACCEPTANCE.md)
- [Pre-Backend Data Readiness Gate](PRE_BACKEND_READINESS.md)
- [Feature-to-Data Field Mapping](FEATURE_DATA_FIELD_MAPPING.md)
- [Arabic Graduation Defense Guide](PROJECT_DEFENSE_GUIDE_AR.md)
- [Requirements Traceability Matrix](TRACEABILITY_MATRIX.md)

## System Design

- [System Architecture](ARCHITECTURE.md)
- [Pre-Backend Single-Process Architecture](SYSTEM_ARCHITECTURE_PRE_BACKEND.md)
- [Pre-Backend Metrics and Model Method](METRICS_AND_MODEL_METHOD.md)
- [API Specification](API_SPECIFICATION.md)
- [Logical Database Specification](DATABASE_SPECIFICATION.md)
- [SQLite Physical Schema](PHYSICAL_SCHEMA_PROPOSAL.md)
- [UX, Accessibility, and Localization](UX_ACCESSIBILITY_I18N.md)
- [UI/UX Guidelines and Low-Fidelity Wireframes](UI_UX_GUIDELINES_AND_WIREFRAMES.md)
- [Evidence-Aware User Journeys and Wireframes](USER_JOURNEYS_AND_WIREFRAMES.md)
- [Complete Diagram Pack](../diagrams/README.md)

## Quality and Operations

- [Security and Privacy](SECURITY_PRIVACY.md)
- [Test Strategy](TEST_STRATEGY.md)
- [Deployment and Operations](DEPLOYMENT_OPERATIONS.md)
- [Development Workflow](DEVELOPMENT_WORKFLOW.md)
- [Release Checklist](RELEASE_CHECKLIST.md)
- [Definition of Done](DEFINITION_OF_DONE.md)

## Governance

- [Risks and Open Decisions](RISKS_AND_OPEN_DECISIONS.md)
- [Glossary](GLOSSARY.md)
- [Documentation Status and Roadmap](DOCUMENTATION_ROADMAP.md)
- [Architecture Decision Records](adr/README.md)

## Templates to Complete as Evidence Becomes Available

- [Data Dictionary Template](DATA_DICTIONARY_TEMPLATE.md)
- [Dataset Card Template](DATASET_CARD_TEMPLATE.md)
- [Model Card Template](MODEL_CARD_TEMPLATE.md)

## Related Project Documents

- [Overall project plan](../PROJECT_PLAN.md)
- [Feature specification](../FEATURE_SPEC.md)
- [Data and database planning notes](../DATA_AND_DATABASE.md)
- [Analytics plan](../ANALYTICS_PLAN.md)
- [Machine learning plan](../ML_PLAN.md)
- [Web application plan](../WEB_APP_PLAN.md)
- [Repository structure](../REPO_STRUCTURE.md)
- [GitHub workflow](../GITHUB_WORKFLOW.md)
