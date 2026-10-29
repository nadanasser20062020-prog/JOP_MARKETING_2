# Logical Entity-Relationship Diagram

**Status:** Provisional logical ERD. Entity and field candidates must be checked against the actual source files before schema implementation. Optional attributes and relationships may not be available in the collected data.

```mermaid
erDiagram
    COMPANY {
        string company_id PK
        string name_original
        string name_normalized
    }
    LOCATION {
        string location_id PK
        string country
        string city
        string region
    }
    SOURCE {
        string source_id PK
        string source_name
        string source_domain
    }
    JOB_POST {
        string job_post_id PK
        string company_id FK
        string location_id FK
        string source_id FK
        string source_job_id
        string title_original
        string title_normalized
        string description
        date posted_at
        datetime collected_at
        string work_mode
        decimal salary_min
        decimal salary_max
        string salary_currency
        string salary_period
        string salary_original_text
        string source_url
    }
    SKILL {
        string skill_id PK
        string canonical_name
        string category
    }
    JOB_SKILL {
        string job_post_id PK, FK
        string skill_id PK, FK
        string mention_type
        string evidence
    }
    LEARNING_RESOURCE {
        string resource_id PK
        string skill_id FK
        string title
        string provider
        string language
        string access_status
        date verified_at
        string url
    }

    COMPANY o|--o{ JOB_POST : publishes
    LOCATION o|--o{ JOB_POST : locates
    SOURCE o|--o{ JOB_POST : provides
    JOB_POST ||--o{ JOB_SKILL : has
    SKILL ||--o{ JOB_SKILL : describes
    SKILL ||--o{ LEARNING_RESOURCE : supports
```

## Design Notes

- `JOB_SKILL` is the junction entity for the many-to-many relationship between advertisements and skills.
- Company and location references are optional when the source does not provide reliable values.
- The `mention_type` field should distinguish required, preferred, or unspecified only when the source supports that interpretation.
- Salary fields are optional and must not combine incompatible currencies or pay periods.
- `posted_at` and `collected_at` represent different events.
- The ERD does not include user, saved-job, saved-search, or notification entities in the current scope.
