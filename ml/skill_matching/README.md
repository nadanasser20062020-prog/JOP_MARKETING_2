# Skill Matching

`matching_baseline.py` is the offline Python reference for a deterministic, explainable Jaccard overlap score over canonical skill IDs. The online version is implemented in Node.js and exposed as `POST /api/v1/matches`; results include matched, missing, and user-only skills, directional coverage, and supporting-record counts. The score is skill overlap only, not a hiring probability, qualification verdict, or complete suitability measure.

Inputs must be resolved to reviewed canonical IDs upstream. Include only consistent `(approved_aliases, curated)` and `(exact_only, curated_exact_only)` pairs in both `job_skills` and `skills`; an exact-only policy alone is not approval. Exclude all `needs_review`, `needs_owner_review`, and `exclude_pending_review` terms.

The reference module does not persist user profiles or call a service; the Node API likewise handles requests transiently. The trained Naive Bayes title ranker is a separate model in `train_role_title_nb.py` with its own artifact and evaluation; Jaccard is not ML. Tests run from the repository root with:

```text
python -m unittest ml.skill_matching.test_matching_baseline
```
