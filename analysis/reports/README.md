# Analysis Reports

Reports should identify the archive run, query or method, metric definition, denominator, filters, sample size, date scope, and limitations. Results describe collected job-ad records only.

`pre_backend/` contains the reproducible pre-backend analysis report, aggregate tables, and charts generated from local SQLite. Do not include raw job descriptions, private input data, or unsupported claims of representativeness, salary comparability, or current listing activity.

`data_cleaning/` contains the loss-preserving cleaning audit: before/after quality reports, source manifest, country/role/skill profiles, actual-only salary statistics, and an inventory/review list for legacy salary estimates. The current run includes all seven declared job sources (775,155 rows); the project SQLite database and full Parquet package remain unavailable for comparison.
