# Data Pipeline Scripts

This directory contains reproducible Python data-preparation scripts in `data_cleaning/`. Run `python scripts/data_cleaning/clean_all_data.py` from the repository root to rebuild all processed datasets and references. The scripts use the Python standard library.

`database_loading/` contains the Neon/PostgreSQL schema, a loader that defaults to the reduced Arab-complete Neon Free profile, and a SQL storage report. Run `python scripts/database_loading/load_to_database.py --validate-files-only` before connecting; usage and quota caveats are in [`database_loading/README.md`](database_loading/README.md). Data-preparation commands and source caveats are documented in [`data_cleaning/README.md`](data_cleaning/README.md).
