# Data Flow Diagram — Level 0

This context-level DFD treats JOP Marketing Intelligence as one process and shows its external actors and data exchanges.

```mermaid
flowchart LR
    Visitor[Visitor / job seeker]
    Team[Project team]
    Drive[(Shared Drive source files)]
    Product((P0: JOP Marketing Intelligence))
    JobBoards[External job-advertisement sites]
    Learning[External learning providers]

    Visitor -->|Search filters, market choices, temporary skill input| Product
    Product -->|Job results, market insights, skill matches, learning links| Visitor
    Team -->|Reviewed data, taxonomy, learning resources, methodology| Product
    Drive -->|Collected source files for controlled processing| Product
    Product -->|Outbound advertisement URLs| JobBoards
    Product -->|Outbound learning-resource URLs| Learning
```

## Boundary Notes

- User-entered skill data is temporary under the proposed D-015 privacy baseline, pending team approval.
- The product links to external sites but does not control them.
- The source files are inputs to a controlled data-preparation process, not a live scraping integration.
