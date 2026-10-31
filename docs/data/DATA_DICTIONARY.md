# Normalized Data Dictionary

- **Generated from:** `scripts/data_cleaning/build_site_data.py` and the raw files listed in [`DATA_AUDIT.md`](DATA_AUDIT.md).
- **Interpretation rule:** source values are preserved; missing values are not filled; no field establishes that a listing is active.

## Job export files

Each of the three `jobs_*.csv.gz` files shares the following schema. CSV values are emitted as text; blank means unavailable in the source or not mapped.

| Field | Meaning / source rule |
|---|---|
| `record_id` | Staging key composed from source dataset, source row number, and a digest of source-row content. Keeps exact duplicate rows distinct. Not an upstream job ID. |
| `source_dataset` | Stable dataset label, such as `international_jobs`, `remote_tech_jobs`, or `jooble_careerjet_jobs`. |
| `source_file` | Original source filename used for the row. |
| `source_row_number` | One-based row number in the selected source file (excluding its header). |
| `source_record_id` | Original `id`, `job_id`, or `row_id` when supplied; otherwise blank. |
| `record_origin` | Source `record_origin` or `source_file` value when supplied. |
| `source_platform` | Source/platform/`job_via` field when available; a leading `via ` is removed, but the value is otherwise not normalized. |
| `title` | Source title or job title. If missing, falls back to `job_title_short`. |
| `title_short` | Source `job_title_short`, when provided. |
| `company` | Source `company` or `company_name`. |
| `country` | Source `country` or `job_country`. |
| `city` | Source city value, when present. |
| `region` | First available source `state_region`, `region`, or `state`. |
| `location_raw` | Original location text from supported source location fields. |
| `work_mode_raw` | Original work-mode text; when only `job_work_from_home` exists, stored as `job_work_from_home=<source value>`. Not a standardized work-mode classification. |
| `remote_flag` | Original `job_work_from_home` value, when supplied. |
| `employment_type_raw` | First available source `job_type`, `job_schedule_type`, or `employment_type`. |
| `experience_raw` | First available source `level`, `years_experience`, or `experience`. |
| `category_raw` | First available source category/track field. Not mapped to a canonical role taxonomy. |
| `description` | Original source description, when available. No description is synthesized. |
| `posted_at` | Only explicit `posted_at`, `job_posted_date`, or `date_posted`. Dates are preserved as text and are not parsed into a unified timestamp. |
| `source_updated_at` | Source `updated` or `source_updated_at`, preserved separately. This is not assumed to be a posting date or collection time. |
| `source_date_field` | `posted_at_or_job_posted_date`, `updated_semantics_unverified`, or `not_available`; describes which source field was used. |
| `salary_raw` | Original `salary` or `salary_raw` text. Non-disclosure text is kept even when no numeric amount exists. |
| `salary_rate` | Source rate field where present. No conversion or inference. |
| `salary_year_avg` | Source annual-average value when present. Kept as text. |
| `salary_hour_avg` | Source hourly-average value when present. Kept as text. |
| `salary_currency` | Source currency value when supplied; not inferred from country or text. |
| `salary_basis` | Source basis/period/rate field when present. No period conversion. |
| `salary_source` | Source salary-provenance text, including research or benchmark notes when supplied. |
| `salary_provenance_status` | `estimate_or_research_indicated`, `source_or_origin_unverified`, or `not_available`. A non-disclosure string is not a numeric salary amount. |
| `skills` | Original skill-list string from the selected source row. |
| `skills_original` | Skill-list string from the base/raw paired export when available; otherwise equals the selected source list or is blank if no base row matched. |
| `skills_source` | Explicit source skill provenance when provided; otherwise a conservative staging label. It is row-level metadata, not attribution for each individual skill. |
| `skills_enrichment_status` | `not_compared`, `matches_source_version`, `changed_source_version_unverified`, or `base_row_not_found_or_id_missing`. |
| `source_url` | First available source link/apply URL/job URL. Link availability is recorded; link reachability is not tested. |
| `listing_status` | Always `unknown_not_verified` for current outputs. |
| `snapshot_type` | Source bucket/status label; does not claim an advertisement is active. |
| `exact_duplicate_within_source` | `yes` or `no`, based on exact source-row equality within one input file. Duplicate rows are retained. |
| `data_quality_flags` | Semicolon-separated flags, including missing fields, unverified date semantics, unverified listing activity, unverified skill enrichment, salary-estimate warnings, and exact duplicates. |

## `job_skills.csv.gz`

One row per retained job-to-canonical-skill assignment after parsing source-specific delimiters, removing repeated raw labels within a row, and collapsing reviewed aliases to one canonical ID per job. Unknown terms are preserved as exact-only IDs.

| Field | Meaning |
|---|---|
| `record_id` | Foreign key to one of the job export files. |
| `source_dataset`, `source_file` | Source provenance copied from the job row. |
| `skill_raw` | First source label retained for this canonical assignment. The original full skill string remains on the job row. |
| `skill_normalized` | Casefolded, whitespace-collapsed label; punctuation is preserved. |
| `skill_id` | Curated canonical skill ID or stable `term:<hash>` ID for an uncurated source term. |
| `skill_category` | Curated category, or `uncategorized` for terms awaiting review. |
| `skill_match_policy` | `approved_aliases`, `exact_only`, or `exclude_pending_review`. Do not use fuzzy matching. |
| `skill_review_status` | Curation state, for example `curated`, `curated_exact_only`, `needs_review`, or `needs_owner_review`. |
| `skill_provenance` | Row-level source provenance text; individual additions may not be distinguishable in mixed rows. |
| `skill_status` | `present_in_base_export`, `added_in_enriched_export_provenance_unverified`, row-level source-provenance labels, or `source_field_provenance_not_supplied`. |

### Skill matching rules

1. Resolve user-entered labels using `skill_aliases.csv`.
2. Use `approved_aliases` only for explicit aliases in `skill_curation.json`.
3. Use `exact_only` only for casefolded/whitespace-collapsed equality; do not guess synonyms.
4. Exclude `exclude_pending_review` from matching and recommendations.
5. Do not treat presence in a source or enrichment field as a verified job requirement.

## Reference catalogs

### `skill_catalog.csv`

Fields: `skill_id`, `canonical_name`, `category`, `match_policy`, `review_status`, `observed_alias_count`, `observed_source_count`, `observed_job_skill_occurrences`, `notes`. Occurrence counts are source-export appearances, not globally unique jobs.

### `skill_aliases.csv`

Fields: `alias_normalized`, `alias_label`, `skill_id`, `alias_type`, `match_policy`, `review_status`, `observed_source_count`, `observed_job_skill_occurrences`, `notes`. The normalization key folds case and whitespace only. Punctuation remains significant unless an explicit alias maps it.

### `learning_resources.csv`

Fields: `resource_id`, `title`, `provider`, `resource_type`, semicolon-separated `skill_ids`, semicolon-separated `languages`, `level`, `access_status`, `cost_status`, `account_requirement`, `credential`, `resource_url`, `verification_status`, `verified_on`, and `notes`. `cost_status` is `free_verified`, `some_free_options`, `conditional_or_mixed`, or `cost_unverified`; only `free_verified` qualifies for a free-only recommendation. Cost, language, account, and credential claims are intentionally scoped to the specific verified course/page; catalog-level availability is not generalized to every item.

## Quality report

`data/processed/data_quality_report.json` records counts by input source and bucket, missing-field counts, exact duplicate rows retained, raw/enriched skill comparisons, duplicate skill token removals, canonical skill-assignment duplicates suppressed, salary text without a numeric amount, output paths/sizes, and the policies used for dates, status, salaries, and deduplication.
