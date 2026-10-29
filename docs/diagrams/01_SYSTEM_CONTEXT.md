# System Context Diagram

This diagram shows the product's external actors and dependencies. It does not imply that the application directly scrapes external job boards or learning providers.

```mermaid
flowchart LR
    JobSeeker[Engineer / job seeker]
    Reviewer[Project reviewer]
    Team[Project team]
    Drive[(Shared Drive source files)]
    Product[JOP Marketing Intelligence]
    JobBoards[External job-advertisement sources]
    Learning[External learning-resource providers]

    JobSeeker -->|searches, compares, enters skills| Product
    Reviewer -->|reviews evidence and limitations| Product
    Team -->|audits, prepares, and maintains project data| Product
    Team -->|reads collected files| Drive
    Drive -->|read-only source data| Product
    Product -->|opens original advertisement links| JobBoards
    Product -->|opens curated learning links| Learning
```

## Boundary Notes

- The project team owns the transformation and presentation of its collected sample.
- The original Drive files remain read-only source material.
- External job and learning websites control their own availability and content.
- The product should not imply that it has complete coverage of an external labor market.
