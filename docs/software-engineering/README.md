# Software Engineering Documentation

This section defines the product and engineering baseline for JOP Marketing Intelligence. It covers requirements, user behavior, architecture, interfaces, data storage, security, quality, and delivery.

## Document Status

Most documents remain design specifications rather than implementation. The initial data audit is complete, and Neon/PostgreSQL has been selected for the database. An initial executable DDL file is available at `../../scripts/database_loading/neon_schema.sql`, but it has not been applied to Neon and does not include a data loader. Frontend/backend frameworks, deployment hosting, and operational targets remain open; dependent requirements are provisional or conditional.

## Product Definition

- [Software Requirements Specification (SRS)](REQUIREMENTS_SPECIFICATION.md)
- [System Analysis and Design Deliverables Coverage](SYSTEM_ANALYSIS_DELIVERABLES.md)
- [Documentation Status and Roadmap](DOCUMENTATION_ROADMAP.md)
- [User Stories and Acceptance Criteria](USER_STORIES.md)
- [Use Cases and User Flows](USE_CASES.md)
- [Requirements Traceability Matrix](TRACEABILITY_MATRIX.md)

## System Design

- [System Architecture](ARCHITECTURE.md)
- [API Specification](API_SPECIFICATION.md)
- [Logical Database Specification](DATABASE_SPECIFICATION.md)
- [Proposed PostgreSQL Physical Schema](PHYSICAL_SCHEMA_PROPOSAL.md)
- [Initial Neon PostgreSQL DDL](../../scripts/database_loading/neon_schema.sql)
- [UX, Accessibility, and Localization](UX_ACCESSIBILITY_I18N.md)
- [UI/UX Guidelines and Low-Fidelity Wireframes](UI_UX_GUIDELINES_AND_WIREFRAMES.md)
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
