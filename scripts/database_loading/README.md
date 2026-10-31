# Neon Database Schema and Loader

`neon_schema.sql` is the initial PostgreSQL schema for Neon. Run the complete file in the Neon SQL Editor after selecting the intended database. It creates 12 tables, constraints, indexes, and seed rows for the seven source datasets and their processed source files.

The SQL creates schema objects only. It does not upload the compressed CSV files or create a Neon project. A repeat-safe Python data loader is still planned.

## Table relationships

- `data_sources` has many `source_files`.
- `source_files` identifies the source dataset, source filename, snapshot group, and snapshot type for each `jobs` row.
- `jobs` has many `job_skills`; each `job_skills` row references one `skills` row.
- `skills` has many `skill_aliases` and can be associated with many `learning_resources` through `learning_resource_skills`.
- `skill_observations` references a source dataset and a normalized alias; that alias leads to its canonical skill.
- `learning_resources` has many language rows in `learning_resource_languages`.
- `import_runs` and `source_files` are associated through `import_run_files`, which stores per-file counts and status.

## Recommended data loading order

1. Run `neon_schema.sql` once for a new Neon database.
2. Load `skill_catalog.csv` into `skills` first, then load `skill_aliases.csv` into `skill_aliases`.
3. Load the three `jobs_*.csv.gz` files into `jobs`.
4. Load `job_skills.csv.gz` into `job_skills`.
5. Load `skill_observations.csv.gz` into `skill_observations`.
6. Load `learning_resources.csv` into `learning_resources`, then split its semicolon-separated `skill_ids` and `languages` into the two relationship tables.
7. Record each pipeline execution in `import_runs` and `import_run_files` if import auditing is enabled.

Preserve the separate historical and unverified snapshot groups. Do not treat `source_updated_at` as a posting date or `listing_status` as verified. Keep Neon connection strings in environment variables, never in the repository.