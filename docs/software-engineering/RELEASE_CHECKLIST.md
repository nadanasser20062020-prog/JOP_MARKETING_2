# Release Checklist

Use this checklist for a demonstration or production release. Mark items not applicable with a brief reason rather than leaving them ambiguous.

## Scope and Documentation

- [ ] Release scope matches approved requirements and user stories.
- [ ] Conditional features have passed their data-quality gates or are disabled and documented.
- [ ] Data sources, sample coverage, metric definitions, and limitations are documented.
- [ ] API, database, deployment, and user documentation match the release.
- [ ] Known issues and unsupported markets or fields are recorded.

## Data and Models

- [ ] Dataset version and loading process are known.
- [ ] Record counts, relationships, duplicates, and key fields have been validated.
- [ ] Salary values use documented units and are clearly distinguished from estimates.
- [ ] Models shown to users have current Model Cards, baselines, and evaluation evidence.
- [ ] Learning-resource links and course-level cost status have been reviewed; only `free_verified` items are labelled free.

## Security and Privacy

- [ ] No credentials or raw private data are included in source or build artifacts.
- [ ] Database credentials are configured outside the frontend.
- [ ] Skill input is not persisted or logged in the initial release.
- [ ] External links and error responses have been reviewed.
- [ ] Data source terms and attribution requirements have been checked.

## Product Quality

- [ ] Search, filters, job details, comparison, matching, and resource flows pass acceptance tests.
- [ ] Loading, empty, missing-data, and failure states are verified.
- [ ] English and Arabic critical flows, including RTL, are reviewed.
- [ ] Accessibility, responsive layout, and supported browsers are checked.
- [ ] Displayed metrics reconcile with documented analysis.

## Deployment and Recovery

- [ ] Deployment version and environment are recorded.
- [ ] Database migrations and required data loads are complete.
- [ ] Health checks and critical routes pass in the target environment.
- [ ] Rollback or recovery steps are known and tested where possible.
- [ ] Operational owner and escalation path are identified.

## Release Record

- Release identifier:
- Date:
- Environment:
- Database/data version:
- Reviewer:
- Known limitations:
