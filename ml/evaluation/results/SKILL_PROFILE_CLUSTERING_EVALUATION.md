# Skill-Profile Clustering Evaluation

**Archive:** `full_archive_parquet_v1_20261028`<br>
**Source cohort:** `international_jobs`; historical 2023 International-source records<br>
**Feature representation:** binary presence of each reviewed canonical skill ID; include only `(approved_aliases, curated)` and `(exact_only, curated_exact_only)` pairs; exact-duplicate rows omitted<br>
**Sample:** 595,711 eligible source records; simple random reservoir sample of 12,000; 9,600 train and 2,400 holdout rows<br>
**Random seed:** 20261028<br>
**Serving decision:** report-only experiment; no serialized model and no user-facing occupational labels.

## Evaluation method

The experiment compares MiniBatchKMeans solutions with 4, 6, 8, and 10 clusters. It fits the binary skill matrix on 80% of a deterministic random sample and predicts labels for the held-out 20%. Intrinsic separation is measured using cosine silhouette on a fixed-size holdout subsample; a shuffled-label result is shown as a weak random baseline. A second fit of the selected cluster count is compared using adjusted Rand index. These metrics do not establish that clusters are real job families, useful recommendations, or representative of a labor market.

## Candidate results

| Clusters | Train inertia | Holdout cosine silhouette | Shuffled-label silhouette | Holdout cluster sizes |
| --- | ---: | ---: | ---: | --- |
| 4 | 32110.88 | 0.0451 | -0.0165 | [255, 861, 468, 816] |
| 6 | 30210.46 | 0.1140 | -0.0211 | [643, 357, 323, 322, 244, 511] |
| 8 | 29348.77 | 0.0874 | -0.0265 | [127, 559, 306, 509, 250, 191, 320, 138] |
| 10 | 28718.09 | 0.0935 | -0.0375 | [312, 400, 257, 454, 175, 115, 373, 63, 182, 69] |

Best candidate by the measured holdout silhouette is **k = 6** with cosine silhouette **0.1140**. The two-seed adjusted Rand stability score for that solution is **0.3607**.

## Holdout cluster profiles

Cluster IDs are arbitrary. The skill lists are descriptive terms with the highest within-cluster frequency; they are not curated titles or hiring requirements.

### Cluster 0

Holdout records: 643 (26.8%). Most frequent eligible skills: Python (99.8%), SQL (56.6%), R (30.3%), Amazon Web Services (AWS) (20.2%), Java (13.1%), Git (11.8%), TensorFlow (9.5%), PyTorch (9.2%).

### Cluster 1

Holdout records: 357 (14.9%). Most frequent eligible skills: Microsoft Excel (100.0%), SQL (44.3%), Power BI (26.9%), Microsoft PowerPoint (23.5%), Python (19.1%), Tableau (17.9%), SAS (10.6%), R (8.7%).

### Cluster 2

Holdout records: 323 (13.5%). Most frequent eligible skills: Microsoft Azure (98.1%), Python (80.2%), SQL (71.5%), Amazon Web Services (AWS) (47.7%), Databricks (35.9%), Google Cloud Platform (GCP) (22.0%), Apache Spark (21.7%), Git (16.7%).

### Cluster 3

Holdout records: 322 (13.4%). Most frequent eligible skills: Tableau (99.4%), SQL (86.3%), Python (74.5%), R (48.1%), Power BI (34.8%), Microsoft Excel (19.2%), Looker (14.0%), Amazon Web Services (AWS) (14.0%).

### Cluster 4

Holdout records: 244 (10.2%). Most frequent eligible skills: Apache Spark (92.2%), Python (87.7%), SQL (69.3%), Apache Hadoop (62.7%), Amazon Web Services (AWS) (61.1%), Java (54.1%), Scala (52.0%), Apache Kafka (46.7%).

### Cluster 5

Holdout records: 511 (21.3%). Most frequent eligible skills: SQL (46.4%), Power BI (15.5%), Microsoft Azure (13.1%), Amazon Web Services (AWS) (12.7%), Oracle Database (9.4%), Microsoft SQL Server (7.8%), Tableau (6.5%), Apache Spark (6.1%).

## Limitations and decision

This is an unsupervised, intrinsic evaluation on sampled International-source 2023 job records. Skill extraction and enrichment provenance are imperfect, duplicated advertisements may remain across sources, and the chosen source has no descriptions. A high silhouette does not validate an occupation taxonomy. Human review, source-balanced robustness checks, cluster stability, and a clear product use case are required before considering any cluster output for an application. Salary prediction and supervised classification remain no-go under the current data profile.
