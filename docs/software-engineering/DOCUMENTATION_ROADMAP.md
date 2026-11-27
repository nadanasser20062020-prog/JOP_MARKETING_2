# Documentation Status and Roadmap

This roadmap distinguishes implemented local SQLite/Node.js API artifacts from documents that still require frontend work, source refreshes, deployment checks, or test evidence. Keep implementation claims aligned with the code and latest validation results.

## Baseline Documents Prepared Now

- Product scope and software requirements.
- User stories, acceptance criteria, and use cases.
- Proposed system context and logical architecture.
- Implemented Node.js API contract and local SQLite data model.
- Executable SQLite migrations, local loader, synthetic Node API fixture tests, and data-integrity checks.
- UX, accessibility, localization, security, and privacy requirements.
- Test strategy, development workflow, deployment plan, and definition of done.
- Requirements traceability, glossary, risk register, and decision-record process.
- Data Dictionary, Dataset Card, and Model Card templates.

## Documents to Maintain as Sources Change

- **Data Dictionary and audit:** Reconfirm source columns, types, units, missingness, and transformations for every new source refresh.
- **ERD and physical schema:** The current SQLite tables, keys, and constraints are implemented; update with a reviewed migration only when the data model changes.
- **Dataset Card:** Keep actual sources, collection dates, coverage, record counts, biases, and permitted uses current.
- **Data-quality report:** Rebuild and review duplicate/missing-value rates, field coverage, and relationship checks for each normalized load.
- **Feature feasibility matrix:** Revisit supported filters, comparisons, salary analyses, and trends when coverage changes.

## Documents to Finalize as Runtime Evidence Is Added

- **Accepted Architecture Decision Records:** Node.js API and local SQLite-only database decisions are implemented. Frontend framework and chart library remain open. Full-data Vercel packaging is conditional; no remote database service is approved.
- **API contract:** Implemented request/response schemas, status codes, validation, empty results, privacy, and limitations are documented. Update only when the API changes.
- **Environment and operation runbook:** Local `APP_URL`, `JOP_DATABASE_PATH`, migrations, file backups, restore procedure, and Vercel data-file caveat are documented.
- **CI/CD workflow:** Add only after the actual deployment stages are selected.
- **Final performance thresholds:** Measure against the restored full SQLite database and demonstration hardware.

## Documents to Finalize During and After Implementation

- **High-fidelity mockups and final design-system specification:** Review the low-fidelity wireframes and proposed palette with the team and representative users before building the UI.
- **Detailed test cases and test reports:** Map to implemented components and acceptance criteria.
- **Operational runbooks and release notes:** Verify against local application-start, SQLite backup, import, and recovery procedures.
- **User guide:** Capture the implemented interface and final behavior after feature freeze.
- **Model Cards and model evaluation reports:** Complete only after models have trained and passed evaluation.
- **Final dataset/model cards:** Include actual provenance, versions, evaluation evidence, and limitations.

## Completion Rule

Do not fill unknown values with guesses. Mark a document as **Proposed**, **Pending Data Audit**, or **Pending Implementation** until supporting evidence exists. Update the traceability matrix and decision register when a document is finalized.
