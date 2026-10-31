# Test Strategy

## Objectives

- Verify that the application implements approved requirements and user flows.
- Ensure displayed metrics agree with documented SQL and Python analyses.
- Protect data integrity, user privacy, and safe failure behavior.
- Evaluate ML outputs separately from ordinary application functionality.

## Test Levels

| Level | Scope | Examples |
|---|---|---|
| Unit | Isolated business rules and transformations | Skill normalization, salary parsing, metric definitions, input validation |
| Data quality | Dataset and relational constraints | Missing-value expectations, duplicate rules, foreign keys, normalized values |
| Integration | Boundaries between services and database | Query results, migrations, resource lookup, matching service availability |
| API contract | Request and response behavior | Filter validation, pagination, error categories, empty results |
| End-to-end | Complete visitor journeys | Search to detail, market comparison, skills to match to resource |
| Analytics reconciliation | UI values against source calculations | Sample counts, salary summaries, skill frequencies, time buckets |
| ML evaluation | Model quality and repeatability | Baselines, held-out metrics, error review, leakage checks |
| Accessibility and localization | Keyboard, screen reader semantics, RTL/LTR, translated states | Critical workflows in English and Arabic |
| Security | Input handling and configuration | Injection checks, secret scanning, error disclosure, log privacy |
| Performance | Responsiveness at agreed data and demo load | Common search and dashboard requests, large-result safeguards |

## Required User-Flow Tests

1. View the market overview and confirm sample-size context.
2. Search and filter job advertisements, including a no-results case.
3. Open a job detail page with missing fields and verify the source link behavior.
4. Compare markets with unequal sample sizes and ensure the limitation is visible.
5. Submit valid, empty, unrecognized, and oversized skill input.
6. Review match explanations and verify that skill input is not persisted or logged.
7. Open a learning resource and verify its language and access description; confirm only `free_verified` items are labelled free.
8. Switch between English and Arabic and check RTL/LTR layout.
9. Simulate database or model unavailability and verify safe recovery states.

## Data and ML Test Requirements

- Validate schema, keys, uniqueness rules, required fields, and expected missingness.
- Use representative fixtures that do not contain private or restricted records.
- Test salary calculations only with comparable units and explicitly handled ranges.
- Keep duplicate advertisements from crossing training and test partitions.
- Compare each model with a baseline and report metrics appropriate to its task.
- Review representative false positives and false negatives before using model outputs in the interface.
- Do not treat data quality checks or a high aggregate score as proof of market representativeness.

## Test Data and Environments

Use separate development/test and demonstration/production configurations where the selected hosting setup permits. Test fixtures should be synthetic or approved, minimized, and free of credentials. Do not use private production credentials in notebooks or local test files.

## Exit Criteria

- All Must requirements have a documented test or review result.
- No unresolved critical or high-severity defect affects a primary user journey, data integrity, privacy, or security.
- Key metrics shown in the interface reconcile with their source queries.
- Model outputs shown to users have passed their documented quality gates.
- English and Arabic critical flows have been reviewed, including RTL behavior.
- Known limitations and unimplemented Conditional requirements are documented.

Severity definitions and any numeric coverage or performance thresholds must be agreed by the team before implementation testing begins.
