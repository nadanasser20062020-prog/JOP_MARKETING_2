# Database ERD

The core SQLite schema is shown in `docs/diagrams/04_LOGICAL_ERD.md`. The complete cleaned-audit extension—including all 123 cleaned CSV columns and the API rollups—is documented in `docs/diagrams/22_CLEANED_AUDIT_RELATIONAL_ERD.md` and matches migrations `001`–`006`.

A source-specific change to the data model should update the ERD, add a numbered SQLite migration, and include integrity tests. Optional editable/exported diagram formats can be added here when needed.
