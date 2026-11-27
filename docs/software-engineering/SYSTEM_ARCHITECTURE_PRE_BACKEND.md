# System Architecture Before Backend Implementation

> **Historical design snapshot:** this document began before the backend was implemented. It is retained for design traceability, not as the current implementation contract. The current Node.js API, endpoints, test evidence, and known gaps are documented in [`ARCHITECTURE.md`](ARCHITECTURE.md), [`API_SPECIFICATION.md`](API_SPECIFICATION.md), and [ADR-0002](adr/0002-in-process-ml-execution.md).

## Deployment boundary

The implemented request-serving unit is **one Node.js backend process**. It owns request validation, business logic, read-only SQLite access, aggregation queries, Jaccard role-profile matching, and in-process Naive Bayes title-ranking inference. Python runs only offline for data preparation, training, and evaluation; it is never invoked by an API request. Machine-learning inference is not a separate service. No frontend entry point is present in the current checkout.

## Logical components

1. **Presentation client (future):** user-facing forms, accessible tables/charts, filters and explanatory text. It will call relative same-origin backend endpoints; no browser code should connect to localhost or to an independent ML host.
2. **Single application backend (implemented):** request validation and limits; versioned response schemas; query/aggregation layer; skill policy enforcement; source/status/denominator disclosure; deterministic role-profile overlap; in-process title-model loader. Individual-ad scoring is not implemented.
3. **Local SQLite database:** canonical imported records, source provenance, curated skills/aliases and learning-resource catalogue. Current read-only analysis is based on this file. Any future write operation or dataset refresh requires a separate explicit decision and audit policy.
4. **Offline analysis/evaluation scripts:** reproducible read-only preparation commands that generate aggregate reports and evaluate candidate algorithms without operating as services.

## Current data path for skill matching

The API resolves submitted labels through the reviewed alias dictionary and accepts only consistent `(approved_aliases, curated)` and `(exact_only, curated_exact_only)` policy/status pairs across `skills` and `job_skills`; pending-review IDs are rejected. The Node process queries materialized role-skill rollups, calculates Jaccard overlap and directional coverage, and returns matched, missing, user-only skills and record evidence. This endpoint ranks aggregate role profiles, not individual ads. It labels the result as skill overlap, not suitability, qualification, or hiring probability. Inputs are transient and are not persisted or logged.

## Data path for descriptive analytics

The query layer selects a named source/cohort, excludes ineligible skill matches, counts distinct job records, and computes a denominator from the same cohort. The response includes data-through/snapshot metadata when verified, missing field counts, source links where present, duplicate policy and interpretation. Missing values remain absent/null and are not converted to zero. Historical month aggregation is limited to explicit International-source 2023 `posted_at` values.

## Error and safety behavior

- Invalid or unknown skill IDs: validation error with no silent fallback to raw text matching.
- Pending-review skills: excluded from matching and demand results.
- Unsupported salary/activity claims: no endpoint or response label until the corresponding data-readiness gates are passed.
- Missing descriptions, locations or URLs: expose availability rather than fabricating records or links.
- Expired/unverified course cost: display no free badge until provider page review is current.
- Large result sets: use bounded filters/pagination and a consistent SQLite read transaction; exact limits are to be decided during API requirements/design, not improvised in this analysis stage.
- Browser integration: same-origin relative routes; the browser never addresses `localhost` for backend/ML connectivity.

## ML lifecycle

The current JSON artifact contains a positive-evidence Bernoulli Naive Bayes model trained offline with Python; Node.js loads it and serves an exact observed-title ranking in-process. It is limited-scope/review-only, uncalibrated, and not a production occupational classifier. Jaccard remains a separate deterministic baseline, not ML. Clustering is report-only and not served. Stable job-family classification, salary regression, and activity prediction remain no-go under current labels and provenance. No network hop to a separate ML server is used.

## Remaining privacy, governance and operations work

The current API keeps submitted skill inputs transient, does not persist or log them, applies body/skill limits, and opens SQLite read-only. Still needed before a wider/public release: source-link/license and redistribution review; dataset refresh cadence/approval; full performance and concurrency targets; browser accessibility/localization acceptance; Vercel bundle/cold-start verification; and a complete user-facing release review. Do not imply that this design document resolves those remaining product/legal questions.
