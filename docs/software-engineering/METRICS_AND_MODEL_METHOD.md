# Metrics and Model Method

This document distinguishes descriptive archive measurements from predictions and suitability judgments. The current dataset is a collection of source job-ad records, not a census of all vacancies or the labor market.

## General measurement rules

- The primary record unit is one retained source job-ad row (`jobs.record_id`). It is not guaranteed to represent one unique vacancy because exact duplicates and cross-source reposts exist.
- Report missingness as missingness. Never replace absent fields with zero or infer a missing status.
- A percentage must identify its denominator and cohort. Counts across different source snapshots must not be silently pooled as time series.
- Preserve raw-source provenance, source dataset, snapshot type and match policy.
- Include only consistent `(approved_aliases, curated)` and `(exact_only, curated_exact_only)` policy/status pairs in both `job_skills` and `skills`. `exact_only` by itself is not approval. Exclude `needs_review`, `needs_owner_review`, policy/status mismatches, and all `exclude_pending_review` links. The raw rows remain preserved for audit.
- An observed skill association is evidence present in these records, not proof of employer demand, a qualification, or hiring likelihood.

## Descriptive metric definitions

| Metric | Numerator | Denominator | Interpretation / restriction |
| --- | --- | --- | --- |
| Exact title record count | Distinct retained `record_id` with `lower(trim(title))` matching the displayed title | None for raw count; optional share requires an explicitly declared source cohort | Case and surrounding whitespace only; punctuation, seniority and semantic variants stay separate |
| Role-country record count | Retained records grouped by exact normalized title and normalized supplied country label | Country-mapped records for that exact title; the source-split report uses the corresponding title/source denominator | Current detailed report shows the top 15 exact titles; it is descriptive of this archive, not an occupation taxonomy or country census |
| Role-skill share | Distinct records for an exact title linked to an eligible skill | Role records in that same selected cohort with at least one eligible reviewed skill | Same link/catalog policy gate as all skill metrics; multiple skill shares can sum above 100% |
| Skill-linked job count | Distinct records linked to one canonical `skill_id` under a consistent `(approved_aliases, curated)` or `(exact_only, curated_exact_only)` pair | None for count | Do not count duplicate raw tokens more than once per record; exclude all unreviewed terms |
| Share among skill-observed jobs | Distinct eligible records linked to a skill | Distinct cohort records with at least one eligible skill | Conditional on skill data being present; show count and denominator |
| Skill coverage of all records | Records with at least one eligible skill | All retained records in same named cohort | Missing skill extraction remains unknown, not a claim that no skills are required |
| Market cohort comparison | Distinct eligible skill-linked records in one cohort | Records with at least one eligible skill in that same cohort | Current report uses only `merged_tech_jobs`; dates/activity are unverified and geographic list membership is exact-name based |
| Historical monthly count | International-source records with valid explicit `posted_at` month in 2023 | Count only; optional within-year share uses all qualifying rows in that cohort | Historical distribution, not current demand or a forecast |
| Source coverage share | Records in a source snapshot | 775,155 records in this imported archive | Describes this archive build only; large source imbalance matters |
| Field coverage | Non-blank/non-null field records | All records or documented relevant cohort | Availability is not accuracy/completeness; no implied zero values |

## Skill overlap baseline

For a user-selected skill set `U` and a candidate job/role skill set `J`, the deterministic baseline is:

`Jaccard(U, J) = |U ∩ J| / |U ∪ J|`

The result includes the matching IDs, skills only in the user profile, skills only in the candidate, user-side coverage `|U ∩ J| / |U|`, and candidate-side coverage `|U ∩ J| / |J|`. An empty union returns zero with an empty evidence set. Inputs are canonical skill IDs; aliases should be resolved and pending-review terms excluded before comparison. The score measures set overlap only and is not calibrated as an employer response, hiring probability, or overall candidate suitability.

## In-process Naive Bayes title ranking — limited-scope review only

The Node.js API separately serves a positive-evidence Bernoulli Naive Bayes model from `ml/models/role_title_nb_v1.json`. Python reads the local SQLite database in read-only mode for offline training; runtime inference is in the Node.js API process. The target is the exact normalized observed title `lower(trim(title))`, not a reviewed occupation/job-family label. Features are binary presence of eligible skill IDs, using only consistent `(approved_aliases, curated)` or `(exact_only, curated_exact_only)` link/catalog pairs. Unentered skills do not contribute negative evidence.

The stable SHA-256 record-ID partition is 80%/10%/10%; source-flagged exact duplicates and records without an eligible title/skill pair are excluded. Title classes require at least 30 training records. Validation tuning selects prior weight 2.5 by Top-5, then Top-1, using a 1-in-25 sample. On a separate 1-in-25 sample of 1,259 supported held-out rows, Top-1 is 0.289118 vs 0.181096 prior-only and Top-5 is 0.590151 vs 0.521048 prior-only. However, only 47.2943% of all held-out rows are covered by the 910 supported title classes. These metrics do not show calibration, source/time generalization, stable occupations, or user value; scores are relative and uncalibrated. The endpoint is review-only, not a production occupational classifier. See [`ROLE_TITLE_NAIVE_BAYES_EVALUATION.md`](../../ml/evaluation/results/ROLE_TITLE_NAIVE_BAYES_EVALUATION.md).

Jaccard skill overlap remains a separate deterministic matching baseline, not ML. Clustering remains a separate exploratory experiment and is not served.

## Exploratory clustering method

The offline experiment uses binary skill presence (not skill counts or TF-IDF), the `international_jobs` source, and records without exact within-source duplicate flags. It includes only consistent `(approved_aliases, curated)` and `(exact_only, curated_exact_only)` skill links and excludes all pending-review associations. A fixed-seed reservoir sample of 12,000 eligible job records is split into 80% training and 20% holdout. MiniBatchKMeans candidates use `k ∈ {4,6,8,10}`. Cosine silhouette is estimated on a fixed-size holdout subsample, and a shuffled-label score is a weak reference baseline. A repeated-seed Adjusted Rand Index measures whether assignments are stable under a second initialization on the same train/holdout split.

These are intrinsic diagnostics, not ground-truth accuracy. The sample is source-specific, skill representation is imperfect, clusters can be driven by common tools, and a high silhouette cannot establish occupations or recommend a career. No selected model is saved or shipped. Any future product use requires human interpretation, robustness across sources/time, stability analysis, and a reviewed use case.

## Predictive model gates

### Salary regression — no-go

Only 52 salary-bearing records carry an explicit currency in the SQL feasibility aggregation. The role-country audit contains 58,267 salary-field records across 25,956 exact-title/country pairs; zero annual and zero hourly value fields share an explicit currency and matching period on the same records. Source scales, provenance, estimates versus offers, and pay-period semantics are otherwise incompatible or missing. There is no approved outcome definition or adequate comparable sample. Do not combine annual and hourly values, perform currency conversion without a dated exchange-rate policy, infer salary zeros, calculate role-country means/medians from noncomparable rows, or display a regression.

### Supervised job-family classification — no-go

Source category labels are absent in some sources, sparse in others, and use incompatible vocabularies. Job titles have not been manually mapped to a reviewed target taxonomy; descriptions are sparse. Random record-level splits would also risk source duplication leakage. Define the intended label set, annotate a representative stratified sample, adjudicate labels, construct source-aware leakage-resistant train/validation/test partitions, and set macro-F1/per-class recall and calibration criteria before fitting a classifier.

### Activity prediction — no-go

Imported activity status is `unknown_not_verified`; static snapshots provide no verified close/fill outcomes or observation windows. Do not predict active status from age or call a listing active.
