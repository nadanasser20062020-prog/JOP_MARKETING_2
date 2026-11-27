# Cleaned-audit SQLite database bundle

The full-fidelity `jobs_cleaned_audited.sqlite3` database is stored in the existing shared Google Drive folder **Nada** (directly in the folder root; no new Drive subfolder was used for the upload):

[Open Nada in Google Drive](https://drive.google.com/drive/folders/1CGikDaVWRISqJjsEbGzlxDIBFiEIudla)

The database is 7,649,681,408 bytes (about 7.65 GB), so the Drive upload is one gzip stream split into 11 sequential parts, each below the 100 MB per-file upload limit. The 11 parts are not independently usable. Also in Nada are the part manifest and reassembly instructions:

- `jobs_cleaned_audited.sqlite3.gz.part-001` through `jobs_cleaned_audited.sqlite3.gz.part-011`
- `jobs_cleaned_audited_manifest.json` — part sizes and SHA-256 digests, plus database validation details
- `jobs_cleaned_audited_README.txt` — download and reassembly instructions

Download all 11 parts into one directory and reassemble on Linux, macOS, or WSL:

```bash
cat jobs_cleaned_audited.sqlite3.gz.part-* | gzip -dc > jobs_cleaned_audited.sqlite3
sha256sum jobs_cleaned_audited.sqlite3
```

Expected database SHA-256:

```text
582a141af4c0bde4b941dde062785f465825d12ddacd51f07c924d5f352a54ac
```

The database contains 775,155 jobs, 775,155 full-fidelity cleaning-audit rows (123 source columns), and 4,026,953 job-skill links. It passed `PRAGMA integrity_check` (`ok`) with zero foreign-key violations. It is separate from the operational `job_market.sqlite3` database.

The SQLite database and all generated data remain excluded from Git by `/data/processed/*`; this page is a small pointer and validation record only. The upload did not change or replace any of the pre-existing files in Nada, and no Drive sharing permissions were broadened.
