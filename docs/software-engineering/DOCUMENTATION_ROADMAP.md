# Documentation Status and Roadmap

This roadmap distinguishes specifications that can be established from the project brief from documents that require verified data, implementation decisions, or test results. It prevents provisional design from being mistaken for completed implementation.

## Baseline Documents Prepared Now

- Product scope and software requirements.
- User stories, acceptance criteria, and use cases.
- Proposed system context and logical architecture.
- Proposed API contract and logical database model.
- UX, accessibility, localization, security, and privacy requirements.
- Test strategy, development workflow, deployment plan, and definition of done.
- Requirements traceability, glossary, risk register, and decision-record process.
- Data Dictionary, Dataset Card, and Model Card templates.

## Documents to Finalize After the Dataset Audit

- **Completed Data Dictionary:** Actual source columns, types, units, missingness, and transformations.
- **Final ERD and physical schema:** Confirmed entities, keys, constraints, and indexes.
- **Dataset Card:** Actual sources, collection dates, coverage, record counts, biases, and permitted uses.
- **Data-quality report:** Measured duplicate and missing-value rates, field coverage, and validation results.
- **Final feature feasibility matrix:** Which filters, comparisons, salary analyses, and trends are supported.

## Documents to Finalize After Technology Selection

- **Accepted Architecture Decision Records:** Frameworks, hosting, database configuration, and model-serving approach.
- **Implemented API contract:** Exact request and response schemas, status codes, and authentication policy if it changes.
- **Environment and deployment runbook:** Actual environment names, configuration keys, migration steps, backups, and rollback process.
- **CI/CD workflow:** Actual automated checks and deployment stages.
- **Final performance thresholds:** Measured against the chosen hosting platform and expected dataset size.

## Documents to Finalize During and After Implementation

- **Screen wireframes and design-system specification:** Review with the team and representative users before building the UI.
- **Detailed test cases and test reports:** Map to implemented components and acceptance criteria.
- **Operational runbooks and release notes:** Verify against the actual hosting and recovery procedures.
- **User guide:** Capture the implemented interface and final behavior after feature freeze.
- **Model Cards and model evaluation reports:** Complete only after models have trained and passed evaluation.
- **Final dataset/model cards:** Include actual provenance, versions, evaluation evidence, and limitations.

## Completion Rule

Do not fill unknown values with guesses. Mark a document as **Proposed**, **Pending Data Audit**, or **Pending Implementation** until supporting evidence exists. Update the traceability matrix and decision register when a document is finalized.
