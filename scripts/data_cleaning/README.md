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

## Build the Neon Free upload profile

After the full processed exports and reference CSVs are available, run:

```bash
python scripts/data_cleaning/build_neon_free_dataset.py
```

This creates `jobs_neon_free.csv.gz`, `job_skills_neon_free.csv.gz`, `skill_observations_neon_free.csv.gz`, and `neon_free_quality_report.json` under `data/processed/neon_free/`. The default retains all 22,958 Arab-country job rows found in the available processed exports, every related job-skill row, and all 6,050 rows whose geography is blank, `Other/Unknown`, `Remote (Anywhere)`, or `Worldwide`. It also retains up to 5 named non-Arab rows per `(source_dataset, country)` stratum: 925 rows across 192 strata, covering all seven current source datasets. Sampling is deterministic and does not deduplicate across sources. Profile-specific skill observations are recalculated from the retained job-skill rows.

The builder adds new files only; it does not modify or replace the existing processed exports, raw files, or reference files. Its five-times-COPY-plus-fixed-overhead storage figure is a planning proxy, not a PostgreSQL or Neon measurement. The loader also enforces an 800 MB current-database size guard and reports relation, index, and TOAST sizes after loading; confirm the actual project quota and usage in Neon before considering the upload verified.

## Safety and interpretation rules

- Never edit or overwrite files in `data/raw/`.
- Do not label a record active: source exports do not verify listing status.
- Preserve `updated` separately; do not interpret it as posting or collection date without source documentation.
- Keep the International 2023 sample separate from the latest-export snapshots and other undated/semantically uncertain snapshots.
- Exact duplicates are flagged and retained; there is no cross-source deduplication.
- Retain raw salaries and their source/provenance. The staging builders do not convert currencies; the separate full-audit finalizer converts only under an explicit dated FX/pay-period policy. Never describe research-derived or synthetic salary ranges as employer-posted pay.
- Treat enriched skills as source/enrichment data, not independently verified requirements. `CAN`, `Flow`, and `Word` are explicitly excluded from matching until reviewed.
- Processed files remain Git-ignored by default. Only the new reduced Neon Free files are force-added to this PR under the earlier explicit request; existing full files remain unchanged. This scoped addition does not establish general redistribution rights, which remain unverified. The separate cleaned audit dataset also stays outside Git; only its scripts, final Markdown report, dictionary, and compact aggregate notebook inputs are tracked.

## Loss-preserving cleaning audit

The full audit has two stages. `build_cleaning_audit.py` writes `data/processed/jobs_cleaned_audited.csv.gz`, before/after quality inputs, salary review candidates, source checksums, and the audit notebook. It keeps every selected source row, embeds the original row in `source_row_json`, preserves raw salary/title/country/skill fields, and flags duplicate candidates, date anomalies, and salary outliers without deleting rows. `finalize_full_cleaning_audit.py` adds derived annual salary values and, when eligible references exist, explicitly labeled `Estimated/Synthetic` values for originally missing salaries. An estimate is not an employer-reported salary.

For the full run, the declared audit date was 2026-10-28 and all seven job sources were present (775,155 rows); three paired base exports were used only for skill comparison and not added as job rows. The International CSV was extracted from the user-requested Google Drive ZIP. Its recorded Drive modification date (2026-10-31) is later than the audit date and is documented as a provenance limitation, not treated as a posting or collection date. The raw snapshot used for this run was kept outside `data/raw/` so the partial checked-in raw folder was not replaced.

Salary amounts are annualized only when currency and pay period are explicit. The finalizer requires `data/reference/fx_rates_2026-10-28.json` to match the audit date and produces separate USD, EGP, and SAR values. Missing values may receive a synthetic estimate based on eligible actual source-reported references; all such records carry estimate status/method fields. Ambiguous currency, conflicting currency fields, and unknown periods remain flagged and are not guessed. `Actual` means reported in a source file, not independently verified against a live listing. The external project SQLite/Parquet reconciliation was not available; the in-memory SQLite round-trip is a separate check.

To reproduce a full run, restore all seven job sources and three base exports to a staging directory and pass the same source reference and date:

```bash
python scripts/data_cleaning/build_cleaning_audit.py \\
  --raw-data-directory /path/to/restored/data/raw \\
  --dataset-output data/processed/jobs_cleaned_audited.csv.gz \\
  --report-directory analysis/reports/data_cleaning \\
  --source-ref 'main@<commit>+GoogleDrive:International_Tech_Jobs_Filtered.zip' \\
  --as-of-date 2026-10-28 --require-all-sources
python scripts/data_cleaning/finalize_full_cleaning_audit.py \\
  --raw-data-directory /path/to/restored/data/raw \\
  --dataset data/processed/jobs_cleaned_audited.csv.gz \\
  --report-directory analysis/reports/data_cleaning \\
  --source-ref 'main@<commit>+GoogleDrive:International_Tech_Jobs_Filtered.zip' \\
  --as-of-date 2026-10-28 \\
  --fx-policy-file data/reference/fx_rates_2026-10-28.json
```

The completed artifacts include `analysis/notebooks/cleaning_data_audit.ipynb` and `analysis/reports/data_cleaning/final_data_quality_report.md`; detailed field definitions are in `docs/data/DATA_DICTIONARY.md`. The cleaned dataset is stored in the approved Google Drive folder and is excluded from Git; the report and reproducible code are intended to be tracked.
