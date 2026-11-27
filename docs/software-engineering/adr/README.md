# Architecture Decision Records

Architecture Decision Records (ADRs) capture decisions that materially affect system structure, technology, privacy, or long-term maintainability.

## Status Values

- **Proposed:** Under review; not yet an approved implementation requirement.
- **Accepted:** Approved by the team and ready to guide implementation.
- **Rejected:** Considered and not selected; retain the rationale for future reference.
- **Superseded:** Replaced by a later ADR; link the replacement.

## Authoring Rules

- Use the template in `TEMPLATE.md`.
- Give each ADR a sequential identifier and concise decision title.
- Record context, the decision, alternatives, consequences, and status.
- Update related requirements, architecture, and risk documents after an ADR is accepted.
- Do not present a Proposed ADR as an implemented fact.

## Current Records

- [ADR-0001: Route browser data access through a Node.js backend API](0001-backend-api-boundary.md) — accepted and implemented; local SQLite is read-only to the API.
- [ADR-0002: Run all online inference in-process in Node.js](0002-in-process-ml-execution.md) — accepted and implemented; Jaccard is a separate deterministic baseline, the exact-title Naive Bayes ranker is served only for limited-scope review, training/evaluation remain offline Python, and clustering stays report-only.
