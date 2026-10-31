# Processed Site Data

This directory contains compressed, reproducible datasets generated from the unchanged files in `data/raw/`. Rebuild all job outputs and references from the repository root with:

```bash
python scripts/data_cleaning/clean_all_data.py
```

The current processed datasets are included in this branch by explicit approval. New or untracked generated files remain ignored by default.

The builder writes:

- `jobs_historical_2023_sample.csv.gz` — the International export only; its source posting dates are within 2023. Use as a historical sample for aggregate analysis, not as an active jobs feed.
- `jobs_latest_export_unverified.csv.gz` — selected enriched Remote, Startup, and Jooble/Careerjet exports. These are the latest export snapshots available in this workspace, but listing activity is not verified.
- `jobs_other_snapshots_unverified.csv.gz` — the merged workbook, Arab-tech sample, and cybersecurity sample. They are kept apart because their dates/source semantics do not establish that they are historical or active.
- `job_skills.csv.gz` — one row per job-skill assignment after source-specific parsing and exact duplicate-token removal. Includes source/enrichment provenance, skill IDs, categories, and matching policy.
- `skill_observations.csv.gz` — per-source skill labels and occurrence counts used to regenerate the skill catalog.
- `data_quality_report.json` — source row counts, missing-field counts, exact duplicates, skill-enrichment comparisons, salary-amount checks (non-disclosure text is not counted as an amount), output sizes, and processing policies.

All source rows are retained. The builder does not deduplicate across sources or remove exact duplicate rows. Every job row is marked `unknown_not_verified` for listing status. Skill matching should honor the `skill_match_policy` and provenance fields; do not match or recommend ambiguous terms pending review.

The raw source exports remain excluded from Git. The processed outputs currently committed here are a specifically approved exception; confirm redistribution rights before any production or broader public release. The `.gitignore` rule remains in place for new, untracked generated files.
