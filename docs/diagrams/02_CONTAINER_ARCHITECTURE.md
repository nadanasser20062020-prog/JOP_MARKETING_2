# Container Architecture Diagram

This is a proposed logical container view. Technology and hosting choices remain open.

```mermaid
flowchart LR
    Visitor[Visitor] --> Web[Web frontend]
    Web --> API[Backend API]
    API --> Services[Application services]
    Services --> DB[(Relational database: PostgreSQL / Neon under consideration)]
    Services --> Matching[Skill matching and approved model logic]
    Services --> Resources[Learning-resource catalogue]

    Drive[(Shared Drive source files)] --> Prep[Data preparation and validation]
    Prep --> DB
    Analysis[SQL and Python analysis] --> DB
    Analysis --> Reports[Charts and analytical findings]
    Reports --> Web

    Web --> JobSources[External job sources through user-selected links]
    Web --> LearningSites[External learning providers through user-selected links]
```

## Interaction Rules

- The frontend communicates with the backend API; it does not connect directly to the database.
- Data preparation, analytical notebooks, and the user-facing application are separate responsibilities.
- Model logic may be served by the backend only after passing its evaluation gate; otherwise, model work remains report-only.
- External links are opened by the visitor and are not application-controlled services.
