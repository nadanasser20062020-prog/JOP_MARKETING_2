# Logical Entity-Relationship Diagram

**Status:** Aligns with the implemented local SQLite schema in `database/migrations/001_initial_sqlite_schema.sql` and `002_full_archive_provenance.sql`. The domain tables and foreign-key constraints are executable; this diagram describes the complete local data model rather than a hosted database design.

```mermaid
erDiagram
    DATA_SOURCES {
        string source_dataset PK
        string display_name
        string notes
        string source_kind
        string snapshot_bucket
        string date_semantics
        string listing_status
        int source_file_count
        int source_row_count
    }
    SOURCE_FILES {
        string source_dataset PK, FK
        string source_file PK
        string source_file_id UK
        string source_dataset_original
        string physical_file_name
        string logical_file_name
        string file_format
        string file_role
        string archive_member_name
        int byte_size
        string sha256
        int source_row_count
        int archive_member_count
        string snapshot_group
        string snapshot_type
        string notes
    }
    IMPORT_RUNS {
        int import_run_id PK
        string run_status
        string started_at
        string finished_at
        string pipeline_version
        string source_fingerprint
        text quality_report
        string notes
        string source_archive_run_id
        string archive_generated_on_utc
        string archive_generator
        string archive_build_status
        int archive_source_file_count
        int archive_job_rows
        int archive_job_skill_rows
    }
    IMPORT_RUN_FILES {
        int import_run_id PK, FK
        string source_dataset PK, FK
        string source_file PK, FK
        int rows_read
        int rows_loaded
        int rows_rejected
        string import_status
        string notes
        string source_file_id
        int job_rows_emitted
        int job_skill_rows_emitted
        int reference_rows_emitted
        string output_tables
        string processing_role
    }
    JOBS {
        string record_id PK
        string source_dataset FK
        string source_file FK
        int source_row_number
        string source_record_id
        string title
        string company
        string country
        string city
        string region
        text description
        string posted_at
        string source_updated_at
        string salary_raw
        string salary_currency
        string salary_basis
        string source_url
        string listing_status
        string snapshot_type
        string data_quality_flags
    }
    SKILLS {
        string skill_id PK
        string canonical_name
        string category
        string match_policy
        string review_status
        int observed_alias_count
        int observed_source_count
        int observed_job_skill_occurrences
        string notes
    }
    SKILL_ALIASES {
        string alias_normalized PK
        string skill_id PK, FK
        string alias_label
        string alias_type
        string match_policy
        string review_status
        int observed_source_count
        int observed_job_skill_occurrences
        string notes
    }
    JOB_SKILLS {
        string record_id PK, FK
        string skill_id PK, FK
        string source_dataset FK
        string source_file FK
        string skill_raw
        string skill_normalized
        string skill_category
        string skill_match_policy
        string skill_review_status
        string skill_provenance
        string skill_status
    }
    SKILL_OBSERVATIONS {
        string source_dataset PK, FK
        string skill_normalized PK
        string skill_raw PK
        int occurrence_count
    }
    LEARNING_RESOURCES {
        string resource_id PK
        string title
        string provider
        string resource_type
        string level
        string access_status
        string cost_status
        string account_requirement
        string credential
        string resource_url
        string verification_status
        string verified_on
        string notes
    }
    LEARNING_RESOURCE_SKILLS {
        string resource_id PK, FK
        string skill_id PK, FK
    }
    LEARNING_RESOURCE_LANGUAGES {
        string resource_id PK, FK
        string language_label PK
    }

    DATA_SOURCES ||--o{ SOURCE_FILES : identifies
    SOURCE_FILES ||--o{ JOBS : provides
    DATA_SOURCES ||--o{ SKILL_OBSERVATIONS : records
    IMPORT_RUNS ||--o{ IMPORT_RUN_FILES : records
    SOURCE_FILES ||--o{ IMPORT_RUN_FILES : accounts_for
    SKILLS ||--o{ SKILL_ALIASES : has
    JOBS ||--o{ JOB_SKILLS : links
    SKILLS ||--o{ JOB_SKILLS : appears_in
    LEARNING_RESOURCES ||--o{ LEARNING_RESOURCE_SKILLS : links
    SKILLS ||--o{ LEARNING_RESOURCE_SKILLS : recommends
    LEARNING_RESOURCES ||--o{ LEARNING_RESOURCE_LANGUAGES : labels
```

## Integrity and Modeling Notes

- `source_files` uses a composite `(source_dataset, source_file)` primary key. `jobs` references that pair, and `job_skills` references both the job provenance tuple and its skill. The migration includes a corresponding unique job key for this composite relationship.
- Migration 002 preserves archive-level source kind, date/listing semantics, original file IDs and checksums, archive member details, emitted row counts, and the upstream archive-run identity. A synthetic local `archive_integrity` source key represents the archive bundle record whose original source dataset is null.
- `(record_id, skill_id)` is the primary key of `job_skills`, preventing duplicate job-skill associations.
- `company`, `country`, `city`, and `region` remain source fields on `jobs`; separate normalized company/location tables are not part of the current dataset model.
- Date and salary columns preserve source text; `posted_at` remains separate from `source_updated_at`. The schema does not invent a collection date or numeric salary.
- Learning-resource languages are stored as labels from the curated source, not standardized codes. Resource access and cost data retain their verification status/date and are not current availability guarantees.
- User accounts, saved jobs, searches, and persistent skill profiles are out of scope.
