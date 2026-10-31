# Data and Database Plan

## Current Status

The raw-file audit and first reproducible data-preparation pass are complete. The repository contains a standard-library Python builder and documentation; generated job datasets remain in the ignored `data/processed/` directory. This does not constitute a running frontend or backend.

- [`docs/data/DATA_AUDIT.md`](data/DATA_AUDIT.md) records the source inventory, coverage, duplicates, and caveats.
- [`docs/data/DATA_DICTIONARY.md`](data/DATA_DICTIONARY.md) documents the normalized job, skill, and learning-resource schemas.
- [`scripts/data_cleaning/README.md`](../scripts/data_cleaning/README.md) documents the rebuild commands.

The International export is a historical 2023 sample for aggregate analysis. The latest Remote, Startup, and Jooble/Careerjet exports are separate snapshots whose advertisement status is unverified. The merged workbook, Arab-tech, and cybersecurity exports are kept in a third snapshot bucket because their date semantics do not establish a consistent historical range or live status. Do not merge these groups into a single “current jobs” feed without new source verification.

## Reproducible data stages

1. **Raw source:** Read unchanged, authorized source files from `data/raw/`; do not edit Drive originals.
2. **Staging:** Run `python scripts/data_cleaning/clean_all_data.py` from the repository root. It runs the builders in dependency order, creating three compressed job files, long-form job-skill assignments, frequency observations, a quality report, and refreshed reference catalogs. Generated job files remain under ignored `data/processed/`.
3. **Skill references:** The runner calls `scripts/data_cleaning/build_skill_reference.py` to rebuild the catalog and alias map from observed terms and the reviewed curation JSON.
4. **Learning resources:** The runner calls `scripts/data_cleaning/build_learning_resources.py` to validate skill references and produce the resource CSV.
5. **Database loading:** Load only after checking the latest quality report and confirming data publication permissions. Keep source buckets and provenance fields.
6. **Application:** Build search/filtering, analytics, skill matching, and learning recommendations against documented fields. Show source and verification caveats in the UI.

No output is imputed from missing values. Exact duplicate source rows are flagged and retained; no cross-source deduplication is attempted. Salary values and update dates are not normalized beyond the documented conservative handling.

## Relational model proposal

Implement or adapt these entities after reviewing the actual database choice and query patterns:

- **Job Posts:** `record_id` primary key; source dataset/file/row; upstream source ID; original title, company, description, location, work arrangement, employment type, experience, category, source date values, raw salary values and provenance, URL, listing status, snapshot bucket, and quality flags.
- **Skills:** `skill_id` primary key; canonical name, category, match policy, review status, and curation notes.
- **Skill Aliases:** normalized alias key, label, skill foreign key, alias type, and review/match policy.
- **Job Skills:** one row per job-skill assignment, with job and skill foreign keys plus source skill label and provenance status.
- **Learning Resources:** resource ID, provider, title, type, language, level, URL, access/cost caveat, credential note, verification status/date, and notes.
- **Job Sources / Dataset Runs:** source dataset, source file, bucket, audit date, counts, and transformation version. Use these to retain provenance and track rebuilds.

Company and location dimension tables may be added when there is a demonstrated need; source values remain nullable and are not forcibly normalized. Keep the raw source strings even if a later canonical display field is introduced.

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

The current schema is a data-loading proposal, not a completed database implementation or production ingestion service.
