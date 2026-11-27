# Reviewed-Skill to Observed-Title Naive Bayes Evaluation

**Model ID:** `positive_skill_naive_bayes_observed_title_v1`<br>
**Archive:** `full_archive_parquet_v1_20261028`<br>
**Serving boundary:** in-process Node.js API; training and re-evaluation are offline Python tasks.<br>
**Decision:** the model is served for limited-scope review only; it is **not** approved as a production occupational classifier.

## Task and data

The model ranks exact observed job-title strings from positive evidence in a submitted set of reviewed skill IDs. The target is `lower(trim(jobs.title))`; it is not a stable occupation or job-family taxonomy. Features are binary skill-document presence from the consistent eligibility pairs `(approved_aliases, curated)` and `(exact_only, curated_exact_only)`. An unentered skill is not treated as a negative feature.

Rows with an empty title, no eligible reviewed skill link, or `exact_duplicate_within_source = yes` are excluded. A deterministic SHA-256 record-ID split yields **531,850 training**, **66,866 validation**, and **66,211 held-out test** records (**664,927** total eligible records across all three partitions). The split is 80%/10%/10% by bucket, not a time split; records with similar content or cross-source reposts may still be present in different partitions.

Only title classes with at least **30 training records** are modeled. This yields **910 exact-title classes** and **254,281 supported training records**, a **47.8107%** training-coverage rate. The model uses **173 eligible skill features**. Supported-class coverage is **31,850/66,866 (47.6326%)** on validation and **31,314/66,211 (47.2943%)** on the held-out test partition. Predictions do not cover the other title strings.

## Evaluation and tuning

The implementation is positive-evidence Bernoulli Naive Bayes with additive smoothing (`alpha = 1.0`). It scores each title as:

`priorWeight × log P(title) + Σ log P(submitted skill present | title)`

The prior weight was selected using a deterministic **1-in-25 sample** of supported validation records (**1,254** records), choosing the highest Top-5 accuracy, then highest Top-1, then the lower prior weight. The candidate grid was `[0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.75, 3, 3.25, 3.5, 4, 5]`; **2.5** was selected. The test metric uses a separately salted 1-in-25 sample of supported held-out records (**1,259** records); that sample is not used for hyperparameter selection.

| Evaluation sample | Method | Top-1 accuracy | Top-5 accuracy |
| --- | --- | ---: | ---: |
| Validation, n = 1,254 | Prior-only baseline | 0.163477 | 0.523126 |
| Validation, n = 1,254 | Naive Bayes, prior weight 2.5 | 0.296651 | 0.600478 |
| Held-out test, n = 1,259 | Prior-only baseline | 0.181096 | 0.521048 |
| Held-out test, n = 1,259 | Naive Bayes, prior weight 2.5 | 0.289118 | 0.590151 |

On the sampled held-out test, Top-1 improves by **10.8022 percentage points** and Top-5 by **6.9103 percentage points** relative to the prior-only baseline. These are accuracy results for supported exact-title labels only; they do not establish calibration, market representativeness, or employment suitability.

## Interpretation and limits

- Scores are softmax-normalized relative scores over the 910 modeled labels. They are uncalibrated and are not probabilities of employment, job availability, a candidate's qualification, or a guaranteed recommendation.
- The result is a ranking of collected title strings, not a job-family classifier. Seniority, punctuation, abbreviations, and semantically similar title variants remain separate labels.
- About **52.7%** of held-out records are outside the supported-class test coverage and cannot be evaluated or predicted by this artifact.
- The validation and test metrics use 1/25 samples, not every supported held-out row. The record split is not time- or source-held-out; flagged exact duplicates are excluded, but cross-source reposts and near-duplicates are not fully resolved.
- Skill links are source/enrichment evidence, not independently verified mandatory requirements. Collection bias, mixed source snapshots, sparse descriptions, and unknown listing activity remain.
- At least two submitted skills must be represented in the model vocabulary. Unmodeled submitted skills are reported and do not add score evidence.
- Deterministic Jaccard overlap remains a separate explainable matching baseline; it is not this trained model. Offline skill clustering is exploratory and is not served.

The API status keeps `productionModels` empty and identifies this artifact as `limited_scope_review_only_not_production_approved`. Treat predictions as an experimental, auditable suggestion until label quality, source-aware generalization, coverage, calibration, and user-value testing are addressed.

## Reproduction

Restore the checksum-verified local SQLite archive, install the offline training requirements, then run:

```bash
.venv/bin/python -m ml.skill_matching.train_role_title_nb
```

The trainer reads SQLite in read-only mode and writes the compact JSON artifact at `ml/models/role_title_nb_v1.json`. Node.js loads that artifact in-process; no Python inference service is used. The artifact records the selected prior weight, split counts, coverage, validation tuning, and sampled held-out metrics.
