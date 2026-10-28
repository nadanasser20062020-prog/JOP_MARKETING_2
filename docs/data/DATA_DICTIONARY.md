# Normalized Data Dictionary

- **Generated from:** `scripts/data_cleaning/build_site_data.py` for the staging exports, and `build_cleaning_audit.py` plus `finalize_full_cleaning_audit.py` for the separate loss-preserving audit dataset described below.
- **Interpretation rule:** raw/source fields are preserved. The staging exports do not impute values; the final audit may add a separately labeled synthetic salary estimate in dedicated derived columns, without overwriting original salary fields. No field establishes that a listing is active.

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

One row per retained job-to-canonical-skill assignment after parsing source-specific delimiters, removing repeated raw labels within a row, and collapsing reviewed aliases to one canonical ID per job. Unknown terms are preserved as exact-only IDs and marked `needs_review`; they remain in SQLite for audit but are not eligible for product metrics or matching until reviewed.

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

1. Resolve user-entered labels using `skill_aliases.csv` and return reviewed canonical IDs rather than raw text.
2. Include a link only when both `job_skills` and `skills` carry a consistent `(approved_aliases, curated)` or `(exact_only, curated_exact_only)` policy/status pair.
3. Use `approved_aliases` only for explicit aliases in `skill_curation.json`.
4. Use `exact_only` only for reviewed `curated_exact_only` terms with casefolded/whitespace-collapsed equality; do not guess synonyms.
5. Exclude all `needs_review`, `needs_owner_review`, and `exclude_pending_review` terms from product metrics and recommendations. An `exact_only` policy by itself does not mean a term has been approved.
6. Do not treat presence in a source or enrichment field as a verified job requirement.

## Reference catalogs

### `skill_catalog.csv`

Fields: `skill_id`, `canonical_name`, `category`, `match_policy`, `review_status`, `observed_alias_count`, `observed_source_count`, `observed_job_skill_occurrences`, `notes`. Occurrence counts are source-export appearances, not globally unique jobs.

### `skill_aliases.csv`

Fields: `alias_normalized`, `alias_label`, `skill_id`, `alias_type`, `match_policy`, `review_status`, `observed_source_count`, `observed_job_skill_occurrences`, `notes`. The normalization key folds case and whitespace only. Punctuation remains significant unless an explicit alias maps it.

### `learning_resources.csv`

Fields: `resource_id`, `title`, `provider`, `resource_type`, semicolon-separated `skill_ids`, semicolon-separated `languages`, `level`, `access_status`, `cost_status`, `account_requirement`, `credential`, `resource_url`, `verification_status`, `verified_on`, and `notes`. `cost_status` is `free_verified`, `some_free_options`, `conditional_or_mixed`, or `cost_unverified`; only `free_verified` qualifies for a free-only recommendation. Cost, language, account, and credential claims are intentionally scoped to the specific verified course/page; catalog-level availability is not generalized to every item.

## Quality report

`data/processed/data_quality_report.json` records counts by input source and bucket, missing-field counts, exact duplicate rows retained, raw/enriched skill comparisons, duplicate skill token removals, canonical skill-assignment duplicates suppressed, salary text without a numeric amount, output paths/sizes, and the policies used for dates, status, salaries, and deduplication.

## Loss-preserving cleaning audit dataset

`data/processed/jobs_cleaned_audited.csv.gz` is a separate, loss-preserving output from `scripts/data_cleaning/build_cleaning_audit.py`. It stores one row for each selected source row, including exact duplicates; it does not replace the older staging buckets. The complete original source row is serialized as JSON in `source_row_json`, and the raw source files remain unchanged. The run report, before/after coverage, field-level salary review list, and analysis tables live under `analysis/reports/data_cleaning/`.

The current generated snapshot uses all seven declared job-source files: the six files available in `main@6755883a8c043592d349cace4cd84aaae81d73d0` plus `International_Tech_Jobs_Filtered.csv`, extracted from the user-requested Google Drive ZIP. It contains 775,155 rows with zero job-source rows dropped; three base exports were read only for skill comparisons. Drive reports the ZIP modified on 2026-10-31, later than the 2026-10-28 audit date, and this provenance discrepancy is documented. The project SQLite database and full Parquet archive package remain unavailable, so this run does not validate them.

### Identity, text, location, and dates

| Field | Meaning |
|---|---|
| `record_id` | Deterministic per-source-row key using dataset, source identifier (or row fallback), row number, and source-row digest; duplicate rows remain distinct. |
| `source_dataset`, `source_file`, `source_row_number`, `source_record_id` | Source provenance; row number is one-based and excludes the header. |
| `source_record_id_duplicate_occurrence`, `exact_duplicate_within_source` | Duplicate occurrence flags; records are retained. |
| `title_raw`, `company_raw`, `country_raw`, `description_raw`, `skills_raw`, `source_url_raw` | Source values, kept separately from derived values. All source columns are also kept in `source_row_json`. |
| `title_clean`, `company_clean` | Whitespace-normalized derived values. No fuzzy title taxonomy or synonym merging is applied. |
| `title_key` | Casefolded, whitespace-normalized exact-title key; punctuation and wording remain significant. |
| `country_standardized` | Conservative exact alias mapping only. Unknown/placeholders can remain blank here while their source text remains in `country_raw`/`source_row_json`. |
| `location_scope` | Separates country labels from `Worldwide`, `Remote (Anywhere)`, and missing/unknown scope; it does not validate geography. |
| `experience_raw`, `experience_years_min`, `experience_years_max`, `experience_parse_status` | Original level/experience label plus a transparent parse of explicit year ranges/lower bounds only. No seniority is inferred from title text. |
| `posted_at_raw`, `posted_at_iso` | Explicit posting-date fields only, with a parsed UTC ISO form when parseable. `updated` is never promoted to a posting date. |
| `source_updated_at_raw`, `source_updated_at_iso`, `source_date_field`, `date_quality_flags` | Source update field kept separately, with parsed value and review flags. Old/future values are flagged, not deleted. |
| `encoding_suspected_mojibake` | Possible text-encoding issue; raw text is retained and not automatically repaired. |

### Salary fields and policy

| Field | Meaning |
|---|---|
| `salary_raw` | Original `salary`/`salary_raw` text; non-disclosure text is retained. |
| `salary_candidate_raw`, `salary_source_field_used` | Source field used for conservative parsing, which may be a separate pre-existing range/aggregate field when raw posting text is absent. |
| `salary_local_source_value`, `salary_usd_source_value`, `salary_range_est_source_value` | Original source-native or legacy derived values, preserved as text. Existing `salary_usd` conversions are not trusted or used as FX conversions without a dated rate. |
| `salary_currency_raw`, `salary_currency_code`, `salary_currency_detection_status` | Original currency field, detected ISO code, and whether the code was explicit in the text/column, ambiguous, or conflicting. `$` alone is not resolved from country. |
| `salary_period_code`, `salary_period_detection_status` | Explicit `YEAR`, `MONTH`, `WEEK`, `DAY`, `HOUR`, or `UNKNOWN`; conflicting/missing period text is not guessed. |
| `salary_amount_1_original_currency`, `salary_amount_2_original_currency` | Parsed amount endpoint(s) in source order and native currency. A reversed range is retained and flagged. |
| `salary_min_original_currency`, `salary_max_original_currency`, `salary_midpoint_original_currency` | Parsed endpoints and arithmetic midpoint; single values are represented as equal endpoints. They do not change the original salary text. |
| `salary_value_type`, `salary_provenance_status` | Before finalization, values include `actual_reported`, `estimated_legacy_unverified`, `source_reported_unverified`, `not_disclosed`, `missing`, or `unparseable_or_no_numeric_amount`. The finalizer may change only an originally `missing` value to `estimated_synthetic`; `salary_source_value_type` retains the original classification. “Actual” means reported in a source row, not independently checked against a live listing. |
| `salary_source_raw`, `salary_sources_raw`, `salary_fill_source_raw`, `salary_estimate_source_url`, `salary_estimate_source_date`, `salary_estimate_source_date_status` | Original source and fill-provenance text/URL. Legacy estimate source dates absent from the input remain blank and are explicitly marked missing. |
| `salary_annualized_*_native` | Native-currency annual amount. A `YEAR` amount is copied unchanged; another period is annualized only when it is explicitly identified and an approved policy supplies its factor. Unknown or ambiguous periods remain unannualized. |
| `salary_reporting_currency`, `salary_fx_rate_to_reporting_currency`, `salary_fx_rate_source`, `salary_fx_rate_date`, `salary_annualized_*_reporting_currency` | Derived only under a dated, source-attributed FX policy. The completed finalization uses the frozen `data/reference/fx_rates_2026-10-28.json` policy and reports separate USD, EGP, and SAR columns; missing or conflicting currency is not inferred. |
| `salary_comparability_status`, `salary_statistics_eligible` | Eligibility for actual-only grouped statistics. Currency and pay period must be explicit and nonconflicting; unverified estimates and records triggering the broad period-scale review screen are excluded pending review. |
| `salary_integrity_flags`, `salary_iqr_outlier_flag` | Manual-review flags for source conflicts, invalid range/amount, broad-scale checks, or IQR outliers. Flags never delete or silently exclude a source row. |

`salary_statistics_actual.csv` groups source-reported actual rows by exact normalized title, country/scope, explicit currency, and explicit pay period; it does not mix synthetic estimates or currencies. `annual_salary_statistics_actual.csv` reports actual-only annualized values in USD, EGP, and SAR under the dated policy. The finalizer adds the dedicated fields below for explicit annualization and separately labeled estimates. `salary_review_candidates.csv` lists rows needing manual review; `legacy_salary_estimate_inventory.csv` inventories pre-existing estimates without treating them as verified salary benchmarks.

#### Finalizer-only annualized and synthetic estimate fields

| Field | Meaning |
|---|---|
| `salary_original`, `salary_source_value_type` | Preserve the source salary text and its pre-finalization classification. Synthetic estimates do not replace either field. |
| `salary_estimation_status`, `salary_estimation_method`, `salary_estimation_source` | Final salary status plus the explicit derivation tier and provenance. `Estimated`/`synthetic_*` indicates a model-derived value, not employer-reported pay or an external salary source. |
| `salary_estimation_confidence`, `salary_estimate_reference_count`, `salary_estimation_as_of_date` | Confidence label, number of eligible actual reference records, and the date of the policy/run used for the estimate. |
| `salary_annual_min_usd`, `salary_annual_salary_usd`, `salary_annual_max_usd` (and corresponding `_egp`/`_sar` fields) | Derived annual low/midpoint/high values in each output currency. For synthetic estimates, the low/high endpoints are the reference group's Q1/Q3 spread, not an advertised pay range. |
| `salary_annualized_midpoint_reporting_currency`, `salary_estimate_currency_code`, `salary_estimate_range_basis` | Reporting-currency midpoint and estimate-only currency/range explanation. The report's primary reporting currency is USD; EGP and SAR are parallel outputs. |

Only eligible source-reported actual salaries with explicit, nonconflicting currency and period train the reference medians; synthetic and legacy estimates are excluded. Missing salaries may be estimated from those references and remain clearly labeled. `Not disclosed`, unparseable values, ambiguous currency, and unknown pay periods are not guessed or filled. The model is descriptive of this dataset, not a labor-market forecast.

### Skills and source-row preservation

- `skills_base_raw` and `skills_enrichment_status` compare paired Remote/Startup/Jooble-Careerjet rows with their base export when IDs are unique; other rows or unavailable pairs are labeled explicitly.
- `skills_tokens_json` contains source-aware parsed unique labels; `skill_ids_json` contains stable curated/exact-only IDs using `data/reference/skill_curation.json`.
- `skill_token_count_raw`, `skill_token_count_unique`, `skill_canonical_id_count`, and `skill_duplicate_token_count` expose parsing/dedup effects. `skills_raw` and the full original row remain available.
- `data_quality_flags` is a semicolon-separated row-level list of missing fields, source/encoding/date/salary issues, and duplicate markers. It is review metadata, not a row-removal rule.

### Cleaning audit outputs

- `analysis/reports/data_cleaning/final_data_quality_report.md`: scope, decisions, limitations, and headline results.
- `analysis/reports/data_cleaning/cleaning_summary.json`, `data_quality_before.json`, and `data_quality_after.json`: run metadata, source coverage, and normalized coverage.
- `analysis/reports/data_cleaning/missingness_impact.csv`, `cleaned_column_type_audit.csv`, and `field_consistency_checks.csv`: compact aggregate checks used by the notebook.
- `analysis/reports/data_cleaning/raw_source_column_coverage.csv`, `cleaned_column_coverage.csv`, and `field_coverage_comparison.csv`: source/derived field-coverage aggregates.
- `analysis/reports/data_cleaning/source_manifest.csv`: source revision, file sizes, and SHA-256 hashes.
- `analysis/reports/data_cleaning/salary_coverage_by_role_country.csv`: salary-type and comparability coverage for each exact title/country group.
- `analysis/reports/data_cleaning/salary_statistics_actual.csv`: actual-reported statistics only.
- `analysis/reports/data_cleaning/legacy_salary_estimate_inventory.csv`: unverified pre-existing estimate provenance counts.
- `analysis/reports/data_cleaning/salary_review_candidates.csv`: row-level queue for ambiguous/unverified salary values, source/period/currency issues, parse failures, and review flags.
- `analysis/notebooks/cleaning_data_audit.ipynb`: standard-library notebook that checks the compact saved report summaries and, when the Drive-hosted processed file is restored locally, can stream-validate its row count without loading it all into memory.

Git tracks the final Markdown report plus the compact notebook inputs listed above: the run summary, before/after quality JSON, missingness/type/consistency summaries, field-coverage aggregates, and source manifest. The cleaned dataset, raw sources, row-level salary-review candidates, change log, and remaining generated tables are not committed; restore approved data from Drive or regenerate the full reports from the cleaning scripts and authorized source files.
