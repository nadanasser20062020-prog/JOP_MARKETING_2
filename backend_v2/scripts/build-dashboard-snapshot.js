import fs from 'node:fs';
import path from 'node:path';
import { config, backendRoot } from '../src/config.js';
import { openReadOnlyDatabase } from '../src/database.js';
import { AnalyticsService } from '../src/analytics-service.js';

const databasePath = path.resolve(process.env.DEPLOYMENT_DB_PATH || config.deploymentDatabasePath);
const outputPath = path.join(backendRoot, 'reports', 'dashboard-data.json');
const database = openReadOnlyDatabase(databasePath);
try {
  const datasetGeneratedAt = database.get(
    "SELECT value FROM dataset_metadata WHERE key = 'generated_at_utc'",
  )?.value;
  if (!datasetGeneratedAt) {
    throw new Error('Deployment database is missing dataset_metadata.generated_at_utc. Build it with npm run analytics:build-deploy-db first.');
  }

  const analytics = new AnalyticsService(database, { cacheTtlMs: 5 * 60_000, maxApiLimit: config.maxApiLimit });
  const data = analytics.dashboardData();
  const snapshot = {
    schemaVersion: 1,
    datasetGeneratedAtUtc: datasetGeneratedAt,
    snapshotGeneratedAtUtc: new Date().toISOString(),
    data,
  };
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, `${JSON.stringify(snapshot)}\n`);
  console.log(JSON.stringify({
    outputPath,
    datasetGeneratedAtUtc: datasetGeneratedAt,
    totalJobs: data.overview.totalJobs,
    roleCount: data.topRoles.length,
    countryCount: data.topCountries.length,
    skillCount: data.topSkills.length,
    bytes: fs.statSync(outputPath).size,
  }, null, 2));
} finally {
  database.close();
}
