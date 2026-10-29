# Backend and Data Services

This directory contains the planned server-side API and application services.

- [`api/`](api/README.md): request validation, routing, and response contracts.
- [`services/`](services/README.md): job search, market metrics, skill matching, and resource logic.

The backend is the only application layer that should access database credentials. The browser must not connect directly to Neon. See [`docs/WEB_APP_PLAN.md`](../docs/WEB_APP_PLAN.md) and [`API_SPECIFICATION.md`](../docs/software-engineering/API_SPECIFICATION.md).
