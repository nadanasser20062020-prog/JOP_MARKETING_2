# Container Architecture Diagram

The local SQLite container is implemented. The frontend, API, and application services remain planned; any implementation must access the database only from trusted backend code on the same machine.

```mermaid
flowchart LR
    Visitor[Visitor] --> Web[Web frontend]
    Web --> API[Backend API]
    API --> Services[Application services]
    Services --> DB[(Local SQLite file<br/>data/processed/job_market.sqlite3)]
    Services --> Matching[Skill matching and approved model logic]
    Services --> Resources[Learning-resource catalogue]

    Drive[(Read-only original source files)] --> Prep[Local data preparation and validation]
    Prep --> DB
    Analysis[Local SQL and Python analysis] --> DB
    Analysis --> Reports[Charts and analytical findings]
    Reports --> Web

    Web --> JobSources[External job pages through user-selected links]
    Web --> LearningSites[External learning pages through user-selected links]
```

## Interaction Rules

- The frontend communicates with the backend API; it does not connect directly to the SQLite file.
- The backend opens only a local filesystem database path. There is no remote database service or network database fallback.
- Data preparation, analytical notebooks, and the user-facing application remain separate responsibilities.
- Any future approved model inference runs inside the same backend process; no separate ML service or model server is in scope. Until a model passes its evidence/evaluation gate, its work remains offline and report-only.
- Original source files are read-only inputs; database loading writes only to the local SQLite file.
- External links are opened by the visitor and are not application-controlled services.
