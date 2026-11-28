import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { config, backendRoot } from './config.js';
import { openReadOnlyDatabase } from './database.js';
import { AnalyticsService } from './analytics-service.js';
import { SkillMatchingService } from './skill-matching.js';
import { auditJobFamilyLabels } from './job-family-ml.js';
import { readRoleFamilyModelArtifact } from './job-family-classifier.js';
import { HttpError, badRequest, notFound } from './errors.js';
import { parseBoundedInteger } from './normalize.js';

const DASHBOARD_PATH = fileURLToPath(new URL('./dashboard.html', import.meta.url));
const API_REFERENCE_PATH = path.join(backendRoot, 'API_REFERENCE.md');
const FAMILY_STATUS_PATH = path.join(backendRoot, 'reports', 'job-family-readiness.json');
const DEFAULT_FAMILY_MODEL_PATH = path.join(backendRoot, 'models', 'job-family-model.json.gz');
const DASHBOARD_SNAPSHOT_PATH = path.join(backendRoot, 'reports', 'dashboard-data.json');
const API_PREFIX = '/api/v2';
const MAX_JOB_FAMILY_TEXT_CHARACTERS = 16_000;

function json(res, status, payload, requestId) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', status >= 400 ? 'no-store' : 'private, max-age=0, must-revalidate');
  res.end(JSON.stringify({ ...payload, meta: { ...(payload.meta || {}), requestId } }));
}

async function readJsonBody(req, maxBytes) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > maxBytes) throw new HttpError(413, 'BODY_TOO_LARGE', `Request body must not exceed ${maxBytes} bytes.`);
    chunks.push(chunk);
  }
  if (!size) throw badRequest('A JSON request body is required.');
  try {
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } catch {
    throw badRequest('Request body must be valid JSON.');
  }
}

function success(data, requestId, status = 200) {
  return { status, payload: { success: true, data }, requestId };
}

function normalizedPath(pathname) {
  if (pathname.length > 1 && pathname.endsWith('/')) return pathname.slice(0, -1);
  return pathname;
}

function getFamilyStatus(database = null) {
  if (fs.existsSync(FAMILY_STATUS_PATH)) {
    try {
      return JSON.parse(fs.readFileSync(FAMILY_STATUS_PATH, 'utf8'));
    } catch {
      // Fall back to the source database rather than returning a corrupted report.
    }
  }
  return database ? auditJobFamilyLabels(database) : null;
}

function familyModelStatusPayload(labelQualityAudit, modelBundle) {
  const artifact = modelBundle?.artifact;
  return {
    decision: artifact ? 'MODEL_READY' : 'MODEL_NOT_BUILT',
    predictionEnabled: Boolean(artifact),
    targetField: 'role_family',
    model: artifact ? {
      modelVersion: artifact.modelVersion,
      trainedAtUtc: artifact.trainedAtUtc,
      algorithm: artifact.algorithm,
      featureFields: artifact.featureFields,
      training: {
        labeledRecords: artifact.training?.labeledRecords ?? null,
        classCounts: artifact.training?.classCounts ?? {},
        featureCoverage: artifact.training?.featureCoverage ?? null,
        splitCounts: artifact.training?.splitCounts ?? {},
      },
      evaluation: artifact.evaluation ?? null,
    } : null,
    labelQualityAudit: {
      decision: labelQualityAudit.decision,
      roleFamilyLabelCoverage: labelQualityAudit.roleFamilyLabelCoverage,
      roleFamilyClassCount: labelQualityAudit.roleFamilyClassCount,
      reasons: labelQualityAudit.reasons,
    },
    note: 'The label-quality audit is descriptive; it does not gate training or prediction from the stored role_family labels.',
  };
}

function jobFamilyInputText(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    throw badRequest('The request body must be a JSON object.');
  }
  for (const field of ['text', 'title', 'description']) {
    if (body[field] !== undefined && typeof body[field] !== 'string') {
      throw badRequest(`${field} must be a string.`);
    }
  }
  const text = body.text?.trim() || `${body.title || ''} ${body.description || ''}`.trim();
  if (!text) throw badRequest('Provide non-empty text or a title/description to classify.');
  if (text.length > MAX_JOB_FAMILY_TEXT_CHARACTERS) {
    throw badRequest(`Classification text must not exceed ${MAX_JOB_FAMILY_TEXT_CHARACTERS} characters.`);
  }
  return text;
}

function getDashboardSnapshot(database) {
  if (!fs.existsSync(DASHBOARD_SNAPSHOT_PATH)) return null;
  try {
    const snapshot = JSON.parse(fs.readFileSync(DASHBOARD_SNAPSHOT_PATH, 'utf8'));
    if (snapshot.schemaVersion !== 1 || !snapshot.data) return null;
    const datasetGeneratedAt = database.get(
      "SELECT value FROM dataset_metadata WHERE key = 'generated_at_utc'",
    )?.value;
    return datasetGeneratedAt && datasetGeneratedAt === snapshot.datasetGeneratedAtUtc
      ? snapshot.data
      : null;
  } catch {
    return null;
  }
}

export function createHttpHandler({
  databasePath = config.databasePath,
  cacheTtlMs = config.cacheTtlMs,
  maxApiLimit = config.maxApiLimit,
  maxBodyBytes = config.maxBodyBytes,
  isProduction = config.isProduction,
  dashboardHtml = null,
  jobFamilyModelPath = DEFAULT_FAMILY_MODEL_PATH,
} = {}) {
  let database;
  let analytics;
  let matching;
  let familyStatus;
  let familyModelBundle;
  let databaseOpenError;

  function loadFamilyModel() {
    if (familyModelBundle) return familyModelBundle;
    if (!fs.existsSync(jobFamilyModelPath)) return null;
    try {
      const loaded = readRoleFamilyModelArtifact(jobFamilyModelPath);
      if (loaded.artifact.targetField !== 'role_family') {
        throw new Error(`Expected role_family target, received ${loaded.artifact.targetField || 'unknown'}.`);
      }
      familyModelBundle = loaded;
      return familyModelBundle;
    } catch (cause) {
      throw new HttpError(
        503,
        'MODEL_ARTIFACT_INVALID',
        'The role-family model artifact is unavailable or invalid.',
        isProduction ? undefined : cause.message,
      );
    }
  }

  function loadFamilyLabelAudit() {
    if (familyStatus) return familyStatus;
    familyStatus = getFamilyStatus();
    if (!familyStatus) {
      const { database: db } = dependencies();
      familyStatus = getFamilyStatus(db);
    }
    return familyStatus;
  }

  function dependencies() {
    if (databaseOpenError) throw databaseOpenError;
    if (!database) {
      try {
        database = openReadOnlyDatabase(databasePath);
        analytics = new AnalyticsService(database, { cacheTtlMs, maxApiLimit });
        matching = new SkillMatchingService(database);
      } catch (error) {
        databaseOpenError = error;
        throw error;
      }
    }
    return { database, analytics, matching };
  }

  async function handle(req, res) {
    const requestId = String(req.headers['x-request-id'] || randomUUID()).slice(0, 80);
    res.setHeader('X-Request-Id', requestId);
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'no-referrer');
    res.setHeader('X-Frame-Options', 'DENY');

    const url = new URL(req.url || '/', 'http://localhost');
    const pathname = normalizedPath(url.pathname);
    if (req.method === 'OPTIONS') {
      res.statusCode = 204;
      res.setHeader('Allow', 'GET, POST, OPTIONS');
      res.end();
      return;
    }

    if ((pathname === '/health' || pathname === `${API_PREFIX}/health`) && req.method === 'GET') {
      try {
        const { database: db } = dependencies();
        const check = db.get('SELECT 1 AS ready');
        json(res, 200, { success: true, data: { status: check?.ready === 1 ? 'ok' : 'degraded', database: 'read-only-connected', apiVersion: 'v2' } }, requestId);
      } catch (error) {
        const status = error.code?.startsWith('DATABASE_') ? 503 : 500;
        json(res, status, { success: false, error: { code: error.code || 'HEALTH_CHECK_FAILED', message: isProduction ? 'The NADA SQLite database is unavailable or failed schema preflight.' : error.message } }, requestId);
      }
      return;
    }

    if ((pathname === '/' || pathname === '/dashboard' || pathname === `${API_PREFIX}/dashboard`) && req.method === 'GET') {
      try {
        const html = dashboardHtml ?? fs.readFileSync(DASHBOARD_PATH, 'utf8');
        res.statusCode = 200;
        res.setHeader('Content-Type', 'text/html; charset=utf-8');
        res.setHeader('Cache-Control', 'no-store');
        res.setHeader('Content-Security-Policy', "default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none'");
        res.end(html);
      } catch (error) {
        json(res, 500, { success: false, error: { code: 'DASHBOARD_UNAVAILABLE', message: isProduction ? 'The dashboard asset is unavailable.' : error.message } }, requestId);
      }
      return;
    }

    if (!pathname.startsWith(API_PREFIX)) {
      const result = success({ message: 'Use /api/v2 or /dashboard.' }, requestId);
      json(res, result.status, result.payload, requestId);
      return;
    }

    try {
      const apiPath = normalizedPath(pathname.slice(API_PREFIX.length) || '/');
      if (apiPath === '/' && req.method === 'GET') {
        const result = success({ name: 'JOP Marketing Intelligence API', version: 'v2', documentation: `${API_PREFIX}/docs`, health: `${API_PREFIX}/health` }, requestId);
        json(res, result.status, result.payload, requestId);
        return;
      }
      if (apiPath === '/docs' && req.method === 'GET') {
        const markdown = fs.readFileSync(API_REFERENCE_PATH, 'utf8');
        res.statusCode = 200;
        res.setHeader('Content-Type', 'text/markdown; charset=utf-8');
        res.setHeader('Cache-Control', 'public, max-age=3600');
        res.end(markdown);
        return;
      }

      if (apiPath === '/ml/job-family/status' && req.method === 'GET') {
        const labelQualityAudit = loadFamilyLabelAudit();
        const modelBundle = loadFamilyModel();
        json(res, 200, success(familyModelStatusPayload(labelQualityAudit, modelBundle), requestId).payload, requestId);
        return;
      }
      if (apiPath === '/ml/job-family/predict' && req.method === 'POST') {
        const modelBundle = loadFamilyModel();
        if (!modelBundle) {
          throw new HttpError(503, 'MODEL_NOT_BUILT', 'The role-family model artifact is missing. Run npm run ml:train-family before enabling prediction.');
        }
        const body = await readJsonBody(req, maxBodyBytes);
        const text = jobFamilyInputText(body);
        const roleFamily = modelBundle.model.predict(text);
        if (!roleFamily) throw new HttpError(503, 'MODEL_PREDICTION_FAILED', 'The role-family model did not return a class.');
        json(res, 200, success({
          roleFamily,
          targetField: 'role_family',
          modelVersion: modelBundle.artifact.modelVersion,
          algorithm: modelBundle.artifact.algorithm,
          trainedAtUtc: modelBundle.artifact.trainedAtUtc,
        }, requestId).payload, requestId);
        return;
      }

      const { database: db, analytics: analysis, matching: skillMatcher } = dependencies();
      if (apiPath === '/analytics/overview' && req.method === 'GET') {
        json(res, 200, success(analysis.overview(), requestId).payload, requestId);
        return;
      }
      if (apiPath === '/analytics/dashboard' && req.method === 'GET') {
        const snapshot = getDashboardSnapshot(db);
        json(res, 200, success(snapshot ?? analysis.dashboardData(), requestId).payload, requestId);
        return;
      }
      if (apiPath === '/analytics/roles' && req.method === 'GET') {
        const limit = parseBoundedInteger(url.searchParams.get('limit'), { name: 'limit', fallback: 25, min: 1, max: maxApiLimit });
        const data = analysis.searchRoles(url.searchParams.get('q') || '', limit);
        json(res, 200, success({ query: url.searchParams.get('q') || '', roles: data }, requestId).payload, requestId);
        return;
      }
      if (apiPath === '/analytics/role' && req.method === 'GET') {
        const title = url.searchParams.get('title') || '';
        if (!title.trim()) throw badRequest('The title query parameter is required.');
        json(res, 200, success(analysis.roleReport(title), requestId).payload, requestId);
        return;
      }
      const roleViews = new Map([
        ['/analytics/role/countries', 'countryDemand'],
        ['/analytics/role/skills', 'skills'],
        ['/analytics/role/technology-combinations', 'technologyCombinations'],
        ['/analytics/role/salaries', 'annualSalaryByCountry'],
        ['/analytics/role/work-mode', 'workMode'],
      ]);
      if (roleViews.has(apiPath) && req.method === 'GET') {
        const title = url.searchParams.get('title') || '';
        if (!title.trim()) throw badRequest('The title query parameter is required.');
        const report = analysis.roleReport(title);
        json(res, 200, success({ role: report.role, data: report[roleViews.get(apiPath)] }, requestId).payload, requestId);
        return;
      }
      if (apiPath === '/analytics/skills' && req.method === 'GET') {
        const limit = parseBoundedInteger(url.searchParams.get('limit'), { name: 'limit', fallback: 25, min: 1, max: maxApiLimit });
        json(res, 200, success(analysis.globalSkills(limit), requestId).payload, requestId);
        return;
      }
      if (apiPath === '/analytics/work-mode' && req.method === 'GET') {
        json(res, 200, success(analysis.workMode(url.searchParams.get('title') || ''), requestId).payload, requestId);
        return;
      }
      if (apiPath === '/analytics/markets/arab-vs-international' && req.method === 'GET') {
        const limit = parseBoundedInteger(url.searchParams.get('limit'), { name: 'limit', fallback: 15, min: 1, max: maxApiLimit });
        json(res, 200, success(analysis.arabVsInternational(limit), requestId).payload, requestId);
        return;
      }
      if (apiPath === '/ml/skill-to-job-match' && req.method === 'POST') {
        const body = await readJsonBody(req, maxBodyBytes);
        json(res, 200, success(skillMatcher.match(body), requestId).payload, requestId);
        return;
      }
      throw notFound(`No ${req.method} route exists at ${pathname}.`);
    } catch (error) {
      const status = error instanceof HttpError ? error.status : error.code?.startsWith('DATABASE_') ? 503 : 500;
      const code = error.code || 'INTERNAL_ERROR';
      const message = status >= 500 && isProduction ? 'The request could not be completed.' : error.message;
      const details = status < 500 || !isProduction ? error.details : undefined;
      json(res, status, { success: false, error: { code, message, ...(details === undefined ? {} : { details }) } }, requestId);
    }
  }

  handle.close = () => {
    database?.close();
    database = null;
    analytics = null;
    matching = null;
    familyStatus = null;
    familyModelBundle = null;
    databaseOpenError = null;
  };
  return handle;
}
