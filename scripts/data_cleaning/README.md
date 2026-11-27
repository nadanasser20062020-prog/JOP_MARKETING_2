# Data Preparation Scripts

These scripts read unchanged files from `data/raw/` and write derived artifacts to the ignored `data/processed/` directory. They use only the Python standard library.

## Rebuild all available data

The cleaning folder is `scripts/data_cleaning/`. From the repository root, run its comment-free entry point after the raw exports are present:

```bash
python scripts/data_cleaning/clean_all_data.py
```

The entry point runs the individual builders in dependency order. To run them separately:

```bash
python scripts/data_cleaning/build_site_data.py
python scripts/data_cleaning/build_skill_reference.py
python scripts/data_cleaning/build_learning_resources.py
```

`build_site_data.py` writes three intentionally separate job buckets, a normalized long-form job-skill table, skill-frequency observations, and a JSON data-quality report. It selects the after-adding-skills versions for Remote, Startup, and Jooble/Careerjet; it does not add their raw/base copies as extra jobs. The source IDs are compared so added skills can be identified as changed from the base export, but their correctness is not independently verified.

`build_skill_reference.py` reads the generated skill observations and the reviewed `data/reference/skill_curation.json`. It creates `skill_catalog.csv` and `skill_aliases.csv`; uncategorized observed terms remain exact-only and marked for review. Alias normalization is intentionally conservative: casefold and collapse whitespace only, with no fuzzy matching.

`build_learning_resources.py` validates the curated JSON resource list against the skill IDs and writes `data/reference/learning_resources.csv`.

## Safety and interpretation rules

- Never edit or overwrite files in `data/raw/`.
- Do not label a record active: source exports do not verify listing status.
- Preserve `updated` separately; do not interpret it as posting or collection date without source documentation.
- Keep the International 2023 sample separate from the latest-export snapshots and other undated/semantically uncertain snapshots.
- Exact duplicates are flagged and retained; there is no cross-source deduplication.
- Retain raw salaries and their source/provenance. Do not convert currencies or describe research-derived salary ranges as employer-posted pay.
- Treat enriched skills as source/enrichment data, not independently verified requirements. `CAN`, `Flow`, and `Word` are explicitly excluded from matching until reviewed.
- Processed files remain excluded from Git; the reports and scripts are reproducible from the authorized local raw files.

## Loss-preserving cleaning audit

`build_cleaning_audit.py` is the separate, instructor-ready Python cleaning pipeline. It writes `data/processed/jobs_cleaned_audited.csv.gz`, before/after quality JSON, salary coverage/statistics/review tables, source checksums, and a notebook. It keeps every source row and embeds the original row JSON; exact duplicates, date anomalies, and salary outliers are flagged, never deleted. Existing estimates are preserved but labeled unverified and excluded from actual-salary statistics. No missing salary is filled.

Run it after all declared inputs are available:

```bash
python scripts/data_cleaning/build_cleaning_audit.py \\
  --raw-data-directory data/raw \\
  --source-ref "main@<commit>"
```

If a source is absent, the default run generates an explicitly partial result and lists the missing file; pass `--require-all-sources` to fail instead. The completed audit run used all seven declared job sources (775,155 rows): six files from the read-only `main@6755883a8c043592d349cace4cd84aaae81d73d0` archive and `International_Tech_Jobs_Filtered.csv` extracted from the user-requested Google Drive ZIP. The Drive ZIP's reported modified date is 2026-10-31, later than the 2026-10-28 audit date; it was included at the user's explicit direction, and that timestamp discrepancy should remain in provenance. Three paired base exports were read only for skill comparisons and were not added as job rows. The workspace still lacks `job_market.sqlite3` and the full Parquet package, so no comparison to those archived database artifacts was possible.

Currency conversion and non-year annualization require an explicit approved JSON policy via `--salary-policy-file`; no exchange rate or hourly/daily/weekly/monthly annualization default is assumed. A yearly source amount may be carried through unchanged as an annual amount. See `docs/data/DATA_DICTIONARY.md` and `analysis/reports/data_cleaning/final_data_quality_report.md` for field meanings and limitations.
