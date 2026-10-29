# Skill-Matching Sequence Diagram

This sequence describes the proposed request flow. The non-persistence behavior is subject to team approval under D-015.

```mermaid
sequenceDiagram
    autonumber
    actor Visitor
    participant UI as Web UI
    participant API as Backend API
    participant Validator as Request Validator
    participant Match as Matching Service
    participant Repo as Data Repository
    participant DB as Relational Database

    Visitor->>UI: Enter skills and optional supported preferences
    UI->>API: Submit matching request
    API->>Validator: Validate request size and fields
    Validator->>Validator: Normalize recognized skill aliases
    alt Request is invalid
        Validator-->>API: Validation errors
        API-->>UI: User-safe validation response
        UI-->>Visitor: Explain required correction
    else Request is valid
        Validator-->>API: Normalized temporary input
        API->>Match: Request ranked matches
        Match->>Repo: Retrieve relevant job-skill records
        Repo->>DB: Execute parameterized read queries
        DB-->>Repo: Job, skill, and evidence records
        Repo-->>Match: Candidate records
        Match->>Match: Calculate coverage, matched skills, and gaps
        Match-->>API: Ranked results with explanations
        API-->>UI: Matching response and limitations
        UI-->>Visitor: Show results and learning links
    end
```

## Security and Privacy Boundaries

- The browser does not access the database directly.
- The API validates all user-controlled fields.
- The repository uses parameterized read operations.
- Matching input should not be stored or written to request-body logs under the proposed D-015 default.
