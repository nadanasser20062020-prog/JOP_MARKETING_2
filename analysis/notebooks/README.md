# Python Analysis Notebooks

Store reproducible exploratory-analysis and visualization notebooks here.

Use Pandas and NumPy for analysis and Matplotlib and Seaborn for visualizations. Query the local SQLite file through Python, keep private data out of notebooks, avoid loading large files unnecessarily, and document each notebook's question, data version, transformations, results, and limitations.

`cleaning_data_audit.ipynb` documents the completed loss-preserving cleaning audit over all seven declared job sources (775,155 rows). It checks compact tracked report summaries and, when the cleaned dataset has been restored from Drive to the ignored `data/processed/` path, streams the file to verify its row count without loading it all into memory. It does not modify raw files. Salary amounts are annualized only under the explicit FX/pay-period policy, while synthetic estimates for eligible missing salaries are labeled separately from source-reported amounts. The International CSV came from the user-requested Drive ZIP; its recorded modification date (2026-10-31) is later than the declared audit date (2026-10-28) and is documented as a provenance limitation. See the notebook, `analysis/reports/data_cleaning/final_data_quality_report.md`, and `docs/data/DATA_DICTIONARY.md` for scope, methods, and limitations.
