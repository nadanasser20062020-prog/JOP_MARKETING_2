# Contributing to JOP Marketing Intelligence

## Before Starting

- Review the [project plan](docs/PROJECT_PLAN.md), [feature specification](docs/FEATURE_SPEC.md), and relevant [software engineering documentation](docs/software-engineering/README.md).
- Link work to a project task identifier or GitHub Issue.
- Confirm data availability and dependencies before starting work that depends on specific fields.

## Work and Review Process

1. Work on a scoped task with clear acceptance criteria.
2. Keep changes focused and use the repository's GitHub task and pull-request templates.
3. Run relevant checks and document the results.
4. Request peer review for changes to data, database structure, analytics, models, security, or user-facing behavior.
5. Update related specifications and traceability records when requirements or behavior change.

## Documentation and Code Standards

- Write repository documentation and technical specifications in professional English.
- Do not add inline source-code comments. Use clear names and document design decisions in the appropriate documentation or Architecture Decision Record.
- Mark assumptions and unresolved items explicitly; do not describe a proposed design as implemented behavior.

## Data and Security

- Treat original Drive files as read-only.
- Do not commit large raw or processed datasets, credentials, environment files, or private records.
- Keep database secrets outside frontend code, notebooks, and Git history.
- Follow the security and privacy requirements in `docs/software-engineering/SECURITY_PRIVACY.md`.

## Pull Requests

A pull request should link its task, describe the change, state how it was verified, and identify relevant limitations. It should not be merged until the acceptance criteria are met and the affected documentation is current.
