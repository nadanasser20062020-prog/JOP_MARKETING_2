# SQL Analysis Queries

These read-only SQLite queries use the local `data/processed/job_market.sqlite3` database. They are analytic artifacts, not schema migrations. The profile driver in `analysis/generate_pre_backend_analysis.py` runs them and writes aggregate outputs under `analysis/reports/pre_backend/`.

Run from the repository root after the full archive has been loaded:

```bash
source .venv/bin/activate
python -m pip install -r analysis/requirements.txt
python analysis/generate_pre_backend_analysis.py
```

The queries preserve source rows and do not update SQLite. Skill metrics include only the consistent policy/status pairs `(approved_aliases, curated)` and `(exact_only, curated_exact_only)` on both `job_skills` and `skills`. An `exact_only` match policy alone is not sufficient: `needs_review` exact-only terms and `exclude_pending_review` terms are omitted. Query 14 reports the curation counts and exclusion split; denominators count records with at least one included reviewed skill. Query 15 enumerates the configured Arab-country labels actually present in the common-source comparison snapshot, so archive-wide and comparison-source absences are distinguished. The Arab-versus-other comparison is restricted to `merged_tech_jobs`, the archive source with both cohorts; the groups are the configured 22-name Arab-country set and remaining supplied country/territory labels within that source. This reduces source-mix confounding but does not resolve the source's unverified date semantics. `Remote (Anywhere)`, `Worldwide`, `Other/Unknown`, and blank locations are not treated as countries. The resource-verification query flags source dates after the archive build date; those values are not proof of current access or price.

The historical monthly query is restricted to `international_jobs` and its explicit 2023 `posted_at` values. The source-updated fields, mixed snapshots, and unverified listing status are not used as posting-date series. Salary fields are profiled separately; there is no salary aggregation across currencies, pay periods, or estimated values.
