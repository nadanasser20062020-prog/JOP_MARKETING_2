# Proposed PostgreSQL Physical Schema

**Status:** Provisional design artifact for the SRS. This is not executable DDL. Confirm every field, constraint, and data type against the actual collected files before creating migrations.

## 1. Design Objectives

- Normalize reusable companies, locations, sources, skills, and resources.
- Preserve original advertisement values alongside normalized values.
- Represent the many-to-many relationship between job posts and skills.
- Make salary units, source provenance, and posting/collection dates explicit.
- Support the expected search, market aggregation, matching, and resource queries without storing user profiles in the initial scope.

## 2. Candidate Tables

### `sources`

| Column | Candidate PostgreSQL type | Constraint / purpose |
|---|---|---|
| `source_id` | `BIGINT GENERATED ... AS IDENTITY` | Primary key |
| `source_name` | `TEXT` | Required source/platform label |
| `source_domain` | `TEXT` | Nullable normalized domain |
| `created_at` | `TIMESTAMPTZ` | Ingestion metadata, if required |

### `companies`

| Column | Candidate PostgreSQL type | Constraint / purpose |
|---|---|---|
| `company_id` | `BIGINT GENERATED ... AS IDENTITY` | Primary key |
| `name_original` | `TEXT` | Original employer name when available |
| `name_normalized` | `TEXT` | Normalized value used for grouping; nullable until resolved |

Do not impose uniqueness on normalized employer names until the audit identifies collisions and alias rules.

### `locations`

| Column | Candidate PostgreSQL type | Constraint / purpose |
|---|---|---|
| `location_id` | `BIGINT GENERATED ... AS IDENTITY` | Primary key |
| `country_name` | `TEXT` | Original or normalized country label, with a documented convention |
| `country_code` | `CHAR(2)` | Nullable standardized code if validation is possible |
| `city` | `TEXT` | Nullable city |
| `region` | `TEXT` | Nullable region/state |

### `job_posts`

| Column | Candidate PostgreSQL type | Constraint / purpose |
|---|---|---|
| `job_post_id` | `BIGINT GENERATED ... AS IDENTITY` | Primary key |
| `source_id` | `BIGINT` | Foreign key to `sources`; nullability depends on source coverage |
| `source_job_id` | `TEXT` | Nullable external identifier, if present |
| `company_id` | `BIGINT` | Nullable foreign key to `companies` |
| `location_id` | `BIGINT` | Nullable foreign key to `locations` |
| `title_original` | `TEXT` | Preserve source title |
| `title_normalized` | `TEXT` | Nullable canonical title used for grouping |
| `description_original` | `TEXT` | Original description if available and permitted to retain |
| `posted_at` | `DATE` | Nullable source posting date; do not substitute collection date |
| `collected_at` | `TIMESTAMPTZ` | Collection timestamp assigned or verified by the ingestion process |
| `work_mode` | `TEXT` | Nullable controlled value such as remote, hybrid, onsite, or unknown |
| `employment_type` | `TEXT` | Nullable normalized employment type, if supported |
| `experience_level` | `TEXT` | Nullable normalized experience level, if supported |
| `salary_min` | `NUMERIC(14,2)` | Nullable lower bound for disclosed salary |
| `salary_max` | `NUMERIC(14,2)` | Nullable upper bound for disclosed salary |
| `salary_currency` | `CHAR(3)` | Nullable currency code; required when normalized salary values are stored |
| `salary_period` | `TEXT` | Nullable period such as hourly, monthly, or annual |
| `salary_original_text` | `TEXT` | Original salary text for traceability |
| `source_url` | `TEXT` | Nullable original advertisement URL |
| `source_record_hash` | `TEXT` | Optional deduplication/audit fingerprint; define after profiling |

### `skills`

| Column | Candidate PostgreSQL type | Constraint / purpose |
|---|---|---|
| `skill_id` | `BIGINT GENERATED ... AS IDENTITY` | Primary key |
| `canonical_name` | `TEXT` | Required standardized skill name; uniqueness policy must be reviewed |
| `category` | `TEXT` | Nullable category such as language, framework, or tool |

### `skill_aliases`

| Column | Candidate PostgreSQL type | Constraint / purpose |
|---|---|---|
| `alias_id` | `BIGINT GENERATED ... AS IDENTITY` | Primary key |
| `skill_id` | `BIGINT` | Required foreign key to `skills` |
| `alias_text` | `TEXT` | Original alias or spelling variant |
| `normalized_alias` | `TEXT` | Normalized lookup value |
| `language_code` | `TEXT` | Nullable language identifier where useful |

Alias uniqueness must be checked for collisions before adding a global unique constraint; one alias may be ambiguous in different contexts.

### `job_skills`

| Column | Candidate PostgreSQL type | Constraint / purpose |
|---|---|---|
| `job_post_id` | `BIGINT` | Foreign key and part of composite primary key |
| `skill_id` | `BIGINT` | Foreign key and part of composite primary key |
| `mention_type` | `TEXT` | Controlled value only if the source distinguishes required, preferred, or unspecified |
| `evidence_text` | `TEXT` | Optional source phrase or short evidence reference, subject to data-use policy |
| `extraction_method` | `TEXT` | Optional indicator for manual, rule-based, or model-assisted extraction |
| `confidence` | `NUMERIC(4,3)` | Optional value only if an extraction method provides a calibrated confidence measure |

Candidate primary key: `(job_post_id, skill_id)`. Add a separate association identifier only if repeated mentions must be stored independently.

### `learning_resources`

| Column | Candidate PostgreSQL type | Constraint / purpose |
|---|---|---|
| `resource_id` | `BIGINT GENERATED ... AS IDENTITY` | Primary key |
| `skill_id` | `BIGINT` | Required foreign key to `skills` under the one-resource-to-one-primary-skill model |
| `title` | `TEXT` | Required display title |
| `provider` | `TEXT` | Provider or publisher |
| `url` | `TEXT` | Required validated external URL |
| `language_code` | `TEXT` | Language of the resource |
| `level` | `TEXT` | Optional learning level |
| `access_status` | `TEXT` | Reviewed status such as free, partially free, or paid |
| `verified_at` | `DATE` | Date access status was last reviewed |
| `is_active` | `BOOLEAN` | Whether the resource is currently listed |

If one resource must map to several skills, replace the direct `skill_id` relationship with a `resource_skills` junction table.

## 3. Relationships and Keys

- `job_posts.source_id` references `sources.source_id` when a source is known.
- `job_posts.company_id` references `companies.company_id` and may be null.
- `job_posts.location_id` references `locations.location_id` and may be null.
- `job_skills.job_post_id` references `job_posts.job_post_id`.
- `job_skills.skill_id` references `skills.skill_id`.
- `skill_aliases.skill_id` references `skills.skill_id`.
- `learning_resources.skill_id` references `skills.skill_id` under the initial one-primary-skill model.
- Use primary keys independent of titles and source text; titles are not reliable identifiers.

## 4. Normalization Considerations

- **First normal form:** Store individual skill relationships as rows in `job_skills`, not as a comma-separated field in `job_posts`.
- **Second and third normal forms:** Keep companies, locations, sources, skills, aliases, and resources in separate entities so attributes depend on their keys rather than repeated advertisement data.
- Retain source values alongside normalized values where the transformation is useful for search or comparison.
- Do not create a table solely to claim normalization if it does not represent a stable entity or query need.
- Record unknown and missing values consistently; never create a placeholder entity for an unreported company or location unless a documented design requires it.

## 5. Candidate Constraints and Validation Rules

All constraints are provisional until source profiling is complete.

- If both salary bounds exist, `salary_min` must be non-negative and `salary_max` must be greater than or equal to `salary_min`.
- Normalized salary amounts require a known currency and pay period.
- Work-mode values should use an approved controlled vocabulary; preserve unknown values explicitly.
- `collected_at` should be non-null for loaded records if the ingestion process can provide it.
- Prevent duplicate `(job_post_id, skill_id)` associations.
- Use foreign keys to prevent orphaned relationships.
- Validate URL syntax but do not assume a valid URL remains available.
- Any uniqueness rule for source URLs, source identifiers, company names, or aliases must be verified against the dataset before enforcement.

## 6. Candidate Indexes

Create indexes only after confirming expected query patterns and measuring performance. Candidates include:

- `job_posts(title_normalized)` for title filtering.
- `job_posts(location_id)` and location country fields for market filters.
- `job_posts(posted_at)` for supported time analysis.
- `job_posts(source_id)` and a source identifier or URL for provenance and deduplication.
- `job_skills(skill_id)` and `job_skills(job_post_id)` for skill search and detail pages.
- `skill_aliases(normalized_alias)` for matching input normalization.
- A database-appropriate full-text index for job description search, if needed.

## 7. Migration and Data-Load Policy

- Create ordered, reviewable migrations after the physical schema is approved.
- Test migrations against a non-production database before deployment.
- Load processed data in a repeat-safe manner; define how reruns handle duplicates before production use.
- Validate schema, row counts, foreign keys, salary units, and rejected records after each load.
- Keep database credentials outside Git and notebooks.
- The Python loader is planned for `scripts/database_loading/`; its implementation must wait for T01–T05.
