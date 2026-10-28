# Job Data Audit

## Current loss-preserving cleaning run

- **Audit date:** 2026-10-28.
- **Scope:** all seven declared job-source files, **775,155 rows** total; all input rows were retained and zero rows dropped. Three base exports were read only for skill-enrichment comparisons, not added as job rows.
- **Report:** [`analysis/reports/data_cleaning/final_data_quality_report.md`](../../analysis/reports/data_cleaning/final_data_quality_report.md).
- **Source reference:** `main@6755883a8c043592d349cace4cd84aaae81d73d0` plus the user-requested `International_Tech_Jobs_Filtered.zip` from Google Drive. The source manifest records per-file hashes and sizes; all ten input files remained unchanged during processing.
- **Drive archive provenance:** the ZIP was 42,435,058 bytes (SHA-256 `24f19dd3528757db92310c1f5fde008d2e2e8d1b8ec31efbff441d5462292309`); it contained one CSV of 210,070,595 bytes (SHA-256 `1c168e124207d28992ebe790812d07df2e4fd117e2dc013713ecf4e7c38fed7a`). Drive reports the ZIP modified on 2026-10-31, later than the 2026-10-28 audit date; it was included at the user's explicit direction, and the timestamp discrepancy is retained as a provenance caveat.
- **Database limitation:** the project `job_market.sqlite3` and full Parquet package are not in this checkout. The in-memory SQLite round trip validates the generated CSV salary aggregates only; it is not a comparison to those archived artifacts.

## Prior staging audit snapshot (date recorded as 2026-10-31; unverified)

The inventory below is preserved from an earlier staging/validation report. Its historical totals are not a replacement for the current cleaning report above.

- **Previous rebuild command:** `python scripts/data_cleaning/build_site_data.py`

### Dataset boundaries

The staging output deliberately has three job buckets. “Latest export” means the newest available export snapshot in this workspace—not proof that an advertisement is still active.

| Output | Source scope | Rows | Intended use | Important limitation |
|---|---|---:|---|---|
| `jobs_historical_2023_sample.csv.gz` | `International_Tech_Jobs_Filtered.csv` | 705,866 | Historical, aggregate analytics | Source posting dates are within 2023; descriptions and application URLs are absent. Not a live jobs feed. |
| `jobs_latest_export_unverified.csv.gz` | Selected enriched Remote, Startup, and Jooble/Careerjet exports | 23,201 | Job discovery/search prototype, only with a visible unverified-status warning | `updated` is preserved but its meaning is not established; source exports do not prove that a listing remains open. |
| `jobs_other_snapshots_unverified.csv.gz` | Merged Excel workbook, Arab-tech sample, cybersecurity sample | 46,088 | Additional searchable/analytical snapshots, subject to their row-level limitations | The sources do not establish a consistent historical period or current listing status. Keep these apart from the historical sample and latest exports. |

The selected total is 775,155 rows. Raw and after-adding-skills copies of Remote, Startup, and Jooble/Careerjet are paired versions of the same postings, not additional job sets. Only the enriched copy is exported as a job row; the raw copy is read to compare skills. No cross-source deduplication is attempted.

### Source inventory and coverage

| Source file | Rows | Exact duplicate rows retained | Posting-date coverage | Description / link coverage | Numeric salary amount coverage |
|---|---:|---:|---|---|---:|
| `International_Tech_Jobs_Filtered.csv` | 705,866 | 80 | `job_posted_date` present for all; dates fall in 2023 | 0 / 0 | 29,257 |
| `Merged_Tech_Jobs_45k_skills_enriched_AFTER_ADDING_SKILLS.xlsx` | 45,591 | 11 | `job_posted_date` present for 38,898 | 6,693 / 6,693 | 23,127 |
| `arab_tech_jobs_skills_enriched_AFTER_ADDING_SKILLS_439.csv` | 439 | 0 | `posted_at` present for 79 | 143 / 88 | 52 |
| `cybersecurity_jobs_expanded_6_columns.csv` | 58 | 0 | Not supplied | 0 / 0 | 2; remaining 56 salary strings are non-disclosure text such as “Not disclosed” |
| `remote_tech_jobs_foreign_after_adding_skills.csv` | 1,075 | 0 | No confirmed posting date; `updated` present for all | 1,075 / 1,075 | 50 |
| `startup_jobs_foreign_after_adding_skills.csv` | 3,543 | 0 | No confirmed posting date; `updated` present for all | 0 / 3,543 | 1,591 |
| `tech_jobs_jooble_careerjet_AGNABY_after_adding_skills.csv` | 18,583 | 0 | No confirmed posting date; `updated` present for all | 18,583 / 18,583 | 5,243 |

The salary-amount check is conservative: a numeric amount must be present. “Not disclosed”, “amount not disclosed”, and similar text remains in `salary_raw` but is not treated as a salary amount. Salary figures with an estimate/market-research provenance are kept, but marked; they must not be presented as employer-offered compensation. No currency conversion, range parsing, or salary imputation is performed.

#### Dates and activity

- The International sample has an explicit posting-date field with values in 2023.
- Remote, Startup, and Jooble/Careerjet `updated` columns are present but mix formats and lack verified semantics. Treat them as source values, not as posting or collection timestamps.
- Arab-tech `posted_at` is populated for 79/439 rows, with observed dates from 2022-10-05 through 2026-10-14.
- The merged workbook includes `updated` values in 2026 and some posting dates, but their collection/posting meaning is not established by the field names alone.
- Every normalized job row therefore has `listing_status=unknown_not_verified`; no active/open state is inferred.

#### Duplicate and identifier findings

- Exact duplicate rows were found in the International export (80 duplicate rows) and merged workbook (11 duplicate rows). They are retained and flagged.
- The merged workbook contains 6,693 non-empty unique source IDs and 38,898 rows without a source ID. Its README says the source did not remove duplicates; exact-row detection does not establish whether non-identical rows represent reposts.
- For each raw/enriched pair, source-ID sets were verified to match. Skill values changed in 1,050 Remote rows, 3,543 Startup rows, and 18,583 Jooble/Careerjet rows; no base comparison was unavailable. Skills changed from empty to non-empty in 83, 2,993, and 11,477 rows respectively.
- The generated `record_id` includes source dataset, source row number, and a row digest so retained duplicate rows still receive distinct keys. It is a staging key, not an upstream job ID.

### Skills and provenance

The input files use different skill encodings: a Python-style list in International, comma-separated text in the Remote/Startup/Jooble-Careerjet exports, semicolon-separated text in Arab-tech/Cybersecurity, and mixed comma/semicolon delimiters in the merged workbook. The parser is source-aware, preserves the source string on the job row, removes repeated tokens within a row, and then suppresses duplicate canonical assignments.

- `job_skills.csv.gz` contains 4,026,953 assignments after exact-token and canonical-ID deduplication.
- Curated taxonomy output contains 1,498 canonical entries: 175 reviewed skill entries, 3 ambiguous placeholder entries, and 1,320 observed terms kept as unreviewed exact-only entries. `skill_aliases.csv` includes 1,648 explicit/observed alias rows. Of the reviewed vocabulary, 173 canonical IDs occur in the retained job-skill assignments (169 approved-alias and 4 curated exact-only IDs); two reviewed aliases have no observed assignment in this archive.
- `approved_aliases` uses only aliases in `data/reference/skill_curation.json`; an exact-only policy allows conservative case/whitespace-normalized equality, but it is not sufficient for inclusion unless the term is reviewed. The 4,026,953 stored assignments comprise 3,514,220 `(approved_aliases, curated)` assignments, 186,799 `(exact_only, curated_exact_only)` assignments, 265,954 `(exact_only, needs_review)` assignments, and 59,980 `(exclude_pending_review, needs_owner_review)` assignments.
- Analytics and matching include only consistent policy/status pairs `(approved_aliases, curated)` and `(exact_only, curated_exact_only)` in both `job_skills` and `skills`. This yields 3,701,019 eligible assignments across 173 observed reviewed skill IDs and 664,989 job records with at least one such assignment. The other 325,934 assignments remain stored but are excluded: 1,320 unreviewed exact-only terms and 3 ambiguous terms. Thus `needs_review` exact-only records are not treated as approved just because their matching policy says `exact_only`.
- `CAN`, `Flow`, and `Word` are intentionally excluded pending data-owner review. The 59,980 excluded ambiguous rows comprise 2,727 `can`, 29,900 `flow`, and 27,353 `word` assignments. In particular, the frequent `can` label is preserved without deciding whether it is a skill or extraction artifact.
- Per-skill provenance counts are 3,311,949 assignments with no source-field provenance supplied, 413,587 with mixed row-level provenance but no per-skill lineage, 17,071 canonical assignments present in a paired base export, and 284,346 introduced in an enriched export with unverified provenance. Presence in a base file does not independently prove a skill requirement.
- The merged workbook supplies row-level `skills_source` values, including original-plus-research, description-extraction, and inferred/research-added labels. These do not identify provenance per individual skill, so the long-form table preserves the row-level value and marks that limitation.

Counts are appearances across source exports, not globally deduplicated people, employers, or unique postings. The historical and snapshot sources may overlap with each other.

### Learning resource references

`data/reference/learning_resources.csv` contains 32 records linked to curated skill IDs. Official course pages were fetched where possible; each record includes a `verification_status`, date, language note, account/credential note, and structured cost caveat. Current cost statuses: 20 `free_verified`, 5 `some_free_options`, 1 `conditional_or_mixed`, and 6 `cost_unverified`. Only `free_verified` items are eligible for a free-only recommendation; broader catalog availability or an unclear course fee is not treated as proof of free access.

### Reproducibility and release cautions

1. Keep raw files unchanged and out of Git.
2. Run `build_site_data.py`, then `build_skill_reference.py` and `build_learning_resources.py`.
3. Review `data/processed/data_quality_report.json` before each import or release.
4. Do not present latest-export rows as current/active unless an external, documented status check is added.
5. Confirm licensing and redistribution rights for each source before publishing job records or descriptions publicly.
