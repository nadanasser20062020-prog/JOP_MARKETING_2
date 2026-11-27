# Unit Tests

Unit tests cover isolated business rules and data-access behavior. Run all tests with:

```bash
python -m unittest discover -s tests -v
```

The SQLite tests use temporary local files to verify migration checksums, repeat-safe imports, local-only path configuration, processed-file loading, row counts, and foreign-key enforcement without modifying the demonstration database.
