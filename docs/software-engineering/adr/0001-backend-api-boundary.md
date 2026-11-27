# ADR-0001: Route Browser Data Access Through a Node.js Backend API

- **Status:** Accepted and implemented
- **Date:** 2026-10-28
- **Decision owner:** Project owner
- **Related requirements:** NFR-004, NFR-005, FR-028

## Context

The website reads a local SQLite database and accepts temporary skill-matching requests. The browser is public and untrusted; it must not receive the database path or direct file access. The initial product has no accounts or persistent skill profiles.

## Decision

All browser data access passes through one Node.js 22 HTTP API. The API uses parameterized SQL and opens SQLite read-only. The local demonstration database is `data/processed/job_market.sqlite3`; `JOP_DATABASE_PATH` may point to another local path. Connection URLs and remote database paths are rejected. Vercel uses the same Node handler only when the SQLite file is included in the deployment artifact; it cannot access a developer's computer.

## Alternatives Considered

- **Direct browser-to-SQLite access:** Rejected because a browser must not expose or open a local database file.
- **Hosted/remote database service:** Not used; the user specified a local-only database and no hosted database fallback.
- **Static exports only:** Rejected for the local product because interactive filters, role analytics, and matching use the relational schema.

## Consequences

- SQLite path and content stay server-side; no database credentials are needed.
- The Node API is responsible for validation, pagination, error behavior, privacy, and safe output.
- Python remains the data loader and offline analysis runtime; it is not invoked by online API requests.
- A full-data Vercel deployment requires a packaged SQLite file and may be constrained by file size/runtime limits. Local full-data operation remains the supported mode unless an actual deployment is verified.

## Review Trigger

Revisit only if the user explicitly changes the local-only storage boundary. Do not expose SQLite as a static asset or silently add a network database fallback.
