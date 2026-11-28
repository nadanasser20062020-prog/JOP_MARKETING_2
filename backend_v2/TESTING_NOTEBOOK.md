# Testing notebook — Backend v2

**Audit/source date:** 2026-10-28. **Runtime checked:** Node.js 22.22.3 (`node:sqlite` reports its experimental warning on Node 22). تم بناء `backend_v2` وإجراء الاختبارات والتحقق النهائي باستخدام JavaScript/Node.js فقط. في جولات استكشاف سابقة قبل هذا التحقق استُخدم Python مرتين لقراءات SQLite فقط، خلافًا لقيد المستخدم؛ لم تُكتب بيانات ولم تُستخدم نتائج تلك القراءات، وأُعيدت فحوص المخطط والأعداد المطلوبة هنا باستخدام Node.js.

## A. Approved data-source and provenance checks

### A1. NADA SQLite parts (the only files read from NADA)

- Used exactly `jobs_cleaned_audited.sqlite3.gz.part-001` through `part-011`; no other files in NADA were opened or examined.
- Count: **11** files. Combined bytes: **986,484,511**.
- Concatenated archive SHA-256: `a8a9d46b63a9f923dfe07a074ed07f16bc0a6c0643974abb8692a0f713f9efab`.
- Concatenated archive hash equaled `data/processed/jobs_cleaned_audited.sqlite3.gz`; `gzip -t` passed.
- SHA-256 of the decompressed archive stream equaled the extracted `data/processed/jobs_cleaned_audited.sqlite3`: `582a141af4c0bde4b941dde062785f465825d12ddacd51f07c924d5f352a54ac`.
- Extracted SQLite bytes: **7,649,681,408**. Node `node:sqlite` `PRAGMA quick_check(1)` returned **`ok`**.
- Node read-only schema/count check returned:

| Table/entity | Count |
|---|---:|
| `jobs` | 775,155 |
| `job_cleaning_audit` | 775,155 |
| `job_skills` | 4,026,953 |
| `skills` | 1,498 |
| Distinct `job_skills.skill_id` absent from `skills` | 0 |

The schema preflight confirmed the salary annual fields and only `record_id`/`skill_id` as the portable required fields on `job_skills`; the deployment builder’s fallback no longer depends on raw/normalized/category columns.

### A2. Cross-check against the approved cleaned-data Drive folder

Drive folder: **JOP_MARKETING_2 - Cleaned Data (Audit 2026-10-28)**, folder ID `1zYIKXR74ASQQ6PBAUmtL54Ihq0RUnPmH`. Read its small manifest, README, cleaning summary, salary policy, final report, and source manifest. The Drive manifest states audit date `2026-10-28`, **775,155** rows, gzip bytes **212,226,750**, and original CSV gzip SHA-256 `6f53340a00a17f4a6d86087a6bf6d98a4fce1a1bb79b795b6237f87fd927fd72`. It lists three CSV gzip parts:

| Part | Bytes | SHA-256 from Drive manifest |
|---|---:|---|
| `jobs_cleaned_audited.csv.gz.part-001` | 94,371,840 | `51a002a5472a94687f7734310a3fc7ed418509df0d1f81b968a9879d3f7217a0` |
| `jobs_cleaned_audited.csv.gz.part-002` | 94,371,840 | `27f6da4545f36dfbe6374e3a708a7204d8f26a1b7448079e8d24269a0687af37` |
| `jobs_cleaned_audited.csv.gz.part-003` | 23,483,070 | `5905210dac7021028ce9406068a69c945208fb552fdd251e0326c011c8505c25` |

The CSV gzip parts were **not** staged locally or rehashed in this session; those manifest values are Drive metadata, not locally recomputed checksums. Instead, the authorized NADA SQLite’s seven `source_file` counts were compared to the seven selected source files in Drive’s cleaning summary/source manifest. All names and counts matched exactly:

| `source_file` | SQLite rows | Drive cleaned-data row count |
|---|---:|---:|
| `International_Tech_Jobs_Filtered.csv` | 705,866 | 705,866 |
| `Merged_Tech_Jobs_45k_skills_enriched_AFTER_ADDING_SKILLS.xlsx` | 45,591 | 45,591 |
| `arab_tech_jobs_skills_enriched_AFTER_ADDING_SKILLS_439.csv` | 439 | 439 |
| `cybersecurity_jobs_expanded_6_columns.csv` | 58 | 58 |
| `remote_tech_jobs_foreign_after_adding_skills.csv` | 1,075 | 1,075 |
| `startup_jobs_foreign_after_adding_skills.csv` | 3,543 | 3,543 |
| `tech_jobs_jooble_careerjet_AGNABY_after_adding_skills.csv` | 18,583 | 18,583 |
| **Total** | **775,155** | **775,155** |

This proves row-count/source-file coverage against the designated cleaned-data manifest; it is not a byte-for-byte or cell-by-cell comparison between the CSV and SQLite formats. The implementation uses the SQLite reconstructed from the authorized NADA 11 parts as its database source.

### A3. Salary/work-mode inventory from the approved SQLite

| Salary-estimation status | Rows |
|---|---:|
| Estimated | 735,952 |
| Unverified | 32,206 |
| Actual | 6,937 |
| Not disclosed | 56 |
| Unparseable | 4 |

The new annual USD/EGP/SAR fields are used; **739,484** rows have a populated annual USD center. Old raw salary columns are not used for the analytic averages. Work-mode counts: `not_remote_explicit` 677,472; `remote` 67,336; `unknown_or_unmapped` 30,345; `hybrid` 2. The app and report explicitly do not interpret `not_remote_explicit` as confirmed onsite work.

## B. Phase gates and automated tests

### B1. Phase 1 — backend foundation

Commands:

```bash
cd backend_v2
npm run check
npm test
DATASET_DB_PATH=../data/processed/jobs_cleaned_audited.sqlite3 npm run db:check
```

Outcome after the ML integration: syntax passed for **28 JavaScript files**; **24/24 tests passed**. Unit/integration tests cover schema preflight/read-only behavior, fixture analytics and matching, grouped `role_family` training without approval gates, compressed model round trips, model status/inference without the analytics DB and despite the informational `NO_GO` label audit, dashboard/health, JSON validation, stable errors, and compressed SQLite materialization.

### B2. Phase 2 — analytics and dashboard

`npm test` passed all 24 tests, including these specific metric checks:

- role demand by country keeps the two percentage denominators separate;
- salary metrics use the populated annual USD/EGP/SAR columns rather than legacy salary columns;
- role skill counts, co-occurrences, and work-mode percentages reconcile against fixture records;
- Arab, international, and unknown markets stay separate;
- dashboard/API response fields are suitable for charting.

Manual real-data request: `GET /api/v2/analytics/role?title=Data%20Engineer` returned HTTP 200 and **56,524** ads. It returned U.S. demand 11,268 ads out of 223,430 U.S. ads; India 5,116/53,703; U.K. 4,327/43,819. Top role skills were SQL 39,482 (69.85%), Python 36,943 (65.3581%), AWS 20,157 (35.661%), Azure 19,857 (35.1302%), and Spark 18,790 (33.2425%). Python+SQL co-occurred in 29,093 role ads (51.4702%).

Annual USD examples from new fields: U.S. Data Engineer mean **$156,858.22** (9,659 records; range $90,000–$156,862.50), India **$86,369.28** (5,086; $59,794.12–$156,862.50). Values are predominantly estimated and are not employer-reported guarantees.

### B3. Phase 3 — ML gate and deployment projection

Build command, run against the NADA SQLite reconstructed from the authorized 11 parts:

```bash
DATASET_DB_PATH=../data/processed/jobs_cleaned_audited.sqlite3 npm run analytics:build-deploy-db
```

Outcome:

| Check | Result |
|---|---:|
| `PRAGMA quick_check(1)` | `ok` |
| Jobs/audit rows | 775,155 / 775,155 |
| Skill links | 4,026,953 / 4,026,953 |
| Skills | 1,498 / 1,498 |
| Salary columns | all nine annual min/center/max columns reconciled by nonblank count and sum (floating tolerance `1e-12`) |
| Salary-status groups | all five statuses/counts match exactly |
| Annual USD centers | 739,484 |
| Raw compact SQLite | 279,310,336 bytes |
| Gzip deployment artifact | 79,477,402 bytes |
| Deployment target | below the script’s 200 MiB artifact threshold; raw file alone exceeds a 250 MiB function budget |
| Dashboard snapshot | 18,284 bytes; 775,155 jobs |

The API was started with `VERCEL=1 PORT=4000 node src/server.js`, which selected the gzip DB default. After removing only the local `/tmp` materialization cache, the first real health request decompressed the DB and returned HTTP 200 in **1.092 s**; the materialized SQLite measured 279,310,336 bytes. The final real-data smoke results:

| Request | Result |
|---|---|
| `GET /api/v2` | 200; documentation link `/api/v2/docs` |
| `GET /api/v2/docs` | 200; Markdown reference |
| `GET /api/v2/health` | 200; `read-only-connected`; cold gzip materialization 1.092 s |
| `GET /`, `/dashboard`, `/api/v2/dashboard` | 200 HTML (17,029 bytes) |
| `GET /api/v2/analytics/overview` | 200; 775,155 ads; 217,611 normalized titles; 163 countries; Data Engineer top role 56,524; first live computation 8.164 s |
| `GET /api/v2/analytics/dashboard` before snapshot | 200; 33.3 s; confirms all dashboard calculations on the full compact projection |
| `GET /api/v2/analytics/dashboard` with matching snapshot | 200; 6 ms in the cold-cache local smoke process; 775,155 ads |
| `GET /api/v2/analytics/role?title=Data%20Engineer` | 200 in 4.573 s; detailed demand, skills, salary, mode and combinations |
| `POST /api/v2/ml/skill-to-job-match` with Python + SQL | 200; returns 3 ads at requested limit; `hiringProbability:false` |
| `GET /api/v2/ml/job-family/status` | 200; `MODEL_READY`, `targetField:role_family`; nested label audit remains `NO_GO` but is non-blocking |
| `POST /api/v2/ml/job-family/predict` | 200 on full source; example Data Engineer + Python/SQL/Spark text → `data_engineering` |

A separate local-mode check ran `PORT=4001 node src/server.js` without `VERCEL=1`, thereby selecting the full raw SQLite source path. Health returned `200` in 40 ms, `/api/v2/docs` returned Markdown `200`, and the actual Data Engineer report returned `200` with 56,524 ads in 42.877 s. This verifies local source mode; its full 7.65 GB database is slower than the compact deployment projection.

Global dashboard summary: remote 67,336 (8.6868%); `not_remote_explicit` 677,472 (87.3983%); unknown/unmapped 30,345 (3.9147%); hybrid 2 (0.0003%). Market counts: Arab 22,922 ads; international 746,421; unknown/non-country 5,812. Mean annual USD among records with values: Arab $53,458.89 (22,647 records; 22,637 estimated/10 actual), international $100,708.44 (711,943; 708,600 estimated/3,340 actual/3 unverified). These are descriptive dataset summaries, not controlled wage comparisons.

The Node.js trainer ran against the full read-only SQLite source and fitted `role-family-tfidf-mnb-v1` on all 775,155 stored `role_family` labels across 16 classes. Grouped split: train 612,197, validation 58,010, test 104,948 (19,699 distinct test text groups). Held-out agreement metrics: accuracy 94.1457%, macro-F1 76.6955%, weighted-F1 94.1527%; full per-class scores and confusion matrix are in `reports/job-family-model-evaluation.json`. `description_raw` exists on 26,494 records (3.4179%), so most training examples rely on titles. The model artifact is `models/job-family-model.json.gz` (2,437,083 bytes). Label review provenance is still absent and audit `NO_GO` is shown as a caveat only; it does not disable training or prediction. These metrics are not independent human-reviewed ground-truth accuracy.

## C. Deployment configuration checks

- `vercel.json` and `package.json` parse as JSON.
- `npm run vercel:check` passes locally: Node.js 22 runtime, API function path, rewrites, all seven `includeFiles` assets, compressed SQLite schema/counts, trained-model target/classes, and size target verified. The included assets total **81,991,101 bytes**; gzip DB 79,477,402 bytes; compressed model 2,437,083 bytes; raw DB 279,310,336 bytes.
- `vercel.json` points at `api/[...path].js` and includes the gzip SQLite, compressed `role_family` model, model evaluation, API reference, dashboard HTML, readiness JSON, and generated dashboard snapshot.
- Gzip SQLite is opened through the same read-only schema preflight; the dedicated gzip fixture test passes.
- Vercel root should be `backend_v2/`. **No Vercel deployment or platform package build was performed.** The compressed SQLite is ignored by Git under the data policy and must be provisioned into the deployment working tree before Vercel packages the function.

## D. Issues found during testing and disposition

1. Syntax error in `scripts/audit-job-family-labels.js` Markdown construction: fixed; final syntax test includes the file.
2. `ANALYZE; PRAGMA optimize` tried to write attached read-only source metadata: changed to `ANALYZE main`; final full builder succeeds.
3. Builder fallback referred to source `job_skills` fields that were not required by the app view: changed fallback to use only `skill_id`; remaining analytics/matching SQL uses `record_id` and `skill_id`.
4. Raw compact DB exceeded target: created gzip artifact and a bounded gzip-to-temp read-only path; compressed artifact measures 79,477,402 bytes.
5. Vercel root rewrite originally targeted a non-existent static `/dashboard`; now rewrites to `/api/v2/dashboard`, which serves the bundled HTML.

## E. Reproduction and final gate

```bash
cd backend_v2
npm run check && npm test
DATASET_DB_PATH=data/jobs_analytics.sqlite3.gz npm run db:check
DATASET_DB_PATH=../data/processed/jobs_cleaned_audited.sqlite3 npm run ml:audit-labels
```

The production-like server may be started with `VERCEL=1 PORT=4000 node src/server.js`. The dashboard snapshot is regenerated with the deployment DB by `npm run analytics:build-dashboard`, normally after `npm run analytics:build-deploy-db`.
