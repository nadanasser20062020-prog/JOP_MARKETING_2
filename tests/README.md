# Tests

Test work is separated by level and responsibility:

- [`unit/`](unit/README.md): isolated transformations and business rules.
- [`integration/`](integration/README.md): database, API, and service boundaries.
- [`data_quality/`](data_quality/README.md): data contracts, missingness, duplicates, and relationships.
- [`e2e/`](e2e/README.md): complete visitor journeys through the website.

See `docs/software-engineering/TEST_STRATEGY.md`. Use only approved test data and never place secrets in fixtures.
