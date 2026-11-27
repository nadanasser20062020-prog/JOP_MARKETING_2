# Clustering Experiments

`fit_skill_profile_clusters.py` evaluates exploratory groups of job records using a sparse binary matrix of reviewed canonical skill IDs. It reads the local SQLite database in read-only mode, uses the International-source historical cohort, excludes exact duplicate rows and all skill links outside the reviewed policy/status pairs, compares MiniBatchKMeans cluster counts on a deterministic train/holdout sample, and writes metrics plus descriptive skill profiles to `ml/evaluation/results/`.

This is not an approved occupation taxonomy, recommendation model, or user-facing feature. No model artifact is saved. The current evaluation and its limitations are documented in [`../evaluation/results/SKILL_PROFILE_CLUSTERING_EVALUATION.md`](../evaluation/results/SKILL_PROFILE_CLUSTERING_EVALUATION.md). See [`../README.md`](../README.md) for installation and reproduction instructions.
