# ML Readiness and Experiments

## Current runtime boundary

The implemented website API and online application logic are Node.js-only and run in one process with local read-only SQLite. The API does not launch Python or contact an ML service. Python is used for offline data loading, analysis, and model experiments. See the [Node API status](../backend/README.md) and the machine-readable feature contract in [`requirements.json`](requirements.json).

## Online skill-overlap baseline

The production API resolves user-entered skill labels through the reviewed alias catalogue and ranks role profiles with deterministic Jaccard overlap. This is implemented in Node.js at `backend/node/queries.js` and exposed by `POST /api/v1/matches`. It is a transparent similarity baseline, not a trained model, hiring probability, or full suitability judgment. Matching filters only the policy/status-consistent `(approved_aliases, curated)` and `(exact_only, curated_exact_only)` pairs. Input is transient and neither logged nor persisted. The Python reference implementation in [`skill_matching/matching_baseline.py`](skill_matching/matching_baseline.py) remains an offline method/test reference.

## Served Naive Bayes title ranking

A separate trained model is served in-process by Node.js at `POST /api/v1/models/role-title/predict`; inference does not start Python or call another service. The offline trainer is [`skill_matching/train_role_title_nb.py`](skill_matching/train_role_title_nb.py), and the compact artifact is [`models/role_title_nb_v1.json`](models/role_title_nb_v1.json). It uses positive evidence from eligible reviewed skills to rank exact normalized title strings, not to predict a stable job family. At least two modeled skills are required; the relative scores are uncalibrated.

The model remains limited-scope/review-only, not production-approved: on a 1,259-record sampled held-out set, Top-1 is 0.289118 vs 0.181096 prior-only and Top-5 is 0.590151 vs 0.521048. Only 47.2943% of all held-out rows are in supported title classes. See [`ROLE_TITLE_NAIVE_BAYES_EVALUATION.md`](evaluation/results/ROLE_TITLE_NAIVE_BAYES_EVALUATION.md) for the split, coverage, tuning, and interpretation limits. This model is distinct from Jaccard and from report-only clustering.

Run the reference baseline tests from the repository root:

```bash
python -m unittest ml.skill_matching.test_matching_baseline
```

## Exploratory clustering

`clustering/fit_skill_profile_clusters.py` is an offline, repeatable experiment against the local SQLite database in read-only mode. It uses the International-source 2023 cohort, filters exact within-source duplicates and unreviewed skill links, samples eligible records with a fixed-seed reservoir sample, fits a sparse binary skill matrix, compares candidate MiniBatchKMeans counts on held-out records, and reports intrinsic quality/stability measures and cluster skill profiles.

It deliberately does not serialize a model or assign stable occupational labels. Results remain report-only and are not exposed by the Node API. Install clustering dependencies and run it locally only after restoring the full SQLite file:

```bash
python -m pip install -r ml/clustering/requirements.txt
python ml/clustering/fit_skill_profile_clusters.py
```

The saved clustering evaluation in `evaluation/results/` is evidence about an exploratory sample, not a validated production model. The served Naive Bayes title ranker is a separate, limited-scope review artifact; it does not constitute a stable job-family classifier. Salary regression, stable job-family classification, and active-listing prediction remain disabled until their documented data and evaluation gates pass. All online inference must remain in the Node.js backend process; a separate ML server is out of scope.
