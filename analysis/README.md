# Data Analysis

Analysis reads from the local SQLite database and keeps the source of truth unchanged.

- [`sql/`](sql/README.md): documented SQL for dataset profiling, source and field coverage, normalized skills, exact-title groups, country markets, historical 2023 counts, salary feasibility, and duplicate review.
- [`generate_pre_backend_analysis.py`](generate_pre_backend_analysis.py): reproducibly runs the approved SQL queries, writes aggregate CSVs and charts, and builds the data-driven report in [`reports/pre_backend/`](reports/pre_backend/).
- [`notebooks/`](notebooks/README.md): space for later exploratory notebooks that use the same data definitions and read-only SQLite connection.
- [`reports/`](reports/README.md): findings, evidence, charts, sample sizes, and limitations.

Install the analysis tools with `python -m pip install -r analysis/requirements.txt`. The full local database is not included in Git. The analysis uses SQL aggregates and bounded results rather than loading the 775,155 job rows into memory.
