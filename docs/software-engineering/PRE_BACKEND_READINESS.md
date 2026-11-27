# Pre-Backend Readiness Gate

## Purpose and boundary

**Historical status note:** This document preserves the pre-backend data-quality gate and analysis decisions. The Node.js API is now implemented in `backend/node/`; this file is no longer a statement that backend work has not started. The local SQLite archive remains the only application data source and must not be silently refreshed, replaced, or joined with a hosted database. The current runtime is one Node.js process for HTTP, SQL analytics, and deterministic matching; Python is used offline for loading, analysis, and experiments only. No independent ML service is in scope.

## Data gate

| Gate | Finding | Product constraint |
| --- | --- | --- |
| Source archive | Seven datasets and 775,155 retained source records in import `full_archive_parquet_v1_20261028` | Disclose source mix and snapshot limits; not the complete labor market |
| Duplicate handling | 91 exact duplicate rows remain flagged; cross-source reposts are not resolved | Preserve provenance; do not present counts as deduplicated unique vacancies |
| Listing state | All imported statuses are `unknown_not_verified` | Never label records active/open |
| Role labels | 218,302 exact normalized title strings; no reviewed unified occupational taxonomy | Normalize case/outer whitespace only; preserve semantic variants |
| Skill evidence | 3,701,019 reviewed eligible links across 173 observed reviewed skill IDs; 664,989 job records with eligible links | Include only consistent `(approved_aliases, curated)` and `(exact_only, curated_exact_only)` pairs in both link and catalog tables; exclude 265,954 needs-review exact-only and 59,980 owner-review links; explain denominator |
| Descriptions and URLs | 26,494 descriptions (3.42%) and 29,982 source URLs (3.87%) | Individual-ad detail is secondary; do not imply comprehensive source-link coverage |
| Country | 160 usable labels; no ISO mapping; two of 22 configured Arab-country labels absent | Exact reviewed name grouping; report absent labels; map only after reviewed geography mapping |
| Market contrast | `merged_tech_jobs` has 22,442 Arab-labelled and 17,279 other represented-country records; reviewed-skill denominators are 22,398 and 17,279; 17 of 22 configured Arab labels occur in this source | Descriptive only, source date semantics unverified; five absent source labels (Comoros, Djibouti, Mauritania, Somalia, Syria) are unknown, not zero-opportunity markets |
| Dates | 705,866 `international_jobs` rows have explicit 2023 posting dates | Historical source distribution only; other `updated` fields are not posting dates |
| Salary | 21,585 annual and 10,337 hourly values; currency supplied on only 52 salary-bearing rows in the feasibility profile | No cross-source pay comparison or salary regression; do not conflate hourly/annual or estimates/offers |
| Work mode | Source-specific boolean-like values and mixed free text | Preserve raw values; false does not imply on-site; no complete hybrid taxonomy |
| Learning catalogue | 32 rows; 20 source-marked free, but all 32 verification dates are later than archive build date | Revisit each provider page, cost, language, access, and URL before any public free badge |

## Feature and model gate

Feature contracts, input fields, outputs, and readiness states are in `ml/requirements.json`. Primary pre-backend decisions:

1. Approve descriptive skill demand, with record counts, denominator, policy and source context.
2. Approve exact-normalized title lookup, not semantic title family classification.
3. Approve historical month aggregation for the defined International 2023 cohort only.
4. Keep the Arab/non-Arab contrast descriptive and restricted to one common source.
5. Keep salary regression, supervised occupational classification, active-listing claims, and resource-cost claims disabled.
6. Permit an interpretable Jaccard skill-overlap baseline for an explicitly user-selected profile, subject to review. Describe only observed overlap; never emit a hiring probability or suitability verdict.
7. Keep skill clustering as exploratory offline analysis until human validation and stability/robustness checks; do not ship cluster names as occupations.
8. The implemented Node.js API owns online SQL analytics and deterministic matching. Python analysis and clustering remain offline; no Python subprocess or standalone ML service is used in API requests.

## Acceptance criteria before API work

- Every user-visible metric has a named unit, numerator, denominator, missingness treatment, source cohort, and interpretation limit.
- Unknown values remain unknown and are never substituted with zero.
- Every job result preserves its source and imported record identity; duplicate policy is visible.
- Skill matching filters according to the reviewed policy and returns an explanation of matched terms.
- Date, salary, activity, and geographic features have explicit gates rather than silent fallback values.
- Local SQLite remains the data boundary until the user authorizes any refresh or source change.
- The implemented system has one Node.js API process and uses the local SQLite file read-only; no remote database or separate ML service is used.

## Reproduction

Run the aggregate report with `python analysis/generate_pre_backend_analysis.py`. Run the exploratory clustering experiment with `python ml/clustering/fit_skill_profile_clusters.py`. Both open SQLite in read-only mode. Run overlap tests with `python -m unittest ml.skill_matching.test_matching_baseline`.
