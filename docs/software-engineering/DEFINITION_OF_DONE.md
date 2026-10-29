# Definition of Done

A task is complete only when its deliverable is reviewable, its acceptance criteria are met, and its impact on related documentation and requirements has been addressed.

## Project-Level Criteria

- All Must requirements have an implemented or explicitly documented disposition.
- Conditional features have passed their data-quality gates or are clearly marked unsupported.
- The application presents the collected sample with appropriate provenance and limitations.
- The primary user flows work in English and Arabic, including RTL behavior.
- Security, privacy, and data-source constraints have been reviewed.
- Operating instructions and the final demonstration materials are available.

## Documentation Task Criteria

- The document is professional English and has a clear purpose and owner or review path.
- Assumptions, unknowns, and decisions are distinguished from implemented facts.
- Internal links work and related requirements, tasks, and decisions are cross-referenced.
- No implementation comments, credentials, private records, or unapproved raw data are included.

## Data and Database Task Criteria

- Source files remain unchanged.
- Transformations are documented and reproducible.
- Data dictionary, schema, and ERD match the implemented data model.
- Missing values, duplicates, salary units, and date meanings are handled explicitly.
- Record counts and relational integrity have been validated.

## Analytics and ML Task Criteria

- The question, sample, method, assumptions, and limitations are documented.
- Metrics are traceable to source queries or reproducible experiments.
- Models are compared with a baseline and evaluated on data not used for fitting.
- Errors and market-specific limitations are reviewed.
- Weak or unsupported results are not presented as validated product features.

## Web and API Task Criteria

- User-visible behavior meets its acceptance criteria, including loading, empty, missing-data, and error states.
- API behavior matches its documented contract.
- No credentials are exposed to the browser or repository.
- Accessibility, responsive layout, language direction, and source links have been reviewed.
- Displayed metrics reconcile with their documented source.

## Pull-Request Criteria

- The change is scoped to the linked task and has been reviewed by another team member where appropriate.
- Required checks pass and relevant tests are recorded.
- Documentation, traceability, and risk records are updated.
- No raw data, secrets, or unintended user information are included.
