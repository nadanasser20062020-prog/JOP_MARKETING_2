# Data Pipeline and Quality Gates

The pipeline preserves original source files and makes each transformation reviewable.

```mermaid
flowchart TD
    Drive[(Collected CSV / ZIP files in shared Drive)] --> Inventory[Read-only inventory and schema inspection]
    Inventory --> Audit[Profile fields, coverage, missingness, and duplicates]
    Audit --> Feasibility{Are required fields usable?}
    Feasibility -->|No| Limitations[Document unsupported fields and revise feature scope]
    Feasibility -->|Yes| Staging[Create controlled working copy or staging records]
    Staging --> Normalize[Normalize titles, skills, locations, dates, and units where supported]
    Normalize --> Deduplicate[Apply documented duplicate rules]
    Deduplicate --> Validate[Validate data contract and quality rules]
    Validate --> Quality{Quality checks pass?}
    Quality -->|No| Review[Review failures and update cleaning rules]
    Review --> Normalize
    Quality -->|Yes| Load[Load approved records into relational database]
    Load --> Verify[Verify counts, keys, and relationships]
    Verify --> Downstream[SQL analysis, Python analysis, ML experiments, and website]
```

## Gate Requirements

- Do not modify the original Drive files.
- Preserve source values and record transformation decisions.
- Do not load data until the data dictionary and relational model are reviewed.
- Send failed quality checks back for review; do not silently discard or invent values.
- Record the loaded dataset version and counts for downstream analyses.
