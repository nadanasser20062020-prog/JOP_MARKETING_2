# API Specification

**Status:** Proposed contract for team review; no API has been implemented. Route names and field details must be aligned with the audited schema and selected backend framework.

## Design Principles

- Use a versioned, resource-oriented HTTP API. Proposed base path: `/api/v1`.
- Keep database access server-side; do not expose database credentials to the browser.
- Validate and allowlist query parameters. Use parameterized database operations.
- Return consistent pagination, empty-result, validation, and failure behavior.
- Do not persist user-entered skills in the initial release.
- Return observed advertisement data separately from analytical or model-generated results.

## Proposed Endpoints

| Method and path | Purpose | Inputs and conditions |
|---|---|---|
| `GET /health` | Check service health for operations | Must not expose secrets or internal infrastructure details |
| `GET /api/v1/metadata` | Return available markets, date coverage, supported filters, and data freshness | Only include verified fields and coverage |
| `GET /api/v1/overview` | Return dashboard aggregates | Optional market/date filters where supported; include sample counts |
| `GET /api/v1/jobs` | Search and list job advertisements | Search term, supported filters, pagination, and allowlisted sort field |
| `GET /api/v1/jobs/{jobId}` | Return one advertisement | Stable identifier; return not found for unknown IDs |
| `GET /api/v1/markets/compare` | Compare supported metrics across selected markets | Require compatible metric definitions and units |
| `GET /api/v1/markets/trends` | Return time-series aggregates | Available only after date-quality gate; specify metric, market, and period |
| `GET /api/v1/skills` | Search or list normalized skills and demand aggregates | Optional market/role filters supported by the data |
| `GET /api/v1/skills/co-occurrence` | Return related-skill aggregates | Include a documented measure and sample support |
| `POST /api/v1/matches` | Return temporary skill-based matches | Request contains a bounded list of skills and optional supported preferences; do not persist input |
| `GET /api/v1/skills/{skillId}/resources` | Return reviewed learning resources for a skill | Include language and verified access status |
| `GET /api/v1/methodology` | Return or link to the data and analysis methodology | Content should match the current implementation |

## Job List Query Contract

The following query parameters are proposed and must be restricted to audited fields:

- Search text.
- Country or location identifier.
- Normalized role or skill identifier.
- Work arrangement and experience level.
- Salary minimum/maximum only when salary units are comparable.
- Page number and page size.
- Sort key and sort direction from an explicit allowlist.

Proposed pagination defaults are page 1 and 20 records per page, with a maximum of 100 records per page. Confirm these limits through performance testing.

## Matching Request Contract

The request should contain a list of user-entered or selected skills and optional country/work-arrangement preferences. Validate that the request is not empty, enforce a reasonable maximum input size, normalize recognized aliases, and preserve unrecognized input only for the current request. Do not include the skill list in application logs or persist it to a user profile.

A successful response should include:

- Ranked job or role identifiers and display summaries.
- A clearly named skill-coverage score and its definition.
- Skills matched and skills missing for each result.
- Evidence count or source sample where practical.
- A warning that skill coverage is not a hiring probability.

## Response and Error Conventions

Successful list responses should provide the result collection and pagination metadata. Detail responses should identify the requested resource. Errors should provide a stable machine-readable error category, a user-safe message, and a request/correlation identifier where available. Internal stack traces, SQL messages, credentials, and sensitive inputs must never be returned.

| HTTP status | Use |
|---|---|
| `200` | Successful read or matching request |
| `400` | Invalid query or request format |
| `404` | Unknown resource identifier |
| `422` | Structurally valid request that cannot be processed under current data rules |
| `429` | Request rate or resource limit exceeded, if rate limiting is enabled |
| `500` | Unexpected internal failure with a generic response |
| `503` | Database or required service temporarily unavailable |

A valid search with no results should return a successful empty collection, not a server error.

## Security and Compatibility

- Validate path parameters, request sizes, sort keys, filters, and text lengths.
- Avoid reflecting unescaped user input in responses.
- Apply rate limits to expensive public operations if required by the hosting environment.
- Version incompatible API changes; keep the current version stable during the demonstration.
- Finalize exact schemas and examples after T01–T05 and the interface design review.
