# Data Workspace

The data workflow uses these directories:

- [`raw/`](raw/README.md): unchanged, authorized source files. Keep actual data files out of Git.
- [`interim/`](interim/README.md): temporary outputs created during cleaning.
- [`processed/`](processed/README.md): final cleaned, standardized, validated dataset for loading and analysis. Actual dataset files remain outside Git.
- [`reference/`](reference/README.md): approved small reference catalogues such as skill aliases and learning-resource metadata.

The original Drive files are read-only source material. See [`docs/data/`](../docs/data/README.md) for audit and data-dictionary documentation.
