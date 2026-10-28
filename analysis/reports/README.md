# Analysis Reports

Store reviewed analytical reports, chart exports approved for use, and evidence supporting website metrics here.

Every reported value must identify its source query or notebook, sample size, units, date coverage, and relevant limitations. Do not store restricted raw data in reports.

`data_cleaning/` includes the tracked final Markdown quality report, source manifest, and compact aggregate summaries used by the cleaning notebook. The full local run also emits larger review tables, a row-level change log, and the processed dataset; those generated files are intentionally excluded from Git. The run covers all seven declared job sources (775,155 rows). Annualized actuals and labeled synthetic estimates are reported separately. The external project SQLite/Parquet reconciliation was unavailable; see the final report for provenance and limitations.
