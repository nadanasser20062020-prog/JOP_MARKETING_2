# Job-Advertisement Data Record State Diagram

This state machine describes the proposed preparation lifecycle for an individual source record. These are conceptual processing states; the implementation may track them through pipeline logs rather than a status column in the production database.

```mermaid
stateDiagram-v2
    [*] --> Discovered
    Discovered --> RawCaptured: authorized source record copied without edits
    RawCaptured --> Audited: source and fields inspected
    Audited --> Staged: record passes initial intake checks
    Audited --> Rejected: unusable or not permitted for processing
    Staged --> Normalizing: apply documented cleaning rules
    Normalizing --> Validating: preserve source and normalized values
    Validating --> Accepted: quality rules pass
    Validating --> Quarantined: quality rules fail
    Quarantined --> Normalizing: reviewed correction or approved rule change
    Quarantined --> Rejected: record cannot be repaired safely
    Accepted --> Loaded: database constraints and load checks pass
    Loaded --> AvailableForAnalysis: included in approved dataset version
    Loaded --> Quarantined: post-load validation failure
    AvailableForAnalysis --> Superseded: later dataset version replaces record
    Rejected --> [*]
    Superseded --> [*]
```

## State Rules

- Raw source files remain unchanged; transformations create separate outputs.
- Every transition should be traceable to a documented validation or transformation rule.
- A record that fails validation is quarantined or rejected, not silently deleted.
- `AvailableForAnalysis` does not mean an advertisement is still active on its source website.
