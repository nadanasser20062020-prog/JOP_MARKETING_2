# ADR-0002: Run All Online Inference In-Process in Node.js

- **Status:** Accepted and implemented for the current release
- **Date:** 2026-10-28
- **Decision owner:** Project owner
- **Related records:** `ml/requirements.json`, `API_SPECIFICATION.md`

## Context

The project has a deterministic Jaccard skill-overlap baseline and a separate positive-evidence Naive Bayes model that ranks exact observed title strings from reviewed-skill inputs. The title model has a bundled JSON artifact and a limited-scope held-out evaluation, but is not a stable occupational classifier and is not production-approved. Clustering has no served model or stable user-facing occupational labels. Salary regression, stable job-family classification, and active-listing prediction do not pass their data-quality gates. The owner requires Node.js-only online inference, with Python kept out of the request path.

## Decision

- The HTTP/API runtime, SQL analytics, deterministic Jaccard matching, and trained title-ranking inference run in one Node.js backend process.
- `POST /api/v1/matches` uses Jaccard to compare reviewed skill sets in aggregate exact-title role profiles. It is a similarity baseline, not a trained model, per-ad match score, candidate-suitability decision, or hiring probability.
- `POST /api/v1/models/role-title/predict` separately loads `ml/models/role_title_nb_v1.json` and ranks supported exact observed title strings. It is explicitly limited-scope/review-only; relative scores are uncalibrated and it is not a stable occupational classifier.
- Python remains for offline data preparation, SQL/Python analysis, training, and evaluation. The API does not spawn Python and does not call a separate ML server.
- Clustering stays exploratory/report-only. Salary regression, stable job-family classification, and active-listing prediction remain disabled.
- Any expansion of the title model beyond limited-scope review, or any new online model task, requires a new explicit decision, task-specific evaluation, and compatible Node.js inference. No remote inference service is allowed by this decision.

## Alternatives Considered

- **Node API that launches Python during each request:** Not selected because the requested runtime is Node-only and Python runtime packaging differs across local and Vercel deployments.
- **Separate ML service:** Rejected because it adds a deployment, network boundary, and service operation not needed by the current evidence.
- **Serve exploratory clusters as role predictions:** Rejected because stability and occupational validity have not been demonstrated.
- **No online skill matching:** Rejected because a simple, explainable similarity baseline can be provided without claiming a prediction.

## Consequences

- `/api/v1/models/status` keeps `productionModels` empty while separately listing the limited-scope served Naive Bayes model and the non-ML Jaccard baseline.
- Jaccard score and directional coverage are explainable, and matching input is transient/non-persistent. The current endpoint ranks role profiles; individual job-ad scoring is not implemented.
- Offline clustering figures remain research deliverables, not recommendations or stable occupations.
- Full local-data validation and selected HTTP smoke tests have passed; concurrent-load/performance testing and deployment reconciliation remain before a public release.

## Review Trigger

Revisit when a proposal expands the current review-only title ranker to production or adds another model task; require a reviewed target, broader/source-aware evaluation, coverage and calibration analysis, privacy/performance checks, and continued in-process Node.js inference unless the owner explicitly changes the runtime requirement.
