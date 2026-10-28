# ADR-0001: Route Browser Data Access Through a Backend API

- **Status:** Proposed
- **Date:** 2026-10-28
- **Decision owners:** Project team
- **Related requirements/tasks:** NFR-004, NFR-005, T14

## Context

The application needs to read job-market data from a relational database and process temporary skill-matching requests. A browser client is a public, untrusted environment and cannot safely protect database credentials. The initial release does not require user accounts or persistent skill profiles.

## Decision

Propose that browser requests pass through a server-side backend API. The backend validates requests, accesses the database using server-side credentials, and returns only the data required by the user interface. This proposal requires team approval before implementation.

## Alternatives Considered

- **Direct browser-to-database access:** Rejected as the default because it can expose credentials or database access rules to the public client.
- **Static exported files only:** Could reduce backend complexity but may not support the required filtering, comparisons, and matching without additional decisions.

## Consequences

- Database credentials can remain outside the browser bundle.
- The backend becomes an operational component that must be tested and deployed.
- API contracts, validation, error handling, and server-side monitoring are required.
- Matching input can be processed without storing it if the backend avoids persistence and request-body logging.

## Review Trigger

Revisit this proposal if the selected hosting platform provides a reviewed alternative with equivalent credential isolation, data access control, observability, and privacy behavior.
