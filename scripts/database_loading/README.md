# Python Database-Loading Script

This directory is reserved for the Python script that loads validated data from `data/processed/` into PostgreSQL/Neon.

Planned entry point: `load_to_database.py`.

The future loader must keep credentials outside the repository, validate the input schema, support safe repeat runs, use controlled transactions where appropriate, and report inserted/updated/skipped row counts and relationship checks. It must not modify raw or processed source files.

No loader code has been created yet. Finalize it after the ERD and database schema are approved.
