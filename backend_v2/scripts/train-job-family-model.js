import fs from 'node:fs';
import path from 'node:path';
import { gzipSync } from 'node:zlib';
import { config, backendRoot } from '../src/config.js';
import { openReadOnlyDatabase } from '../src/database.js';
import { trainRoleFamilyModel } from '../src/job-family-classifier.js';

const databasePath = path.resolve(process.env.DATASET_DB_PATH || config.databasePath);
const modelPath = path.resolve(process.env.JOB_FAMILY_MODEL_PATH || path.join(backendRoot, 'models', 'job-family-model.json.gz'));
const evaluationPath = path.resolve(process.env.JOB_FAMILY_EVALUATION_PATH || path.join(backendRoot, 'reports', 'job-family-model-evaluation.json'));
const options = {
  alpha: positiveNumber(process.env.JOB_FAMILY_ALPHA, 1),
  minDocumentFrequency: positiveInteger(process.env.JOB_FAMILY_MIN_DF, 2),
  maxFeatures: positiveInteger(process.env.JOB_FAMILY_MAX_FEATURES, 20_000),
  maxDescriptionCharacters: positiveInteger(process.env.JOB_FAMILY_MAX_DESCRIPTION_CHARS, 8_000),
  progressEvery: positiveInteger(process.env.JOB_FAMILY_PROGRESS_EVERY, 100_000),
  trainedAtUtc: process.env.JOB_FAMILY_TRAINED_AT_UTC,
};

fs.mkdirSync(path.dirname(modelPath), { recursive: true });
fs.mkdirSync(path.dirname(evaluationPath), { recursive: true });
const database = openReadOnlyDatabase(databasePath);
try {
  const auditColumns = new Set(database.rawConnectionForPreflight()
    .prepare('PRAGMA table_info("job_cleaning_audit")')
    .all()
    .map((row) => row.name));
  for (const required of ['title_clean', 'description_raw', 'role_family']) {
    if (!auditColumns.has(required)) throw new Error(`Training source must expose job_cleaning_audit.${required}; use the full source SQLite, not the compact Vercel projection.`);
  }

  console.log(JSON.stringify({ message: 'Training role_family classifier from stored labels.', databasePath, options }));
  const result = trainRoleFamilyModel(database, {
    ...options,
    onProgress: ({ stage, processed, total }) => {
      console.log(`${stage}: ${processed.toLocaleString('en-US')}${total ? ` / ${Number(total).toLocaleString('en-US')}` : ''}`);
    },
  });

  const compressedModel = gzipSync(Buffer.from(JSON.stringify(result.artifact)), { level: 9 });
  const temporaryModelPath = `${modelPath}.tmp`;
  fs.writeFileSync(temporaryModelPath, compressedModel);
  fs.renameSync(temporaryModelPath, modelPath);

  const evaluation = {
    modelVersion: result.artifact.modelVersion,
    targetField: result.artifact.targetField,
    featureFields: result.artifact.featureFields,
    algorithm: result.artifact.algorithm,
    trainedAtUtc: result.artifact.trainedAtUtc,
    training: result.artifact.training,
    evaluation: result.artifact.evaluation,
    modelArtifact: path.relative(backendRoot, modelPath),
    modelArtifactBytes: compressedModel.length,
  };
  fs.writeFileSync(evaluationPath, `${JSON.stringify(evaluation, null, 2)}\n`);
  console.log(JSON.stringify({
    modelPath,
    evaluationPath,
    labeledRecords: result.artifact.training.labeledRecords,
    splitCounts: result.splitCounts,
    classes: Object.keys(result.artifact.training.classCounts).length,
    vocabularySize: result.vocabularySize,
    accuracy: result.metrics.accuracy,
    macroF1: result.metrics.macroF1,
    weightedF1: result.metrics.weightedF1,
    testRecords: result.metrics.evaluatedRecords,
    modelArtifactBytes: compressedModel.length,
  }, null, 2));
} finally {
  database.close();
}

function positiveInteger(value, fallback) {
  const number = Number(value);
  return Number.isInteger(number) && number > 0 ? number : fallback;
}

function positiveNumber(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : fallback;
}
