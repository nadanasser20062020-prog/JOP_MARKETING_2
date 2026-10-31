# Project Diagram Pack

All diagrams in this directory are version-controlled Mermaid diagrams and render in GitHub Markdown. They describe the proposed system and must be reviewed against the dataset audit, final feature scope, and approved technology decisions before implementation.

## Architecture and Data

| Diagram | Purpose |
|---|---|
| [System Context](01_SYSTEM_CONTEXT.md) | Shows users, the product boundary, source files, and external destinations. |
| [Container Architecture](02_CONTAINER_ARCHITECTURE.md) | Shows the proposed frontend, API, services, database, preparation, analytics, and model containers. |
| [Backend Components](03_BACKEND_COMPONENTS.md) | Shows responsibilities and interactions within the proposed backend. |
| [Logical ERD](04_LOGICAL_ERD.md) | Shows candidate relational entities and relationships; fields remain subject to data audit. |
| [Data Pipeline](05_DATA_PIPELINE.md) | Shows read-only source handling, quality gates, loading, and downstream use. |
| [DFD Level 0](16_DFD_LEVEL_0.md) | Shows the system as one process and its external information exchanges. |
| [DFD Level 1](17_DFD_LEVEL_1.md) | Decomposes the system into data processes and logical stores. |
| [Conceptual Domain Class Diagram](18_DOMAIN_CLASS_DIAGRAM.md) | Shows domain objects and associations alongside the relational ERD. |
| [Data Quality Decision Tree](15_DATA_QUALITY_GATES.md) | Shows when time trends, salary modeling, classification, matching, and other outputs are supported. |

## Product and User Flows

| Diagram | Purpose |
|---|---|
| [Use Case Diagram](06_USE_CASE_DIAGRAM.md) | Summarizes visitor and project-team capabilities. |
| [Job Discovery Flow](07_JOB_DISCOVERY_FLOW.md) | Shows the search, filter, detail, and source-link journey. |
| [Job Search Sequence](19_JOB_SEARCH_SEQUENCE.md) | Shows the search and detail-request interactions across UI, API, services, and database. |
| [Skill Matching Activity](08_SKILL_MATCHING_ACTIVITY.md) | Shows validation, normalization, ranking, gaps, and resource navigation. |
| [Skill Matching Sequence](09_SKILL_MATCHING_SEQUENCE.md) | Shows request and response interactions across UI, API, services, and database. |
| [Site Map](13_SITE_MAP.md) | Shows the proposed navigation and page hierarchy. |
| [UI/UX Guidelines and Low-Fidelity Wireframes](../software-engineering/UI_UX_GUIDELINES_AND_WIREFRAMES.md) | Shows proposed layout sketches and design/accessibility guidance. |

## Analytics, ML, and Delivery

| Diagram | Purpose |
|---|---|
| [Analytics Workflow](10_ANALYTICS_WORKFLOW.md) | Shows the SQL-in-Python and Python visualization workflow. |
| [Machine Learning Lifecycle](11_ML_LIFECYCLE.md) | Shows task-specific data gates, evaluation, and release decisions. |
| [Deployment View](12_DEPLOYMENT_VIEW.md) | Shows logical local, CI, and demonstration environments without choosing a hosting provider. |
| [Development and Release Flow](14_DEVELOPMENT_RELEASE_FLOW.md) | Shows task intake, implementation, review, verification, and release. |

## Diagram Conventions

- These are design-level diagrams, not evidence that a component has been implemented.
- Optional fields, unknown data coverage, and conditional model paths are intentional.
- PostgreSQL/Neon is a proposed database choice; finalize it with the team.
- Do not add a diagram-specific implementation detail without updating the related architecture or requirements document.
