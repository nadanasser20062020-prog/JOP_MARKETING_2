# Data Pipeline Scripts

This directory contains reproducible Python data-preparation scripts in `data_cleaning/`. Run `python scripts/data_cleaning/clean_all_data.py` from the repository root to rebuild all processed datasets and references. The scripts use the Python standard library.

The initial Neon/PostgreSQL schema is available at [`database_loading/neon_schema.sql`](database_loading/neon_schema.sql). A repeat-safe Python data loader has not been implemented yet. Data-preparation commands and caveats are documented in [`data_cleaning/README.md`](data_cleaning/README.md).
