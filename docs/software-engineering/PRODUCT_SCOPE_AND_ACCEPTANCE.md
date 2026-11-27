# Product Scope, Requirements and Acceptance Criteria (Pre-Backend)

## Product goal

Help users explore the observed technical skills and role-title strings in the collected job-ad archive, compare carefully defined source cohorts, and understand skill overlap with user-selected skills. The product must make source limitations and metric definitions visible. It is not a live vacancy feed, complete labor-market census, salary estimator, hiring probability engine, or validated occupational taxonomy.

## In scope for a first reviewed product release

- Browse top observed eligible skills with count and denominator.
- Search exact-normalized role titles while preserving punctuation, seniority and semantic differences.
- Filter descriptive data by source, available country label and documented historical cohort.
- Compare the two Arab/other represented-country groups only within `merged_tech_jobs`, with counts, denominators, absent Arab labels and caveat.
- Show the historical 2023 International-source monthly record counts without implying a current trend.
- Let a user select reviewed canonical skill IDs and calculate explainable overlap with an available job/role skill profile, if a candidate profile is present and validated.
- Present learning resources only after item-by-item URL, price, access, language and verification review.
- Display source provenance, activity unknown state, duplicate policy and field availability.

## Explicitly out of scope / disabled

- Starting the backend or API in this preparation phase.
- A separate ML service or server.
- Claims of live/active/open vacancies.
- Claims that archive rows represent the entire labor market or provide current demand.
- Salary ranking, salary conversion, pay prediction or salary regression.
- Supervised job-family classification from current incompatible source labels.
- Automatic semantic role-family merging.
- Map-based opportunity claims before reviewed ISO/geographic mapping.
- A free-course guarantee based solely on imported verification metadata.
- Automatic deletion or deduplication of source records, archive refresh, new data ingestion, or changes to original source files.

## Functional requirements

| ID | Requirement |
| --- | --- |
| FR-01 | Every result preserves source record identity and source dataset. |
| FR-02 | Skill counts use distinct `record_id` per canonical skill; include only consistent `(approved_aliases, curated)` and `(exact_only, curated_exact_only)` pairs on `job_skills` and `skills`; exclude unreviewed terms and policy/status mismatches. |
| FR-03 | Every percentage shows the numerator, denominator, cohort and meaning. |
| FR-04 | Title matching uses case-folded/trimmed exact strings only until a reviewed taxonomy is approved. |
| FR-05 | Arab/other comparison uses the common-source `merged_tech_jobs` cohort and excludes blank, NULL and non-country sentinel labels. |
| FR-06 | Historical monthly series uses only explicit `international_jobs.posted_at` records in 2023. |
| FR-07 | Missing values stay missing; no implicit zero, inferred location, assumed activity or invented salary. |
| FR-08 | Listings disclose `unknown_not_verified` status and may not be called active/open. |
| FR-09 | Skill overlap reports matched and unmatched canonical IDs and does not claim hiring probability or suitability. |
| FR-10 | Future serving executes SQL and approved Python ML within one backend process; there is no standalone ML service. |
| FR-11 | Course cost/access labels require fresh per-item verification before publication. |
| FR-12 | Any source refresh, database replacement or new dataset requires explicit approval; SQLite is the local source boundary. |

## Non-functional requirements

- Reproducible deterministic analysis with a recorded archive ID, script/query versions, random seed for experiments, and bounded sampling.
- Read-only analysis by default and no persistent output beyond explicitly requested aggregate reports.
- Explainable business/ML outputs; no opaque scores without definitions and evidence.
- Accessible text/table alternatives to charts and maps; localization must preserve source meaning.
- Single-process backend design with bounded query work, controlled response sizes and safe input validation.
- Privacy by default for any user-entered skill profile; storage/retention not authorized by this document.

## User stories and acceptance criteria

### Observe skill demand

As a learner, I want to see frequently observed skills so I can explore what appears in this archive.

Acceptance: each skill row shows canonical label, distinct job-record count, denominator of jobs with eligible skill data, within-denominator share, skill-match policy, source scope and caveat that observed frequency is not hiring probability. Pending-review terms are absent.

### Explore a role title

As a learner, I want to search a role title without silently merging unlike jobs.

Acceptance: only case and outer whitespace are normalized; punctuation and level variants remain separate; result counts can be traced to source records; no unreviewed job-family label is presented.

### Compare market groups

As a project reviewer, I want an auditable Arab/other comparison.

Acceptance: both cohorts come from `merged_tech_jobs`; each chart/table shows counts and the eligible-skill denominator; country-group rules and absent configured labels are named; copy states date/activity and representativeness limitations; a missing country is not rendered as zero opportunities.

### Compare my skills to a profile

As a learner, I want to understand which skills overlap with a selected role/job profile.

Acceptance: inputs are canonical IDs, pending-review aliases are rejected/excluded, score formula and matched/unmatched IDs are visible, empty sets are handled safely, deterministic ties are stable, and output says it is not a hiring probability or full suitability measure.

### Review historical patterns

As a reviewer, I want to inspect the archive's explicit historical dates.

Acceptance: only the International source's explicit 2023 dates appear; chart is labeled historical; other source date fields are not mixed in; missing months are treated as missing observations, not fabricated zeros.

## Open decisions before API design

User-profile persistence and consent; authorization; source redistribution permission and attribution; course verification workflow; data refresh approval/cadence; geographic name mapping; accessibility/localization targets; API pagination/limits; backup and recovery; deployment threat model; testing/monitoring acceptance. These must be reviewed before release.
