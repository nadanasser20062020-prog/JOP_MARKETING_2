# GitHub Workflow

## Task Identifiers

Every task in the [Project Plan](PROJECT_PLAN.md) has an identifier such as T01 or T14. When creating a GitHub Issue, begin its title with the identifier and use `.github/ISSUE_TEMPLATE/task.md`.

## Suggested Board Statuses

- **Backlog:** Planned but not ready to start.
- **Ready:** Requirements and dependencies are clear.
- **In Progress:** An owner or team is actively working on it.
- **Review:** Work is ready for peer review.
- **Blocked:** A documented dependency or decision prevents progress.
- **Done:** Acceptance criteria have been met, outputs are documented, and changes have been reviewed.

## Definition of Ready

Before work begins, a task should have a clear objective, known inputs, resolved dependencies, a reviewable deliverable, and verifiable acceptance criteria. Do not start an ML task before confirming that the required fields are available.

## Definition of Done

Close a task only when:

- Its acceptance criteria are met.
- Results are reproducible or otherwise reviewable.
- Related documentation has been updated.
- Changes contain no credentials or large raw data files.
- Another team member has reviewed the result, figures, or design as appropriate.

## Suggested Labels

`data`, `database`, `sql`, `analysis`, `ml`, `frontend`, `backend`, `documentation`, `testing`, `blocked`, `conditional`.

## Team Responsibilities

After T01, assign owners for data and database work, analytics, models, frontend, backend, and integration. One person may own multiple areas, but each Issue should have a clear owner and deliverable. Review results before merging them.

The repository includes task and pull-request templates. No standalone GitHub Issues or Project board were created as part of this planning update.
