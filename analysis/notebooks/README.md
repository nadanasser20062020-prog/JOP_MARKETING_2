# Python Analysis Notebooks

Store reproducible exploratory-analysis and visualization notebooks here.

Use Pandas and NumPy for analysis and Matplotlib and Seaborn for visualizations. Query the local SQLite file through Python, keep private data out of notebooks, avoid loading large files unnecessarily, and document each notebook's question, data version, transformations, results, and limitations.

`cleaning_data_audit.ipynb` documents and checks the loss-preserving cleaning run. It reads the generated coverage reports and compressed dataset incrementally; it does not modify raw files or fill salary values. The current run includes all seven declared job sources (775,155 rows), including the International historical CSV extracted from the user-requested Drive ZIP. It does not claim comparison with the absent project SQLite database or Parquet archive package.
