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
