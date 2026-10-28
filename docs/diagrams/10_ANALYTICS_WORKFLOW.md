# SQL and Python Analytics Workflow

```mermaid
flowchart LR
    DB[(Validated relational database)] --> SQL[Documented SQL queries]
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
- Keep database credentials outside notebooks and source control.
- Record metric definitions, filters, sample sizes, units, and date coverage.
- Reconcile the values selected for the interface against the source queries.
