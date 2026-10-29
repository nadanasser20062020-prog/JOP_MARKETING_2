# Job Discovery Activity Diagram

```mermaid
flowchart TD
    Start([Start]) --> OpenExplorer[Open job explorer]
    OpenExplorer --> Search[Enter a search term and choose supported filters]
    Search --> Validate{Are the search and filters valid?}
    Validate -->|No| ExplainInput[Show validation guidance]
    ExplainInput --> Search
    Validate -->|Yes| Query[Request matching advertisements]
    Query --> Available{Is the service available?}
    Available -->|No| ServiceError[Show a recoverable service error]
    Available -->|Yes| Results{Are there matching records?}
    Results -->|No| EmptyState[Show no-results state and allow filter changes]
    EmptyState --> Search
    Results -->|Yes| List[Show paginated results and sample context]
    List --> Select[Select an advertisement]
    Select --> Detail[Show available details and missing fields]
    Detail --> Source{Is a valid source link available?}
    Source -->|Yes| OpenSource[Open the original advertisement]
    Source -->|No| NoSource[Explain that no source link is available]
    OpenSource --> End([End])
    NoSource --> End
    ServiceError --> End
```

## Data Integrity Notes

The list and detail page display only audited fields. Missing salary, employer, location, or date values remain missing and are never converted to fabricated values.
