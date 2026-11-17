# Data Workspace

The data workflow uses these directories:

- [`raw/`](raw/README.md): unchanged, authorized source files. Keep actual source data out of Git.
- [`interim/`](interim/README.md): temporary outputs created during cleaning.
- [`processed/`](processed/README.md): reproducible, source-attributed outputs for loading and analysis. The original full exports are left unchanged; this PR adds a reduced Neon Free profile under `processed/neon_free/` by explicit request.
- [`reference/`](reference/README.md): curated skill taxonomy, aliases, and learning-resource metadata with item-specific verification and cost caveats.

The original Drive files are read-only source material. Rebuild steps and interpretation rules are documented in [`scripts/data_cleaning/README.md`](../scripts/data_cleaning/README.md); audit findings and field definitions are in [`docs/data/`](../docs/data/README.md).
