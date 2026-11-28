import fs from 'node:fs';
import path from 'node:path';
import { openReadOnlyDatabase } from '../src/database.js';
import { readRoleFamilyModelArtifact } from '../src/job-family-classifier.js';
import { backendRoot } from '../src/config.js';
const vercelConfig = JSON.parse(fs.readFileSync(path.join(backendRoot, 'vercel.json'), 'utf8'));
const functionPath = 'api/[...path].js';
const functionConfig = vercelConfig.functions?.[functionPath];
const requiredFiles = [
  'data/jobs_analytics.sqlite3.gz',
  'reports/job-family-readiness.json',
  'reports/job-family-model-evaluation.json',
  'models/job-family-model.json.gz',
  'reports/dashboard-data.json',
  'src/dashboard.html',
  'API_REFERENCE.md',
];
const includeFiles = functionConfig?.includeFiles || [];
const missingFromConfig = requiredFiles.filter((file) => !includeFiles.includes(file));
const missingFromWorkspace = requiredFiles.filter((file) => !fs.existsSync(path.join(backendRoot, file)));
const includedFiles = includeFiles.map((file) => ({
  file,
  bytes: fs.existsSync(path.join(backendRoot, file)) ? fs.statSync(path.join(backendRoot, file)).size : null,
}));
const includedBytes = includedFiles.reduce((sum, file) => sum + (file.bytes ?? 0), 0);
const budgetBytes = 250 * 1024 * 1024;
const targetBytes = 200 * 1024 * 1024;

if (!functionConfig || functionConfig.runtime !== 'nodejs22.x') {
  throw new Error(`Vercel function ${functionPath} must declare runtime nodejs22.x.`);
}
if (missingFromConfig.length || missingFromWorkspace.length) {
  throw new Error(`Vercel assets missing from config=${JSON.stringify(missingFromConfig)} or workspace=${JSON.stringify(missingFromWorkspace)}.`);
}
if (includedBytes >= targetBytes) {
  throw new Error(`Vercel includeFiles total ${includedBytes} bytes exceeds the ${targetBytes}-byte preflight target.`);
}

const modelPath = path.join(backendRoot, 'models', 'job-family-model.json.gz');
const { artifact: modelArtifact, model: hydratedModel } = readRoleFamilyModelArtifact(modelPath);
if (modelArtifact.targetField !== 'role_family' || !hydratedModel.fitted) {
  throw new Error('The packaged job-family model must be a fitted role_family classifier.');
}

const databasePath = path.join(backendRoot, 'data', 'jobs_analytics.sqlite3.gz');
const database = openReadOnlyDatabase(databasePath);
let quickCheck;
let counts;
try {
  const result = database.rawConnectionForPreflight().prepare('PRAGMA quick_check(1)').get();
  quickCheck = result?.quick_check ?? Object.values(result ?? {})[0];
  counts = {
    jobs: Number(database.get('SELECT COUNT(*) AS count FROM jobs')?.count ?? 0),
    auditRows: Number(database.get('SELECT COUNT(*) AS count FROM job_cleaning_audit')?.count ?? 0),
    skillLinks: Number(database.get('SELECT COUNT(*) AS count FROM job_skills')?.count ?? 0),
    skills: Number(database.get('SELECT COUNT(*) AS count FROM skills')?.count ?? 0),
  };
} finally {
  database.close();
}
if (quickCheck !== 'ok') throw new Error(`Vercel database quick_check failed: ${quickCheck}`);
if (counts.jobs !== counts.auditRows || counts.skillLinks === 0 || counts.skills === 0) {
  throw new Error(`Vercel database row-count preflight failed: ${JSON.stringify(counts)}`);
}

const rewrites = new Map((vercelConfig.rewrites || []).map((rewrite) => [rewrite.source, rewrite.destination]));
if (rewrites.get('/') !== '/api/v2/dashboard' || rewrites.get('/dashboard') !== '/api/v2/dashboard') {
  throw new Error('Vercel root/dashboard rewrites must target /api/v2/dashboard.');
}
console.log(JSON.stringify({
  projectRoot: path.relative(path.dirname(backendRoot), backendRoot),
  functionPath,
  runtime: functionConfig.runtime,
  maxDuration: functionConfig.maxDuration,
  includeFiles: includedFiles,
  includedBytes,
  preflightTargetBytes: targetBytes,
  functionBudgetBytes: budgetBytes,
  rawDatabaseBytes: fs.existsSync(path.join(backendRoot, 'data', 'jobs_analytics.sqlite3'))
    ? fs.statSync(path.join(backendRoot, 'data', 'jobs_analytics.sqlite3')).size
    : null,
  databasePath,
  quickCheck,
  counts,
  modelArtifact: {
    path: path.relative(backendRoot, modelPath),
    modelVersion: modelArtifact.modelVersion,
    targetField: modelArtifact.targetField,
    vocabularySize: hydratedModel.vocabulary.size,
    classCount: hydratedModel.classDocumentCounts.size,
    testAccuracy: modelArtifact.evaluation?.accuracy ?? null,
    testMacroF1: modelArtifact.evaluation?.macroF1 ?? null,
  },
  rewritesVerified: true,
  note: 'Static local package check only; it does not replace a Vercel platform build or deployment.',
}, null, 2));
