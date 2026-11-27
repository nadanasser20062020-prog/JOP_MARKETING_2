# Machine Learning Plan

Models must address a clear project question; they should not be added as decoration. Every model depends on the dataset audit. If the required data is unavailable or unreliable, document why the model is unsuitable rather than presenting misleading results.

## Current Pre-Backend Decision

**Implemented state:** the Node.js API now serves two separate paths: deterministic Jaccard role-profile overlap (`POST /api/v1/matches`, not ML) and a trained positive-evidence Bernoulli Naive Bayes title-ranking model (`POST /api/v1/models/role-title/predict`). Python is used only offline for training; the Node API loads the JSON artifact in-process. The model ranks exact observed `lower(trim(title))` strings, not a curated occupational taxonomy. It remains `limited_scope_review_only_not_production_approved`: 910 title classes cover 47.2943% of held-out records, and on a sampled held-out set of 1,259 records Top-1 is 0.289118 vs 0.181096 prior-only, while Top-5 is 0.590151 vs 0.521048 prior-only. Full protocol and limitations are in [`ROLE_TITLE_NAIVE_BAYES_EVALUATION.md`](../ml/evaluation/results/ROLE_TITLE_NAIVE_BAYES_EVALUATION.md). Clustering remains offline/report-only; see [`SKILL_PROFILE_CLUSTERING_EVALUATION.md`](../ml/evaluation/results/SKILL_PROFILE_CLUSTERING_EVALUATION.md). Salary regression, stable job-family classification, and active-listing prediction remain disabled by data-quality gates. No separate ML server is in scope. See the [pre-backend readiness gate](software-engineering/PRE_BACKEND_READINESS.md) and [metrics/model method](software-engineering/METRICS_AND_MODEL_METHOD.md) for method and constraints.

## 1. Skill-to-Job Matching — Explainable Baseline

- **Question:** Which observed role profiles cover the largest share of a user's reviewed skills, and which common skills are missing?
- **Potential inputs:** Normalized user skills, eligible reviewed skills aggregated per exact observed title, and optional source/country/work-arrangement filters.
- **Implemented approach:** `POST /api/v1/matches` resolves reviewed skills and ranks aggregated exact-title role profiles with deterministic Jaccard; it explains matched, missing, and user-only skills plus record evidence. It does not currently score individual job-ad records; `/roles/{roleId}/ads` is a separate unscored list. Per-ad ranking is a remaining requirement and must not be attempted with the previous slow full-table path; it needs an indexed/capped design and explicit query-performance evaluation first.
- **Evaluation:** Unit/API tests cover deterministic scores, filters, missing-skill explanation, and a full-database smoke request. There are no human relevance labels or Precision@K results, so ranking quality beyond mathematical correctness has not been validated.
- **Usage limit:** A coverage score is not a hiring probability and does not establish a candidate's suitability in every respect.

## 2. Clustering — Discovering Job Groups

- **Question:** Are there groups of advertisements with similar skill combinations or descriptions?
- **Potential inputs:** A normalized skill set for each advertisement, or text representations of titles and descriptions if the text is usable.
- **Approach:** Build an appropriate representation, test a small number of clustering methods, and review metrics, examples, and the most frequent skills in each group. Assign descriptive names only after manual interpretation.
- **Evaluation:** Review silhouette or another suitable metric for the representation, cluster stability, and representative examples.
- **Output:** Patterns that support market exploration, not authoritative employer or occupation labels.

## 3. Classification — Job-Family Classification

- **Question:** Can an advertisement be classified into useful categories such as Data, Backend, or Frontend?
- **Required inputs:** An analyzable title and description, defined categories, and a reviewed labelled sample or a reliable existing category field.
- **Approach:** Define category rules, prepare and review labels, split data without leakage, and establish a simple text-classification baseline such as TF-IDF with a suitable classifier. Manually review errors.
- **Evaluation:** Report per-class precision, recall, and F1, as well as Macro-F1 and a confusion matrix. Do not rely on accuracy alone when class sizes differ.
- **Go/no-go condition:** Do not expose the model if there are too few reliable labels or its errors are unacceptable. A report explaining insufficient labels is a valid outcome.

## 4. Regression — Salary Estimation

- **Question:** Can an approximate salary level or range be estimated from job-advertisement attributes?
- **Required inputs:** A sufficient number of advertisements with disclosed salaries, comparable currency and pay-period data, and explanatory attributes such as country, role, experience, or skills.
- **Approach:** Standardize units and currencies under a documented policy; do not encode undisclosed salaries as zero. Build a simple baseline and compare it with suitable additional models.
- **Evaluation:** Use an appropriate train/test split, compare against the baseline, and report MAE, RMSE, and R² with clear interpretation in understandable units. Review errors by country and category.
- **Go/no-go condition:** If salary coverage is sparse or inconsistent, keep the experiment in the report and do not show estimates to users.

## Reliable Experiment Practices

- Separate training and test data before fitting data-dependent transformations; prevent duplicate advertisements from leaking across the split.
- Use a time-based split when dates support the intended use of predicting future advertisements.
- Compare every model with a simple baseline and record data definitions, features, metrics, and experiment settings.
- Check performance differences across countries or categories; they may reveal collection bias or weak market coverage.
- Do not display a recommendation or salary figure without explaining its evidence and limitations.

## Integration with the Website

- The implemented API currently returns ranked role profiles with matched/missing/user-only skills and record evidence; it does not rank individual advertisements. A client must label this as role-profile matching and cannot imply per-ad scores. Frontend integration is not implemented.
- Clustering may support exploration of skill groups only after review; it is not currently served.
- Classification may support browsing or normalization of job families.
- Regression estimates must remain distinct from advertised salaries and include clear limitations.
- Document experiment results and metrics; do not conceal weak model performance just to claim that every algorithm was used.
