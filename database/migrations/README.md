# SQLite Migrations

`001_initial_sqlite_schema.sql` creates the local domain schema for sources, files, import runs, skills, jobs, skill links and observations, and learning resources and their links. `002_full_archive_provenance.sql` extends source, file, run, and per-file import metadata to preserve archive identities, checksums, row counts, and processing details. `006_cleaned_audit_relational_extension.sql` adds `job_cleaning_audit`, which stores all 123 cleaned CSV columns with a composite foreign key back to `jobs`, plus the `cleaned_jobs`, `actual_salary_rows`, and `synthetic_salary_estimates` views.

Apply migrations with:

```bash
python scripts/database_loading/load_to_database.py init
```

The migration runner records each applied version and SHA-256 checksum in `schema_migrations`. Applied migration files are immutable; add a later numbered migration for schema changes. The loader enables and checks foreign keys on its SQLite connections. Migrations run only against the local SQLite file selected by `JOP_DATABASE_PATH` or the `--database` argument, never a remote service.
