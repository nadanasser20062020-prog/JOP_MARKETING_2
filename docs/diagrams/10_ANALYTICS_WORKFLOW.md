# SQL and Python Analytics Workflow

```mermaid
flowchart LR
    DB[(Local SQLite database file)] --> SQL[Documented SQL queries]
    SQL --> Python[Python analysis environment]
    Python --> Pandas[Pandas data frames]
    Pandas --> NumPy[NumPy calculations and transformations]
    Pandas --> Charts[Matplotlib and Seaborn visualizations]
    NumPy --> Charts
    SQL --> Reconcile[Metric and sample-count reconciliation]
    Charts --> Reconcile
    Reconcile --> Findings[Reviewed findings and limitations]
    Findings --> Dashboard[Approved website metrics]
    Findings --> Report[Project report and presentation]
```

## Controls

- Use SQL for reproducible aggregation and filtering; use Python for exploration, validation, and visualization.
- Open the local SQLite file through Python; keep private data and generated database files out of notebooks and source control.
- Record metric definitions, filters, sample sizes, units, and date coverage.
- Reconcile the values selected for the interface against the source queries.
