# Database Specification

**Status:** The complete 775,155-job, 4,026,953-link dataset is loaded in local SQLite. The executable schema is [SQLite Physical Schema](PHYSICAL_SCHEMA_PROPOSAL.md), implemented by migrations `001_initial_sqlite_schema.sql` and `002_full_archive_provenance.sql`. The project uses a local SQLite file only; do not configure an external or hosted database.

## Database Goals

- Support reproducible analysis and local application queries.
- Preserve source provenance and distinguish original source values from curated or standardized values.
- Represent job-skill and resource-skill many-to-many relationships with explicit foreign keys.
- Avoid treating missing or inferred fields as observed facts.
- Keep the database local, easy to rebuild, and independent of network database services.

## Implemented Entities

| Entity | Purpose | Key data |
|---|---|---|
| Data Source | Dataset/source label | `source_dataset`, display name, source kind, date/listing semantics, file and row counts |
| Source File | Source-file and snapshot provenance | Dataset/file composite key, archive file ID, physical/logical names, role, size, SHA-256, row counts |
| Import Run | Reproducible local load history | Status, timestamps, input fingerprint, quality report, original archive run ID/date/counts |
| Import Run File | Per-file load counts and status | Run/source/file key, rows read/loaded/rejected, emitted counts, output tables, processing role |
| Job | One collected job-ad record | Staging ID, source/row provenance, original source fields, quality flags |
| Skill | Canonical and observed skill term | Stable `skill_id`, category, match policy, review status, archive counts |
| Skill Alias | Reviewed or observed skill label | Normalized alias, label, skill ID, alias type, match/review policy |
| Job Skill | Job-to-skill association | Job/skill composite key, raw/normalized label, provenance and review status |
| Skill Observation | Source-specific observed term count | Dataset, raw/normalized term, occurrence count |
| Learning Resource | Reviewed learning page/course | Provider, type, URL, access/cost caveats, verification details |
| Learning Resource Skill | Resource-to-skill association | Resource/skill composite key |
| Learning Resource Language | Recorded language label | Resource/language composite key; source label is preserved |

Company, country, city, and region values remain on the job record as supplied by the source rather than being forced into unverified dimensions. The initial scope has no user account, saved-search, or persistent skill-input tables.

## Relationship Cardinalities

- One dataset may have many source files; each file belongs to one known dataset.
- One import run may include many source files, with one status/count record per run and file.
- One source file may contribute many jobs; each job references one known dataset and file.
- Job records and skills have a many-to-many relationship represented by `job_skills`.
- A skill may have many aliases and many observations across source datasets.
- Learning resources and skills have a many-to-many relationship represented by `learning_resource_skills`.
- A learning resource may retain multiple language labels in `learning_resource_languages`.

## Integrity and Normalization Rules

- Use stable identifiers independent of display titles and source text.
- Enforce foreign keys for sources/files, jobs, skills, aliases, observations, imports, and resources; every project connection enables SQLite foreign-key checks.
- Prevent duplicate `(record_id, skill_id)` assignments.
- Preserve original title, salary text, source date values, skills string, and source provenance; source dates and salary values remain text until a separately reviewed normalization rule exists.
- Keep posting date distinct from source-updated date and from collection/import timestamps.
- Store missing optional values as `NULL`, not fabricated defaults.
- Do not compare salaries with incompatible currency or pay-period semantics.
- Treat listing activity as unknown unless an authoritative status check is recorded.
- Preserve the reviewed skill matching policies; do not use fuzzy synonym expansion or include pending-review terms in recommendations.

## Migrations, Local Path, and Access

- Ordered SQLite migrations live in `database/migrations/`; the runner records their versions and checksums in `schema_migrations`.
- The default database file is `data/processed/job_market.sqlite3`, covered by the repository's existing ignore rule.
- `JOP_DATABASE_PATH` may override the file path. It must be a local filesystem path, not a database URL.
- The loader writes through Python's standard-library `sqlite3` module and uses DuckDB only to read the local Parquet archive. It verifies package checksums and row counts, checks the source fingerprint, and requires `--replace` to replace a different local snapshot.
- Run `python scripts/database_loading/load_to_database.py check` to inspect migrations, row counts, and foreign-key integrity.
- No remote database credentials or server-side database service are part of this project configuration.

## Data and Licensing Constraints

The operational database is loaded from the complete checksum-verified archive; no partial sample is available as a load source. The local Parquet package remains under the existing ignored `data/processed/` path and can rebuild SQLite. Review source-use and redistribution terms before sharing job data or deploying a public product. SQLite loading does not verify external listing activity, resource availability, or data licensing.
