# Data-Quality Tests

`test_build_site_data.py` covers the staging builder. `test_build_cleaning_audit.py` and `test_finalize_full_cleaning_audit.py` cover loss preservation, salary parsing/annualization, dated FX-policy validation, synthetic-estimate provenance, and full-audit consistency.

Run from the repository root:

```bash
python -m unittest tests.data_quality.test_build_site_data -v
python -m unittest tests.data_quality.test_build_cleaning_audit tests.data_quality.test_finalize_full_cleaning_audit -v
```

Full generated-data counts and foreign-key validation are recorded in the local processed/report outputs and summarized in [`docs/data/DATA_AUDIT.md`](../../docs/data/DATA_AUDIT.md). Raw data, the cleaned dataset, and large row-level reports are not committed.
