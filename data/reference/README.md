# Reference Data

Small, curated, source-attributed reference data used by job-skill matching and learning recommendations. Files are UTF-8; CSV fields containing multiple IDs or languages use semicolons.

## Skill taxonomy

- `skill_curation.json` is the reviewed source for curated canonical skill IDs, categories, aliases, matching policies, and review notes.
- `skill_catalog.csv` includes curated skills plus observed source terms. It is regenerated from `data/processed/skill_observations.csv.gz`.
- `skill_aliases.csv` maps normalized aliases to stable skill IDs. It is regenerated from the same observations and curation JSON.

Matching policy is deliberately conservative:

- `approved_aliases`: use only aliases explicitly listed in the curation JSON.
- `exact_only`: compare the casefolded, whitespace-collapsed label only; do not use fuzzy or semantic matching. Uncurated terms remain marked `needs_review`.
- `exclude_pending_review`: do not count as a match or recommend the term until the data owner resolves its meaning. This currently applies to `CAN`, `Flow`, and `Word`.

The normalizer preserves punctuation. It does not equate similar-but-distinct technologies such as Java and JavaScript, SQL and T-SQL, Spark and PySpark, or a generic REST label and REST API.

## Learning resources

- `learning_resources.json` is the curated source of resource metadata.
- `learning_resources.csv` is generated from the JSON and validated against curated skill IDs.

Each resource records skill links, language confidence, access/cost caveats, account and credential notes, official URL, verification status, and verification date. `cost_status` is one of `free_verified`, `some_free_options`, `conditional_or_mixed`, or `cost_unverified`. Only `free_verified` may be labelled free in recommendations; catalog-level statements do not prove that every course or lab is free. Course-specific language and enrollment conditions are marked unknown when not confirmed.

## Rebuild

```bash
python scripts/data_cleaning/build_skill_reference.py
python scripts/data_cleaning/build_learning_resources.py
```

The skill catalog and aliases can only be regenerated after `build_site_data.py` creates `data/processed/skill_observations.csv.gz`.
