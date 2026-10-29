# Deployment and Operations Plan

**Status:** Platform-neutral plan. Select hosting and operational targets after confirming the technology stack and project demonstration requirements.

## Environment Model

Use distinct configuration for:

- **Local development:** Individual developer environment with non-production credentials and approved test data.
- **Test or staging:** Shared environment for integration, acceptance, and reviewer walkthroughs before release.
- **Demonstration/production:** Stable environment for the final project presentation, with restricted credentials and reviewed data.

If separate environments are not available, document the reduced isolation and ensure test operations cannot overwrite the demonstration database.

## Deployment Components

- Frontend application.
- Backend/API service.
- PostgreSQL/Neon or another database selected by the team.
- Data-loading and migration process.
- Versioned model or matching logic where required.
- External job and learning-resource links, which are not controlled by the application.

## Release Process

1. Review and merge a scoped change through the repository workflow.
2. Run automated checks for documentation, tests, builds, data contracts, and secret exposure as applicable.
3. Apply database migrations to a non-production environment and verify results.
4. Deploy the application to staging and complete smoke and critical-flow tests.
5. Promote the reviewed version to the demonstration environment.
6. Record the release identifier, migration version, known issues, and rollback option.

The exact CI/CD provider and branch protections remain open decisions.

## Configuration and Secrets

- Keep environment-specific configuration outside source control.
- Use the hosting provider's secret-management mechanism for deployed credentials.
- Use separate credentials or databases for non-production and demonstration environments where feasible.
- Rotate credentials immediately if exposure is suspected.
- Never include secrets, raw dataset files, or sensitive records in deployment logs or artifacts.

## Database Migration and Recovery

- Keep schema changes ordered, reviewed, and repeatable.
- Back up or snapshot the database before risky changes where supported.
- Test restore procedures before relying on backups.
- Document which team member is authorized to perform a restore or destructive migration.
- Keep a safe demonstration dataset or repeatable load procedure so the presentation can be recovered without modifying the source files.

Backup frequency, retention, recovery objectives, and provider capabilities must be confirmed before release.

## Monitoring and Logging

Monitor only information needed to diagnose the demonstration environment, such as service health, request latency, error rates, database connectivity, and deployment version. Logs must not contain credentials, full matching request bodies, or unnecessary personal information. Set an appropriate retention period after selecting the hosting provider.

## Operational Runbooks

### Database Unavailable
1. Confirm whether the issue is connectivity, credentials, provider status, or a migration.
2. Verify service health without exposing secrets.
3. Restore the last known working configuration or escalate to the database owner.
4. Keep the user-facing message generic and recoverable.

### Failed Deployment
1. Stop further promotion.
2. Record the failed release and error category.
3. Roll back to the last known-good application version when supported.
4. Verify health, key queries, and the primary user flows.

### Incorrect or Stale Data
1. Identify the affected source file, load, transformation, and metric.
2. Prevent or qualify affected displays if necessary.
3. Correct the transformation or data load without editing the original source in place.
4. Reconcile the corrected counts and update methodology notes.

### Exposed Credential
1. Revoke or rotate the credential immediately.
2. Update the deployment configuration and verify access.
3. Assess exposure scope and document follow-up actions.
4. Review repository history and logs; removing a secret from the latest file is not sufficient.

## Release Readiness

Before the final demonstration, verify the deployed version, database connectivity, sample counts, critical routes, bilingual behavior, external links, error states, and rollback steps. Document unresolved platform or availability limitations.
