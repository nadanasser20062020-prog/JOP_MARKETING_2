import path from 'node:path';
import { fileURLToPath } from 'node:url';

const thisFile = fileURLToPath(import.meta.url);
export const backendRoot = path.resolve(path.dirname(thisFile), '..');
export const repoRoot = path.resolve(backendRoot, '..');

function positiveInteger(value, fallback, maximum) {
  const parsed = Number.parseInt(value ?? '', 10);
  return Number.isInteger(parsed) && parsed > 0 ? Math.min(parsed, maximum) : fallback;
}

const defaultDatabasePath = process.env.VERCEL
  ? path.join(backendRoot, 'data', 'jobs_analytics.sqlite3.gz')
  : path.join(repoRoot, 'data', 'processed', 'jobs_cleaned_audited.sqlite3');

export const config = Object.freeze({
  port: positiveInteger(process.env.PORT, 4000, 65535),
  host: process.env.HOST || '0.0.0.0',
  environment: process.env.NODE_ENV || 'development',
  databasePath: path.resolve(process.env.DATASET_DB_PATH || defaultDatabasePath),
  deploymentDatabasePath: path.resolve(
    process.env.DEPLOYMENT_DB_PATH || path.join(backendRoot, 'data', 'jobs_analytics.sqlite3'),
  ),
  maxBodyBytes: positiveInteger(process.env.MAX_BODY_BYTES, 64 * 1024, 1024 * 1024),
  cacheTtlMs: positiveInteger(process.env.CACHE_TTL_MS, 30_000, 300_000),
  maxApiLimit: positiveInteger(process.env.MAX_API_LIMIT, 100, 500),
  isProduction: process.env.NODE_ENV === 'production' || Boolean(process.env.VERCEL),
});
