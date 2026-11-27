# Processed Site Data

Generated, compressed datasets are kept in this Git-ignored directory. The current cleaning audit includes all seven declared job sources (775,155 rows), including the International CSV extracted from the user-requested Drive ZIP; see `analysis/reports/data_cleaning/`. Generated files remain local rather than tracked. The operational application database `job_market.sqlite3` and full Parquet archive package are not present in this checkout; a separate cleaned-audit database, `jobs_cleaned_audited.sqlite3`, has been built locally. Restore the archive package before rerunning analytics/API operations that depend on `job_market.sqlite3`. To rebuild the CSV staging outputs, place the authorized raw sources under `data/raw/` and run:

```bash
python scripts/data_cleaning/build_site_data.py
```

The builder writes:

- `jobs_historical_2023_sample.csv.gz` — the International export only; its source posting dates are within 2023. Use as a historical sample for aggregate analysis, not as an active jobs feed.
- `jobs_latest_export_unverified.csv.gz` — selected enriched Remote, Startup, and Jooble/Careerjet exports. These are the latest export snapshots available in this workspace, but listing activity is not verified.
- `jobs_other_snapshots_unverified.csv.gz` — the merged workbook, Arab-tech sample, and cybersecurity sample. They are kept apart because their dates/source semantics do not establish that they are historical or active.
- `job_skills.csv.gz` — one row per job-skill assignment after source-specific parsing and exact duplicate-token removal. Includes source/enrichment provenance, skill IDs, categories, and matching policy.
- `skill_observations.csv.gz` — per-source skill labels and occurrence counts used to regenerate the skill catalog.
- `data_quality_report.json` — source row counts, missing-field counts, exact duplicates, skill-enrichment comparisons, salary-amount checks (non-disclosure text is not counted as an amount), output sizes, and processing policies.

All source rows are retained. The builder does not deduplicate across sources or remove exact duplicate rows. Every job row is marked `unknown_not_verified` for listing status. Skill analytics/matching should include only consistent `(approved_aliases, curated)` and `(exact_only, curated_exact_only)` pairs from the link and catalog tables. Preserve, but exclude, `needs_review`, `needs_owner_review`, policy/status mismatches, and `exclude_pending_review` terms.

These generated files are ignored by Git because the raw source exports are also excluded. Keep processed data local or in approved storage, and do not share it without confirming redistribution permissions.

## Full Local SQLite Database

The complete archive package `full_archive_parquet_v1_20261028/` contains all 775,155 job rows, 4,026,953 job-skill links, reference tables, and source-import metadata. In the last full-data validation run, all package files passed `checksums.sha256`, and the local database loaded from this archive passed migrations 001–005 with zero foreign-key violations. The archive and database are ignored local files, not source-control deliverables; neither is present in the current snapshot. Restore the package from the approved preserved copy into this directory, verify its checksums, and rebuild the local database before repeating those checks.

Install the Parquet reader and load the full archive with:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r scripts/database_loading/requirements.txt
python scripts/database_loading/load_to_database.py load --source archive
python scripts/database_loading/load_to_database.py check
```

The database defaults to `data/processed/job_market.sqlite3`. Automatic mode prefers the verified full archive and does not fall back to the test seed. If this directory is restored from a fresh checkout, download the complete archive package from the preserved Drive folder into `full_archive_parquet_v1_20261028/` before loading. The database, archive package, and SQLite sidecars remain covered by the existing `/data/processed/*` ignore rule.

## Loss-preserving cleaning audit output

The separate `build_cleaning_audit.py` pipeline writes `jobs_cleaned_audited.csv.gz` here. It retains every selected source row, embeds the full original row in `source_row_json`, and adds conservative normalized fields, salary provenance/parse fields, review flags, and explicit comparability eligibility. The file is generated locally and remains ignored by Git. Its reproducibility reports, salary tables, and notebook are under `analysis/reports/data_cleaning/` and `analysis/notebooks/`.

The current audited dataset contains 775,155 rows from all seven declared job sources: the six available files in `main@6755883a8c043592d349cace4cd84aaae81d73d0` plus `International_Tech_Jobs_Filtered.csv`, extracted from the user-requested Google Drive ZIP. The Drive-reported modified date (2026-10-31) is later than the audit date (2026-10-28); the archive was included at the user's direction and the timestamp discrepancy is documented. No estimates were added, pre-existing unverified salary estimates are excluded from actual-only statistics, and no FX conversion or non-year annualization was applied. The operational `job_market.sqlite3` comparison remains unavailable, but the separate cleaned-audit SQLite file below was built and validated.

## Cleaned-audit relational SQLite output

`jobs_cleaned_audited.sqlite3` is the separate full-fidelity relational database generated from the complete Drive cleaned CSV. It contains 775,155 `jobs` rows and 775,155 `job_cleaning_audit` rows; the audit table stores all 123 CSV columns and each source row's JSON. It also contains 4,026,953 `job_skills` links, 1,498 catalog skills, source provenance, and the normalized reference tables and API rollups. The completed import reported **zero foreign-key violations** and `PRAGMA integrity_check = ok`; its file size is about 7.65 GB. It does not replace the application database `job_market.sqlite3`.

The Drive copy has SHA-256 `6f53340a00a17f4a6d86087a6bf6d98a4fce1a1bb79b795b6237f87fd927fd72`, matching `analysis/reports/data_cleaning/cleaning_summary.json`. The builder checks the CSV against that summary before importing. To rebuild from the same Drive snapshot after restoring the CSV and summary, run:

```bash
python scripts/database_loading/build_cleaned_relational_sqlite.py
```

The generated database and CSV are covered by `/data/processed/*` and are intentionally not tracked in Git. The matching ERD and schema details are in [`docs/diagrams/22_CLEANED_AUDIT_RELATIONAL_ERD.md`](../../docs/diagrams/22_CLEANED_AUDIT_RELATIONAL_ERD.md).
