# Job Search Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Visitor
    participant UI as Web UI
    participant API as Backend API
    participant Validator as Query Validator
    participant JobService as Job Search Service
    participant Repository as Data Repository
    participant DB as Relational Database

    Visitor->>UI: Enter search text and select supported filters
    UI->>API: Request a job page
    API->>Validator: Validate filters, sorting, and pagination
    alt Invalid query
        Validator-->>API: Validation failure
        API-->>UI: Safe validation response
        UI-->>Visitor: Show correction guidance
    else Valid query
        Validator-->>API: Normalized query parameters
        API->>JobService: Search for advertisements
        JobService->>Repository: Request filtered, paginated records
        Repository->>DB: Execute parameterized query
        DB-->>Repository: Matching records and total count
        Repository-->>JobService: Result page
        JobService-->>API: Results with sample and page metadata
        API-->>UI: Job list response
        UI-->>Visitor: Render results or empty state
        Visitor->>UI: Select an advertisement
        UI->>API: Request job details
        API->>Repository: Retrieve detail by stable identifier
        Repository->>DB: Read job and related records
        DB-->>Repository: Detail record and relationships
        Repository-->>API: Detail response or not found
        API-->>UI: Job detail response
        UI-->>Visitor: Show available details and source link
    end
```

## Contract Notes

- Filter and sort options must be allowlisted and supported by the audited schema.
- The database query is parameterized and paginated.
- A valid search with no matches returns an empty result state.
- Missing detail fields remain unavailable rather than being inferred.
