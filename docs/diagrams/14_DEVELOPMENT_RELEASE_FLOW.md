# Development and Release Flow

```mermaid
flowchart TD
    Backlog[Project task or GitHub Issue] --> Ready{Objective, inputs, dependencies, and acceptance criteria clear?}
    Ready -->|No| Refine[Clarify scope or resolve dependency]
    Refine --> Backlog
    Ready -->|Yes| Branch[Create a scoped working branch]
    Branch --> Work[Implement or update documentation]
    Work --> Checks[Run relevant tests and checks]
    Checks --> Pass{Checks and acceptance criteria pass?}
    Pass -->|No| Fix[Address failures]
    Fix --> Work
    Pass -->|Yes| PR[Open pull request linked to task]
    PR --> Review[Peer review]
    Review --> Approved{Approved?}
    Approved -->|No| Changes[Address review feedback]
    Changes --> Work
    Approved -->|Yes| Merge[Merge according to repository policy]
    Merge --> Stage[Deploy or validate in staging/demo environment]
    Stage --> Smoke{Critical user flows pass?}
    Smoke -->|No| Rollback[Rollback or disable affected feature]
    Smoke -->|Yes| Release[Record release and known limitations]
    Release --> Done([Done])
```

## Process Notes

- Keep tasks small enough for focused review.
- Do not bypass data-quality or model-evaluation gates to meet a release date.
- Update requirements, diagrams, ADRs, and traceability records when the design changes.
