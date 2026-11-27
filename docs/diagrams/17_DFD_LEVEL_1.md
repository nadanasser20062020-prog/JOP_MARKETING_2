# Data Flow Diagram — Level 1

This DFD decomposes the product into major processes and logical data stores. The stores map to the implemented local SQLite schema; application deployment boundaries remain subject to review.

```mermaid
flowchart LR
    Team[Project team]
    Drive[(Read-only source files)]
    Visitor[Visitor]

    P1((P1: Audit, clean, and load))
    P2((P2: Search and analyze))
    P3((P3: Normalize skills and match))
    P4((P4: Validate and return API results))

    D1[(D1: Local SQLite job, source, and import records)]
    D2[(D2: Local SQLite skill taxonomy and job-skill links)]
    D3[(D3: Local SQLite reviewed learning resources)]
    D4[(D4: Local analytical outputs and approved model artifacts)]

    Drive -->|Collected records| P1
    Team -->|Cleaning rules and reviewed definitions| P1
    P1 -->|Validated job records| D1
    P1 -->|Normalized skills and associations| D2
    Team -->|Curated resources| D3

    D1 --> P2
    D2 --> P2
    P2 -->|Documented metrics| D4

    Visitor -->|Search, filters, or temporary skill request| P4
    P4 -->|Search or market-analysis request| P2
    P2 -->|Job results or documented aggregates| P4
    P4 -->|Matching request| P3
    D1 --> P3
    D2 --> P3
    D3 --> P3
    P3 -->|Ranked matches, gaps, and resource references| P4
    P4 -->|Validated response| Visitor
```

## Interpretation

- The visitor interacts with the API-facing process and does not access data stores directly.
- Data preparation is controlled by the project team and does not modify the original Drive source.
- Model artifacts are stored or served only if an evaluation gate is passed; otherwise, results remain in project reports.
