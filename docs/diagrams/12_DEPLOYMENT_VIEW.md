# Logical Deployment View

This diagram shows a platform-neutral deployment proposal. Hosting providers and environment configuration remain open decisions.

```mermaid
flowchart LR
    Developer[Developer workstation]
    Repo[GitHub repository and pull request checks]
    Visitor[Visitor browser]

    subgraph Local[Local development environment]
        LocalWeb[Frontend development server]
        LocalAPI[Backend service]
        LocalDB[(Non-production database or test fixture)]
        LocalWeb --> LocalAPI
        LocalAPI --> LocalDB
    end

    subgraph Shared[Shared demonstration environment: provider TBD]
        Web[Deployed frontend]
        API[Deployed backend]
        DB[(PostgreSQL / Neon under consideration)]
        Secrets[Server-side environment secrets]
        Web --> API
        API --> DB
        Secrets -. configured for .-> API
    end

    Developer --> Repo
    Repo -->|reviewed deployment| Shared
    Visitor --> Web
    Drive[(Read-only source files)] -->|controlled data preparation| DB
```

## Environment Rules

- Local, shared test, and demonstration settings must not reuse production secrets where separation is available.
- The browser receives no database credentials.
- Data preparation and database migrations are reviewed independently of frontend deployment.
- Do not modify source files in Drive as part of a deployment.
- If separate environments are unavailable, document how test operations are prevented from overwriting demonstration data.
