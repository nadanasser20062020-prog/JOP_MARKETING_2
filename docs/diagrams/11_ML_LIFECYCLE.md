# Machine Learning Lifecycle and Release Gates

```mermaid
flowchart TD
    Data[Audited and normalized job data] --> Features[Create task-appropriate features]
    Features --> SkillData[Skill vectors or normalized skill sets]
    Features --> TextData[Reviewed titles and descriptions]
    Features --> SalaryData[Disclosed and comparable salaries]

    SkillData --> Cluster[Clustering experiment]
    TextData --> Labels{Are reviewed role labels available?}
    Labels -->|Yes| Classify[Classification experiment]
    Labels -->|No| ClassifyNoGo[Document why classification is not supported]
    SalaryData --> SalaryGate{Are salary labels sufficient and comparable?}
    SalaryGate -->|Yes| Regress[Regression experiment]
    SalaryGate -->|No| SalaryNoGo[Do not publish salary estimates]

    Cluster --> Evaluate[Compare with baselines and review errors or examples]
    Classify --> Evaluate
    Regress --> Evaluate
    Evaluate --> Quality{Does the task pass its evaluation gate?}
    Quality -->|No| ReportOnly[Document results and limitations; do not expose model]
    Quality -->|Yes| Card[Complete Model Card and review intended use]
    Card --> DeployGate{Approved for user-facing use?}
    DeployGate -->|Yes| Product[Integrate with explanation and safeguards]
    DeployGate -->|No| ReportOnly
    ClassifyNoGo --> ReportOnly
    SalaryNoGo --> ReportOnly
```

## Interpretation

- Clustering does not require labels, but clusters need human interpretation and validation.
- Classification requires reliable labels and per-class evaluation.
- Regression requires enough disclosed salaries with compatible units and periods.
- A model that fails its gate may still be documented as an experiment, but its outputs must not be presented as validated product advice.
- The explainable skill-coverage baseline is evaluated separately and remains distinct from a hiring-probability claim.
