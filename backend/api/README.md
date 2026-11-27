# Frontend API Quick Reference

The implemented HTTP API is versioned at `/api/v1`. For the complete contract, request and response examples, limits, errors, supported filters, and methodology, see [`API_SPECIFICATION.md`](../../docs/software-engineering/API_SPECIFICATION.md).

## Core endpoints

| Endpoint | Use |
|---|---|
| `GET /health` | Backend + local SQLite readiness |
| `GET /api/v1/metadata` | Counts, source coverage, field coverage, snapshot, supported filters |
| `GET /api/v1/overview` | Dashboard KPIs, country counts, top 10 skills, Arab/other represented-market comparison |
| `GET /api/v1/jobs` | Paginated job explorer; exact raw work-mode/experience and reviewed-skill filters |
| `GET /api/v1/jobs/{recordId}` | Advertisement detail and safe source URL |
| `GET /api/v1/roles?q=...` | Normalized-title suggestions |
| `GET /api/v1/roles/{roleId}/analysis` | Country and eligible-skill analysis for a role |
| `GET /api/v1/roles/{roleId}/ads` | Secondary related-ad list |
| `GET /api/v1/markets/compare` | `merged_tech_jobs` Arab vs other represented markets |
| `GET /api/v1/markets/trends` | Historical `international_jobs` monthly totals for 2023 only |
| `GET /api/v1/skills` | Reviewed catalogue and evidence counts |
| `GET /api/v1/skills/co-occurrence?skillId=...` | Reviewed skill relationships |
| `GET /api/v1/skills/{skillId}/resources` | Resource list; `freeOnly=true` means exactly `free_verified` |
| `POST /api/v1/matches` | Temporary Jaccard overlap-based role ranking |
| `GET /api/v1/models/status` | Production/offline/disabled model status |
| `GET /api/v1/methodology` | Definitions and limitations |

## Response handling

Successful responses use `{ data, meta }`, and list data includes `pagination`. Errors use `{ error: { code, message, requestId, details? } }`. A valid no-result search is HTTP 200 with an empty array; database/data unavailability is 503. Skill-match POST input is never persisted or logged. Percentages carry their numerator and denominator.

Frontend requests should use relative paths (for example, `fetch('/api/v1/overview')`). During local development, proxy `/api` through the frontend dev server to Node on port 3000. Do not connect to SQLite from the browser or hardcode localhost into deployed frontend code. Configure cross-origin development with `APP_URL` in `backend/config/app_url.js`.

No salary filter or salary prediction, active-listing claim, classification model, or production clustering result is available. The Jaccard result is a similarity score—not a hiring probability.
