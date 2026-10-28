# Data and Database Plan

## Current Status and Guiding Principle

The team reports that data collection is the only completed project activity. The contents and fields of the large files in Drive have not yet been documented in this repository. All database designs below are provisional until T01 is complete. Do not modify the original Drive files, and do not commit large raw CSV/ZIP files or database credentials to GitHub.

## T01 — Dataset Audit Checklist

Record the following before building the schema or models:

- File names, formats, sizes, text encodings, and languages.
- Record and column counts, field definitions, and representative values.
- Missing-value rates and duplicates; determine whether repeated records are duplicate postings or reposted advertisements.
- Coverage by country, employer, role, date range, and advertisement source.
- Availability of job descriptions, skills, work arrangement, experience, and education.
- Salary coverage, currencies, pay periods, and whether values are single amounts or ranges.
- Source-link validity, the distinction between posting date and collection date, and any restrictions on data use or redistribution.

**Deliverable:** A Data Audit and Data Dictionary. Do not publish samples that expose personal information or data that the team is not permitted to redistribute.

## Data Stages

1. **Raw source:** Preserve the original files in their current location; do not edit them directly.
2. **Inspection and staging:** Record file structure, data-quality issues, and cleaning decisions. If a working copy is required, store it securely outside Git.
3. **Standardization:** Normalize titles, values, aliases, and duplicates while retaining original values where useful.
4. **Analytical database:** Load structured data into PostgreSQL/Neon for analysis and application access.
5. **Outputs:** Produce reproducible queries, charts, models, and reports with documented transformations.

## Provisional Relational Model

Confirm or revise this model after auditing the actual fields:

- **Job Posts:** Original and normalized title, description, posting and collection dates, work arrangement, experience, original salary text and normalized salary fields where available, and source URL.
- **Companies:** Normalized and original employer names; employer may be unknown.
- **Locations:** Country and city/region where available; unknown locations remain unknown.
- **Skills:** Canonical skill name, optional category, and known aliases.
- **Job Skills:** Junction table linking job posts to skills. Add required/preferred status only when it can be inferred reliably from the source.
- **Sources:** Source platform or site, advertisement/source URL, and collection date.
- **Learning Resources:** Skill, resource title, provider, language, level, URL, free-access status, and verification date.

## Proposed Relationships

- One company may be associated with many job posts; an advertisement may have no known company.
- One location may be associated with many job posts; a post may have no known location.
- Job posts and skills form a many-to-many relationship through Job Skills.
- One source may provide many job posts.
- One skill may be linked to multiple learning resources.

## Field Design Rules

- Preserve original title, salary, and description text; do not replace originals with normalized values only.
- Salary fields require amount or range, currency, pay period (monthly, yearly, hourly, etc.), and original text. Do not aggregate incomparable currencies or pay periods.
- Normalize work arrangements to values such as remote, hybrid, onsite, or unknown only after reviewing the source text.
- Never convert missing values to zero or create an unreported salary, employer, or location.
- Keep posting date separate from collection date.
- Avoid duplicate skill assignments within the same advertisement after alias normalization; retain source or confidence information where feasible.

## ERD and Keys

After T01 and T02, create an ERD showing tables, primary and foreign keys, optional relationships, and nullable fields. Review it with another team member. Clearly represent the Job Posts-to-Skills relationship through Job Skills, as well as source, company, and location relationships.

## Neon and Secure Connections

- Store connection details in local environment variables or hosting configuration; never commit them or embed them in notebooks.
- If environment-variable names need to be documented, use an example configuration with no real credentials.
- Python analysis should query selected results from the database rather than repeatedly loading a large raw file.
- Validate record counts, relationships, and constraints after each load. Keep transformation steps reproducible.
