# System Architecture

**Status:** Proposed logical architecture. Select implementation technologies after the data audit and team review.

## Architecture Goals

- Separate the browser interface from database credentials and data access.
- Reuse a normalized relational source of truth for analysis and application queries.
- Keep analytics and ML experiments reproducible and independently reviewable.
- Make recommendations explainable and expose data limitations.
- Support English and Arabic interfaces without duplicating the underlying data.

## System Context

The system serves visitors exploring the team's collected job advertisements. The project team prepares and validates the data, operates the application, and maintains the learning-resource catalogue. Visitors follow outbound links to original job postings and external learning providers; those sites are outside the application's control.

## Proposed Container View

See the [system context](../diagrams/01_SYSTEM_CONTEXT.md), [container architecture](../diagrams/02_CONTAINER_ARCHITECTURE.md), [backend component](../diagrams/03_BACKEND_COMPONENTS.md), [DFD Level 0](../diagrams/16_DFD_LEVEL_0.md), [DFD Level 1](../diagrams/17_DFD_LEVEL_1.md), and [deployment](../diagrams/12_DEPLOYMENT_VIEW.md) diagrams. These are conceptual; deployment boundaries and selected technologies remain to be confirmed.

## Component Responsibilities

| Component | Responsibility | Must not do |
|---|---|---|
| Web frontend | Render pages, collect temporary search or skill inputs, present results and errors, support both locales | Connect directly to the database or contain database credentials |
| Backend API | Validate requests, apply pagination and filters, call application services, enforce response contracts | Trust user input or expose database error details |
| Application services | Implement search, aggregates, market comparison, skill matching, and resource lookup | Present unsupported metrics as facts |
| PostgreSQL/Neon | Store normalized job, company, location, skill, source, and resource records | Store unreviewed raw data as the only system of record without provenance |
| Data preparation | Audit, clean, standardize, deduplicate, and load collected advertisements | Modify original source files in place |
| Analysis and ML workflows | Produce documented analysis, experiments, and validated model artifacts | Train or publish models without quality gates |
| External job and learning sites | Provide linked original content | Be treated as controlled or guaranteed-available dependencies |

## Data Flow

1. The team inventories collected files and records a data dictionary.
2. Cleaning and standardization produce a documented dataset without changing source files.
3. Validated data is loaded into the relational database.
4. SQL and Python workflows query the database and produce analytical results.
5. The backend serves approved read operations and temporary matching requests.
6. The frontend renders results with sample counts, source links, and limitations.
7. Visitors may navigate to external job or learning pages; the application does not control their availability.

## Trust Boundaries

- **Browser to backend:** Treat all query parameters and skill input as untrusted. Validate length, format, and allowed values.
- **Backend to database:** Use server-side credentials with least privilege and parameterized queries.
- **Application to external sites:** Open only validated URLs and clearly identify external destinations.
- **Team workstation to repository:** Keep credentials, large raw files, and sensitive records outside Git.

## Failure Behavior

- Database outage: return a generic service-unavailable response and show a recoverable interface state.
- Empty result: return a valid empty collection with pagination metadata.
- Model unavailable: disable or clearly mark matching/model-dependent output; do not fabricate a fallback score.
- External link unavailable: retain the advertisement record but indicate that source availability is not guaranteed.
- Partial data coverage: show missing values and sample coverage explicitly.

## Architecture Decisions Still Open

Frontend framework, backend framework, hosting platform, deployment topology, model-serving method, environment separation, database plan/region, and API documentation tooling are unresolved. Track approved decisions in `adr/`.
