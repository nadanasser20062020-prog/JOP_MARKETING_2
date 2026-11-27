# Data and Database Plan

## Current Status

The full `full_archive_parquet_v1_20261028` package is available locally under ignored `data/processed/`; its 775,155 jobs and 4,026,953 job-skill links are loaded into the default local SQLite database. Ordered migrations, checksum verification, import provenance, and integrity checks are implemented. This does not constitute a running frontend/backend application, and no external database is configured.

- [`docs/data/DATA_AUDIT.md`](data/DATA_AUDIT.md) records the source inventory, coverage, duplicates, and caveats.
- [`docs/data/DATA_DICTIONARY.md`](data/DATA_DICTIONARY.md) documents the normalized job, skill, and learning-resource schemas.
- [`scripts/data_cleaning/README.md`](../scripts/data_cleaning/README.md) documents the rebuild commands.

The International export is a historical 2023 sample for aggregate analysis. The latest Remote, Startup, and Jooble/Careerjet exports are separate snapshots whose advertisement status is unverified. The merged workbook, Arab-tech, and cybersecurity exports are kept in a third snapshot bucket because their date semantics do not establish a consistent historical range or live status. Do not merge these groups into a single “current jobs” feed without new source verification.

## Reproducible data stages

1. **Raw source:** Read unchanged, authorized source files from `data/raw/`; do not edit Drive originals.
2. **Staging:** Run `python scripts/data_cleaning/clean_all_data.py` from the repository root. It runs the builders in dependency order, creating three compressed job files, long-form job-skill assignments, frequency observations, a quality report, and refreshed reference catalogs. Generated job files remain under ignored `data/processed/`.
3. **Skill references:** The runner calls `scripts/data_cleaning/build_skill_reference.py` to rebuild the catalog and alias map from observed terms and the reviewed curation JSON.
4. **Learning resources:** The runner calls `scripts/data_cleaning/build_learning_resources.py` to validate skill references and produce the resource CSV.
5. **Database loading:** Place the checksum-verified full Parquet package under `data/processed/full_archive_parquet_v1_20261028/`, install `scripts/database_loading/requirements.txt`, and run `python scripts/database_loading/load_to_database.py load --source archive`. The loader imports the full dataset into local SQLite, records original source provenance, checks relationships, and never changes source files. Automatic mode prefers the archive and fails if it cannot find complete input data.
6. **Application:** Build search/filtering, analytics, skill matching, and learning recommendations against documented fields and the backend's local SQLite connection. Show source and verification caveats in the UI.

No output is imputed from missing values. Exact duplicate source rows are flagged and retained; no cross-source deduplication is attempted. Salary values and update dates are not normalized beyond the documented conservative handling.

## Implemented local relational model

The SQLite migration implements `data_sources`, `source_files`, `import_runs`, `import_run_files`, `jobs`, `skills`, `skill_aliases`, `job_skills`, `skill_observations`, `learning_resources`, `learning_resource_skills`, and `learning_resource_languages`. Keys and foreign-key rules are detailed in [`docs/software-engineering/PHYSICAL_SCHEMA_PROPOSAL.md`](software-engineering/PHYSICAL_SCHEMA_PROPOSAL.md).

The `jobs` table retains the original source fields for title, employer, country/location, dates, salary, skills, listing status, snapshot, and quality flags. Separate company or location tables are not introduced without evidence that a stable normalization rule is useful. Resource languages are retained as labels, not assumed ISO codes. Import history records source-file counts, pipeline version, and a fingerprint of local input files.

## Field and integrity rules

- `record_id` is a generated staging key, not a stable external job ID. Keep `source_record_id` separate and nullable.
- Keep `posted_at` separate from `source_updated_at`. Do not sort or filter mixed `updated` values as dates until their format and semantics are validated.
- Store listing state as unknown unless an authoritative source check provides it. Do not present the latest export bucket as verified active jobs.
- Never convert missing salary, company, country, or description to a default value. Preserve salary text and separate annual/hourly source fields; do not compare unlike currencies or pay periods.
- Research-derived or inferred salary ranges must be marked and must not be described as employer-published compensation.
- For skill matching, use only the policies in the reviewed reference data. No fuzzy synonym expansion; exclude ambiguous labels pending review. Keep whether a skill is base-source or enrichment-derived.
- Preserve duplicate source rows and their flags unless a separately reviewed deduplication method is approved.
- Learning-resource status must be attached to the specific page/course and include language, account, fee, and certificate uncertainty. Do not imply that an entire provider catalog is free because some offerings are.

## Audit and release gates

Before loading a new source refresh or publishing data:

1. Confirm the file list, schema, row counts, date range, and data-use/redistribution permission.
2. Re-run the data builder and inspect `data_quality_report.json`; compare row counts and missingness to the prior audit.
3. Review source-ID overlap, duplicate rows, and changes in skills and salary provenance.
4. Check whether source URLs resolve and whether any official listing-status indicator is available; until then, keep status unknown.
5. Verify the learning-resource links and course-specific access/language terms again before recommending them.
6. Ensure credentials and private source data are not committed or exposed in API responses.

The local schema, archive-provenance migration, full-archive Parquet loader, complete SQLite dataset, and integrity validation are implemented. The operational SQLite database contains all 775,155 jobs and 4,026,953 job-skill relationships, while preserving unknown listing status and unreviewed redistribution rights. The backend API/frontend are still planned.
