# Data-Quality Decision Tree

This diagram defines when the project may publish specific insights. Decisions must be based on measured coverage and documented thresholds agreed by the team.

```mermaid
flowchart TD
    Start([Start with audited dataset]) --> Core[Validate source, schema, duplicates, and missingness]
    Core --> CorePass{Core data-quality checks pass?}
    CorePass -->|No| Remediate[Clean, document limitations, or stop affected analysis]
    Remediate --> Core
    CorePass -->|Yes| General[Publish supported counts and skill-demand summaries with sample context]

    General --> DateCheck{Are posting dates reliable and sufficiently covered?}
    DateCheck -->|Yes| Trend[Enable supported time trends]
    DateCheck -->|No| NoTrend[Do not claim time-based trends]

    General --> SalaryCheck{Are disclosed salaries sufficient and comparable?}
    SalaryCheck -->|Yes| SalaryStats[Show observed salary statistics with currency, period, and sample size]
    SalaryCheck -->|No| NoSalary[Hide comparisons or label coverage as insufficient]
    SalaryStats --> ModelSalary{Does regression pass separate evaluation?}
    ModelSalary -->|Yes| SalaryEstimate[Consider clearly labelled model estimates]
    ModelSalary -->|No| NoEstimate[Show disclosed salaries only]

    General --> LabelCheck{Are reliable, reviewed job-family labels available?}
    LabelCheck -->|Yes| Classification[Evaluate classification]
    LabelCheck -->|No| NoClassification[Document classification as unsupported]

    General --> SkillCheck{Are skill mentions normalized and validated?}
    SkillCheck -->|Yes| SkillUse[Enable matching, co-occurrence, and clustering experiments]
    SkillCheck -->|No| NoSkill[Limit skill outputs and improve taxonomy]
```

## Decision Rules

- A field is not reliable merely because it is present; validate meaning, consistency, and missingness.
- Define numeric sufficiency thresholds after measuring the dataset and reviewing intended comparisons.
- Do not infer salary, dates, locations, or job-family labels that are absent from the source.
- Show an unsupported state or limitation rather than a misleading chart or model output.
