# SQLite Physical Schema

**Status:** Implemented as local SQLite migrations `001`–`005`, covering the domain schema, provenance, query indexes, API rollups, and role-skill lookup index. The last full-data validation used the verified archive with 775,155 jobs and 4,026,953 job-skill links; the ignored SQLite file and archive are absent from the current snapshot and must be restored before full-data API operation. SQLite is the only configured database engine. No hosted database, database server, or connection URL is used.

## 1. Local Storage and Runtime

- Default file: `data/processed/job_market.sqlite3`.
- Optional path override: `JOP_DATABASE_PATH` or the loader's `--database` argument; the value must be a local filesystem path.
- The data loader and offline analysis use Python's standard-library `sqlite3`; the Node.js API uses the built-in `node:sqlite` module in read-only mode.
- The existing `.gitignore` rule for `data/processed/*` keeps the generated database and sidecar files out of Git. The ignore file is intentionally unchanged.
- SQLite foreign-key enforcement is enabled on every project connection.
- The database is reproducible from the complete checksum-verified Parquet archive or a separately reviewed complete normalized local staging set. Automatic loading never substitutes the development fixture.

## 2. Implemented Tables

The 12 domain tables are implemented in migration `001_initial_sqlite_schema.sql`.

| Table | Primary key | Purpose |
|---|---|---|
| `data_sources` | `source_dataset TEXT` | Stable source/dataset name plus source kind, snapshot bucket, date semantics, listing status, source-file count, and row count. |
| `source_files` | `(source_dataset, source_file)` | Source-file identity, logical/physical names, role, archive membership, byte size, SHA-256, row count, and archive-member count; references `data_sources`. |
| `import_runs` | `import_run_id INTEGER` | Local import status, timestamps, pipeline version, input fingerprint, quality report, and the original full-archive run ID, date, generator, status, and totals. |
| `import_run_files` | `(import_run_id, source_dataset, source_file)` | Rows read/loaded/rejected and status per source file, plus archive source-file ID, emitted output counts, tables, and processing role; references the run and source file. |
| `skills` | `skill_id TEXT` | Canonical skill name, category, match/review policy, archive counts, and curation notes. |
| `skill_aliases` | `(alias_normalized, skill_id)` | Normalized label, display label, alias type, review/match policy, observed counts, and skill foreign key. One normalized label can be represented for multiple skills if a future audited source requires it. |
| `jobs` | `record_id TEXT` | Preserved source fields and provenance for each staged advertisement. A unique `(record_id, source_dataset, source_file)` key supports the composite relationship below. |
| `job_skills` | `(record_id, skill_id)` | Many-to-many job/skill relationship with source labels and extraction provenance. |
| `skill_observations` | `(source_dataset, skill_normalized, skill_raw)` | Observed source term and its frequency for each dataset. |
| `learning_resources` | `resource_id TEXT` | Curated resource metadata, course-specific access/cost status, verification details, and URL. |
| `learning_resource_skills` | `(resource_id, skill_id)` | Many-to-many resource-to-skill relationship. |
| `learning_resource_languages` | `(resource_id, language_label)` | Resource language labels as recorded; labels are not assumed to be standardized language codes. |

The migration runner also creates `schema_migrations` to record applied migration versions and checksums. It is schema metadata, not a domain table.

## 3. SQLite Storage and Integrity Rules

- Stable identifiers and source content use `TEXT`; counts and the one-based `source_row_number` use `INTEGER`.
- Job dates, salary fields, source IDs, and source text remain `TEXT` so source formats and semantics are not silently normalized. In particular, `posted_at` is distinct from `source_updated_at`, and a text salary is not an inferred numeric salary.
- Missing optional source values are stored as `NULL`; no placeholder employer, location, salary, or posting date is created.
- `jobs.source_dataset/source_file` references `source_files`; `job_skills` references both its job (including its provenance tuple) and `skills`.
- `(record_id, skill_id)` prevents duplicate job-skill links. Foreign keys prevent orphaned jobs, skills, aliases, observations, resources, and import-file records.
- Match policy and learning-resource cost status use checked vocabularies. Source activity remains `unknown_not_verified` unless independently verified.
- Skills, aliases, observations, job links, and resources retain the documented review/provenance labels. Resource verification dates and cost notes are loaded as recorded; loading them does not certify current availability or licensing.

## 4. Indexes

Migrations 001–002 add indexes for source, country, title, and posting-date job filters; reverse skill-to-job lookup; skill alias lookup through its primary key; observed-skill lookup; and skill/language-to-resource lookup. Migration 003 adds normalized-title/source, normalized-country/source, and source/posting-date query indexes. Migration 004 adds materialized API rollup tables and lookup indexes; migration 005 adds the role-skill rollup lookup index. Further indexes should be based on measured full-database query plans.

## 5. Migration and Load Policy

Apply the current migration and load the local database from the repository root:

```bash
python scripts/database_loading/load_to_database.py init
python scripts/database_loading/load_to_database.py load
python scripts/database_loading/load_to_database.py check
```

Install the local Parquet reader, place the checksum-verified `full_archive_parquet_v1_20261028` package in `data/processed/full_archive_parquet_v1_20261028/`, and load the full dataset:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r scripts/database_loading/requirements.txt
python scripts/database_loading/load_to_database.py load --source archive
python scripts/database_loading/load_to_database.py check
```

Automatic mode prefers the complete archive, uses complete normalized local staging files only when the archive is absent, and fails if neither full input is present. The loader has no sample-data source. Repeating an import with the same input fingerprint is a no-op; a different existing snapshot is not overwritten unless `--replace` is explicitly supplied.

The imported full dataset contains 775,155 jobs, 4,026,953 job-skill links, 1,498 skills, 1,648 aliases, 2,482 skill observations, 32 learning resources, 48 resource-skill links, and all 37 language-label links. Learning-resource detail and skill links are loaded from JSON, and language labels are loaded from the CSV. The legacy development seed is retained only for tests, not for application or analysis data.

## 6. Query and Use Constraints

- Use parameterized SQL and allowlisted sort/filter fields from the backend.
- Retrieve suitable aggregates or batches for analysis rather than loading a full local archive without need.
- Preserve source distinctions and show sample size, coverage, and dates in analytical results.
- Do not claim that a listing is active or that a resource is currently free/available solely because it is in the SQLite file.
- Keep the database file local and rebuildable; do not add a server connection string or replace the local file with a hosted database.
