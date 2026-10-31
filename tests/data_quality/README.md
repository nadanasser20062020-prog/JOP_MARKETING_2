# Data-Quality Tests

`test_build_site_data.py` covers source-specific skill parsing, duplicate-token removal, conservative skill alias matching, ambiguous-term exclusion, salary disclosure handling, salary provenance, and generated record-key uniqueness.

Run from the repository root:

```bash
python -m unittest tests.data_quality.test_build_site_data -v
```

Full generated-data counts and foreign-key validation are recorded in `data/processed/data_quality_report.json` and documented in [`docs/data/DATA_AUDIT.md`](../../docs/data/DATA_AUDIT.md). The processed files and raw source data are not committed.
