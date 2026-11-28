import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { gzipSync } from 'node:zlib';
import http from 'node:http';
import { once } from 'node:events';
import { createHttpHandler } from '../../src/http.js';
import { trainRoleFamilyModel } from '../../src/job-family-classifier.js';
import { createFixtureDatabase } from '../helpers.js';

function createTestModelArtifact() {
  const rows = Array.from({ length: 120 }, (_, index) => {
    const dataRole = index % 2 === 0;
    return {
      title: dataRole ? `Data Engineer ${index}` : `Software Engineer ${index}`,
      description: dataRole ? 'Python SQL warehouse ETL pipelines' : 'JavaScript React browser frontend',
      label: dataRole ? 'data_engineering' : 'software_engineering',
    };
  });
  const database = {
    get() { return { count: rows.length }; },
    iterate(_sql, maxDescriptionCharacters) {
      return rows.map((row) => ({ ...row, description: row.description.slice(0, maxDescriptionCharacters) }))[Symbol.iterator]();
    },
  };
  return trainRoleFamilyModel(database, { minDocumentFrequency: 1, maxFeatures: 1_000 }).artifact;
}

async function testServer(t, { withModel = false, useMissingDatabase = false } = {}) {
  const fixture = createFixtureDatabase();
  const modelDirectory = fs.mkdtempSync(path.join(os.tmpdir(), 'jop-http-family-model-'));
  const jobFamilyModelPath = path.join(modelDirectory, 'model.json.gz');
  if (withModel) fs.writeFileSync(jobFamilyModelPath, gzipSync(Buffer.from(JSON.stringify(createTestModelArtifact()))));
  const handler = createHttpHandler({
    databasePath: useMissingDatabase ? path.join(modelDirectory, 'missing.sqlite3') : fixture.databasePath,
    jobFamilyModelPath,
    isProduction: false,
    dashboardHtml: '<!doctype html><title>fixture dashboard</title>',
  });
  const server = http.createServer((request, response) => { void handler(request, response); });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const address = server.address();
  t.after(async () => {
    handler.close();
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
    fixture.cleanup();
    if (modelDirectory) fs.rmSync(modelDirectory, { recursive: true, force: true });
  });
  return `http://127.0.0.1:${address.port}`;
}

test('health and dashboard use the isolated v2 application', async (t) => {
  const base = await testServer(t);
  const healthResponse = await fetch(`${base}/api/v2/health`);
  const health = await healthResponse.json();
  assert.equal(healthResponse.status, 200);
  assert.equal(health.data.database, 'read-only-connected');
  assert.ok(health.meta.requestId);
  const dashboardResponse = await fetch(`${base}/dashboard`);
  assert.equal(dashboardResponse.status, 200);
  assert.match(await dashboardResponse.text(), /fixture dashboard/);
  for (const route of ['/', '/api/v2/dashboard']) {
    const response = await fetch(`${base}${route}`);
    assert.equal(response.status, 200);
    assert.match(await response.text(), /fixture dashboard/);
  }
  const apiRoot = await fetch(`${base}/api/v2`);
  assert.equal((await apiRoot.json()).data.documentation, '/api/v2/docs');
  const docs = await fetch(`${base}/api/v2/docs`);
  assert.equal(docs.status, 200);
  assert.match(docs.headers.get('content-type'), /text\/markdown/);
  const reference = await docs.text();
  assert.match(reference, /# JOP Marketing Intelligence API/);
  assert.doesNotMatch(reference, /[\u0600-\u06ff]/u);
});

test('health and analytics report a clear error when the SQLite database is missing', async (t) => {
  const base = await testServer(t, { useMissingDatabase: true });
  for (const route of ['/api/v2/health', '/api/v2/analytics/dashboard']) {
    const response = await fetch(`${base}${route}`, { signal: AbortSignal.timeout(5_000) });
    const payload = await response.json();
    assert.equal(response.status, 503);
    assert.equal(payload.error.code, 'DATABASE_NOT_FOUND');
    assert.match(payload.error.message, /SQLite database not found/);
  }
});

test('role report route returns dashboard-ready salary and country data', async (t) => {
  const base = await testServer(t);
  const response = await fetch(`${base}/api/v2/analytics/role?title=Data%20Engineer`);
  const payload = await response.json();
  assert.equal(response.status, 200);
  assert.equal(payload.data.advertisementCount, 3);
  assert.equal(payload.data.annualSalaryByCountry.find((row) => row.country === 'Egypt').currencies.find((row) => row.currency === 'USD').mean, 117500);
});

test('skill matching route validates JSON and returns explainable output', async (t) => {
  const base = await testServer(t);
  const response = await fetch(`${base}/api/v2/ml/skill-to-job-match`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ skills: ['python', 'SQL'], limit: 3 }),
  });
  const payload = await response.json();
  assert.equal(response.status, 200);
  assert.equal(payload.data.hiringProbability, false);
  assert.ok(payload.data.advertisements.length > 0);
});

test('invalid API parameters and missing roles use stable 4xx errors', async (t) => {
  const base = await testServer(t);
  const invalidLimit = await fetch(`${base}/api/v2/analytics/roles?limit=not-a-number`);
  assert.equal(invalidLimit.status, 400);
  assert.equal((await invalidLimit.json()).error.code, 'BAD_REQUEST');
  const missingRole = await fetch(`${base}/api/v2/analytics/role?title=not%20in%20dataset`);
  assert.equal(missingRole.status, 404);
  assert.equal((await missingRole.json()).error.code, 'NOT_FOUND');
});

test('role-family model status and prediction work without the analytics database or label-quality approval', async (t) => {
  const base = await testServer(t, { withModel: true, useMissingDatabase: true });
  const statusResponse = await fetch(`${base}/api/v2/ml/job-family/status`);
  const status = await statusResponse.json();
  assert.equal(statusResponse.status, 200);
  assert.equal(status.data.decision, 'MODEL_READY');
  assert.equal(status.data.predictionEnabled, true);
  assert.equal(status.data.targetField, 'role_family');
  assert.equal(status.data.labelQualityAudit.decision, 'NO_GO');

  const predictionResponse = await fetch(`${base}/api/v2/ml/job-family/predict`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ title: 'Data Engineer', description: 'Python SQL warehouse ETL pipelines' }),
  });
  const prediction = await predictionResponse.json();
  assert.equal(predictionResponse.status, 200);
  assert.equal(prediction.data.roleFamily, 'data_engineering');
  assert.equal(prediction.data.targetField, 'role_family');

  const invalidInput = await fetch(`${base}/api/v2/ml/job-family/predict`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({}),
  });
  assert.equal(invalidInput.status, 400);
});

test('missing job-family model is reported as MODEL_NOT_BUILT, never as a label-quality gate', async (t) => {
  const base = await testServer(t);
  const statusResponse = await fetch(`${base}/api/v2/ml/job-family/status`);
  const status = await statusResponse.json();
  assert.equal(status.data.decision, 'MODEL_NOT_BUILT');
  assert.equal(status.data.predictionEnabled, false);
  assert.equal(status.data.labelQualityAudit.decision, 'NO_GO');

  const predictionResponse = await fetch(`${base}/api/v2/ml/job-family/predict`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ text: 'Python data engineering role' }),
  });
  assert.equal(predictionResponse.status, 503);
  assert.equal((await predictionResponse.json()).error.code, 'MODEL_NOT_BUILT');
});
