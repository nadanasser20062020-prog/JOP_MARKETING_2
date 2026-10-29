# Development Workflow

## Work Intake

- Every unit of work should reference a task identifier from `docs/PROJECT_PLAN.md` or a linked GitHub Issue.
- Keep issues focused on one reviewable deliverable.
- Record dependencies, acceptance criteria, data requirements, and unresolved decisions before implementation begins.
- Do not start work that depends on unverified dataset fields until the data audit is complete.

## Branch and Pull-Request Workflow

1. Start from the team-approved integration branch.
2. Create a short-lived branch for one task or closely related changes.
3. Keep each change scoped and avoid mixing unrelated documentation, data, and application work.
4. Open a pull request linked to its task or issue.
5. Run the relevant tests and checks before requesting review.
6. Obtain review from at least one other team member for database, analytics, model, or security-sensitive changes.
7. Merge only after acceptance criteria and required checks pass.

The team should confirm branch protection, merge strategy, and release-branch policy in GitHub settings.

## Review Expectations

Reviewers should verify:

- The change meets the task acceptance criteria.
- Data definitions and metric calculations match the documented data dictionary.
- No credentials, raw data, or unnecessary personal information are included.
- API and database changes preserve contracts or document breaking changes.
- Model claims are supported by evaluation and limitations.
- User-facing behavior covers loading, empty, missing-data, and error states.
- Documentation and traceability links are updated.

## Documentation and Code Clarity

- Keep repository documentation and technical specifications in professional English.
- Do not add inline source-code comments. Use clear names and document non-obvious decisions in technical documentation or Architecture Decision Records.
- Keep assumptions and unresolved decisions explicit; do not present provisional design as implemented behavior.

## Data, Notebooks, and Secrets

- Treat original Drive data as read-only.
- Do not commit large raw or processed datasets, secrets, environment files, or private records.
- Make analytical notebooks reproducible and keep credentials outside notebook content.
- Separate exploratory work from the data-loading or application pipeline.

## Documentation Change Process

When a requirement or design changes, update the specification, relevant story/use case, traceability entry, risk or decision record, and task acceptance criteria as needed. An implementation change is not complete while its contract documentation is stale.
