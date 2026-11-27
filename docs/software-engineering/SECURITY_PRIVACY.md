# Security and Privacy Requirements

**Status:** Current API controls: local SQLite is opened read-only; matching input is transient, not persisted, and not logged; request size and page sizes are bounded. Reassess if authentication, persistent profiles, user-submitted documents, or broader deployment are added.

## Security Objectives

- Protect access to the local SQLite file and operational configuration.
- Prevent unsafe query construction and injection.
- Limit exposure of collected records and external links.
- Keep user-submitted skill input temporary and out of persistent storage in the initial release.
- Fail safely without disclosing infrastructure details.

## Assets and Trust Boundaries

| Asset or boundary | Protection requirement |
|---|---|
| Local SQLite database file and path | Keep the file local to the backend host, restrict operating-system permissions, and keep the generated database out of Git |
| Collected job-advertisement data | Follow source terms and agreed access restrictions; do not commit large raw files |
| Skill-matching request | Validate and process for the current request; do not retain or log the submitted list |
| API and database | Validate inputs, use parameterized queries, and return safe errors |
| External links | Validate URL schemes and display that destinations are external |
| Repository and deployment configuration | Keep credentials and private configuration out of version control |

## Threats and Controls

| Threat | Minimum control |
|---|---|
| Local database or private configuration exposed in source control or browser bundle | Keep SQLite under the ignored local data directory, restrict file permissions, scan changes and build artifacts, and remove unintended copies |
| SQL injection | Parameterized database operations, allowlisted sorting and filters, input validation |
| Cross-site scripting | Context-appropriate output encoding; treat job descriptions and source text as untrusted content |
| Abuse of public endpoints | Bound request sizes and page sizes; apply rate limits where the deployment platform supports them |
| Sensitive skills captured in logs | Do not log request bodies for matching; minimize identifiers and retention in application logs |
| Database errors exposed to visitors | Return generic user-safe messages and retain diagnostic details only in restricted logs |
| Malicious or misleading external URL | Validate scheme and format; identify outbound links; use safe browser link behavior |
| Unauthorized database-file access | Keep SQLite access in the trusted backend; restrict local file and backup permissions; do not expose the file through a static file server |
| Dependency or build compromise | Use reviewed dependencies, lock dependency versions, and review automated security findings |

## Privacy Requirements

- Do not require accounts in the initial release.
- Do not persist user-entered skill lists or create a user profile.
- Do not include submitted skills in routine analytics, logs, crash reports, or third-party telemetry.
- If usage analytics are later proposed, document the data collected, purpose, retention, and consent requirements before enabling them.
- Review source-site terms, copyright, redistribution conditions, and any personal information present in job advertisements before public release.
- Define retention and removal procedures for collected advertisements if required by source terms or project policy.

## Secure Development Checklist

- [ ] No secrets, raw private data, or credentials are committed.
- [ ] Database access occurs only from a trusted server-side component.
- [ ] Requests are validated and database access is parameterized.
- [ ] User input and collected advertisement content are treated as untrusted.
- [ ] Matching requests are not stored or logged with their skill content.
- [ ] External URLs are validated and clearly identified.
- [ ] Error responses do not expose SQL, stack traces, or deployment details.
- [ ] Dependency and deployment configuration has been reviewed.
- [ ] Data-use permissions and source limitations have been documented.

## Incident Response

If the local database, a backup, or sensitive data is exposed, restrict file access immediately, remove unintended active copies, assess affected data and services, document the incident, and notify the appropriate project owner. If private configuration or any non-database credential is exposed, revoke or rotate it. Do not assume that deleting a file from the latest working tree removes it from Git history or external logs.
