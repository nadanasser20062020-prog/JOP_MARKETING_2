# Tests

Test work is separated by level and responsibility:

- [`unit/`](unit/README.md): isolated transformations, local SQLite migrations/loading, and business rules.
- [`integration/`](integration/README.md): database, API, and service boundaries.
- [`data_quality/`](data_quality/README.md): data contracts, missingness, duplicates, and relationships.
- [`e2e/`](e2e/README.md): complete visitor journeys through the website.

Run the current test suite with `python -m unittest discover -s tests -v`. Database tests use temporary SQLite files and do not connect to or depend on an external database. See `docs/software-engineering/TEST_STRATEGY.md`; use only approved test data and never place private data or credentials in fixtures.
