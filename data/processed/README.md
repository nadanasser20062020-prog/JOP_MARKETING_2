# Processed Site Data

The existing full processed exports in this directory remain unchanged. The separate `neon_free/` folder contains a smaller upload profile built from those exports; it does not replace or rewrite any of the existing data files.

## Existing full processed exports

`build_site_data.py` writes the original full outputs when all required authorized raw sources are available:

- `jobs_historical_2023_sample.csv.gz` — the International export only; its source posting dates are within 2023. Use as a historical sample for aggregate analysis, not as an active-jobs feed.
- `jobs_latest_export_unverified.csv.gz` — selected enriched Remote, Startup, and Jooble/Careerjet exports. These are the latest export snapshots available in this workspace, but listing activity is not verified.
- `jobs_other_snapshots_unverified.csv.gz` — the merged workbook, Arab-tech sample, and cybersecurity sample. They remain separate because their date/source semantics do not establish that they are historical or active.
- `job_skills.csv.gz` — source-attributed job-skill assignments from the full exports.
- `skill_observations.csv.gz` — per-source skill labels and occurrence counts from the full exports.
- `data_quality_report.json` — source row counts, missing-field counts, duplicates, skill-enrichment comparisons, salary checks, output sizes, and processing policies.

These are the pre-existing artifacts; the Neon Free builder reads them but does not modify them. The raw International source file is not present in the current workspace, so a full rebuild requires obtaining that source through an authorized channel.

## Neon Free upload profile

Build the reduced profile from the existing processed exports and reference files with:

```bash
python scripts/data_cleaning/build_neon_free_dataset.py
```

The default selection retains every row whose country matches an Arab League member state or documented alias. From the currently available processed exports, that is 22,958 job rows, and all corresponding job-skill rows are kept. To avoid dropping possible Arab-region listings with missing or non-country geography, all 6,050 rows labeled blank, `Other/Unknown`, `Remote (Anywhere)`, or `Worldwide` are also retained in full. Named non-Arab rows are sampled deterministically with a maximum of 5 per `(source_dataset, country)` stratum; the current result contains 925 such rows across 192 strata, representing all seven source datasets. No cross-source deduplication is performed. The current profile contains 29,933 job rows and 256,549 job-skill rows, including all 194,673 job-skill rows associated with the country-labeled Arab jobs; its storage figure is a planning estimate, not a measured Neon size.

The builder adds these files under `neon_free/` without changing the existing full exports:

- `jobs_neon_free.csv.gz` — all retained Arab-country jobs plus the stratified non-Arab sample.
- `job_skills_neon_free.csv.gz` — every job-skill relationship for the selected jobs.
- `skill_observations_neon_free.csv.gz` — per-source skill counts recalculated from the selected job-skill rows.
- `neon_free_quality_report.json` — selection counts by country, source and stratum, file sizes, and an explicitly labeled planning-only storage estimate.

The loader uses this profile by default. To regenerate a larger non-Arab sample, pass `--maximum-non-arab-rows-per-source-country N` to the builder. New generated files remain ignored by the unchanged `.gitignore` rule; the reduced profile is force-added to this PR only under the user's explicit request. This scoped inclusion does not establish general redistribution rights. Confirm the applicable rights before any broader release or production use.

Every retained job row keeps `unknown_not_verified` listing status. The source data do not prove that a listing is currently active. The builder and loader do not alter raw Drive files.
