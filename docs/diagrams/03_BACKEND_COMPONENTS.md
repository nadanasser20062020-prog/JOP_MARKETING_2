# Backend Component Diagram

The diagram shows proposed responsibilities behind the API. It is independent of the final programming framework.

```mermaid
flowchart LR
    Browser[Web frontend] --> Router[HTTP router and API versioning]
    Router --> Validation[Request validation and response mapping]
    Validation --> Jobs[Job search and detail service]
    Validation --> Markets[Market metrics and comparison service]
    Validation --> Skills[Skill catalogue and demand service]
    Validation --> Matching[Skill matching service]
    Validation --> Resources[Learning-resource service]

    Jobs --> Repositories[Data repositories]
    Markets --> Repositories
    Skills --> Repositories
    Matching --> Taxonomy[Skill normalization and taxonomy]
    Matching --> Repositories
    Matching -. optional after evaluation .-> Model[Approved model component]
    Resources --> Repositories
    Repositories --> Database[(Relational database)]
```

## Component Boundaries

- **Router:** Maps versioned paths and HTTP methods to application operations.
- **Validation:** Enforces input size, formats, allowed filters, and safe response behavior.
- **Services:** Implement product rules without tying them to a specific user-interface framework.
- **Repositories:** Own database queries and map rows to application-level records.
- **Skill taxonomy:** Resolves reviewed aliases to canonical skills while preserving unrecognized input for the current request only, subject to D-015.
- **Optional model component:** May be called only after its task-specific data and evaluation gates pass.
