import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { gzipSync } from 'node:zlib';
import {
  hydrateRoleFamilyModel,
  readRoleFamilyModelArtifact,
  trainRoleFamilyModel,
} from '../../src/job-family-classifier.js';

function trainingRows() {
  return Array.from({ length: 240 }, (_, index) => {
    const dataRole = index % 2 === 0;
    return {
      title: dataRole ? `Data Engineer posting ${index}` : `Software Engineer posting ${index}`,
      description: dataRole
        ? 'Python SQL warehouse ETL data pipelines analytics'
        : 'JavaScript React browser frontend software components',
      label: dataRole ? 'data_engineering' : 'software_engineering',
      category_raw: dataRole ? 'hardware' : 'data science',
    };
  });
}

function fakeDatabase(rows) {
  return {
    get() { return { count: rows.length }; },
    iterate(_sql, maxDescriptionCharacters) {
      return rows.map((row) => ({
        title: row.title,
        description: row.description.slice(0, maxDescriptionCharacters),
        label: row.label,
      }))[Symbol.iterator]();
    },
  };
}

test('streams role_family labels into a text model without approval gates or category_raw', () => {
  const rows = trainingRows();
  const result = trainRoleFamilyModel(fakeDatabase(rows), {
    minDocumentFrequency: 1,
    maxFeatures: 2_000,
    progressEvery: 10_000,
  });

  assert.equal(result.artifact.targetField, 'role_family');
  assert.equal(result.artifact.training.labeledRecords, rows.length);
  assert.equal(result.artifact.training.featureCoverage.titleRecords, rows.length);
  assert.equal(result.artifact.training.featureCoverage.descriptionRecords, rows.length);
  assert.deepEqual(Object.keys(result.artifact.training.classCounts).sort(), ['data_engineering', 'software_engineering']);
  assert.ok(result.splitCounts.train > 0);
  assert.ok(result.splitCounts.test > 0);
  assert.equal(result.model.predict('Data Engineer Python SQL warehouse ETL'), 'data_engineering');
  assert.equal(result.model.predict('Software Engineer JavaScript React frontend'), 'software_engineering');
  assert.equal(result.artifact.evaluation.evaluationSplit, 'test');
  assert.ok(result.artifact.evaluation.evaluatedRecords > 0);
  assert.equal(result.artifact.evaluation.perClass.length, 2);
});

test('role-family artifact hydrates and reads from a compressed model file', (t) => {
  const result = trainRoleFamilyModel(fakeDatabase(trainingRows()), {
    minDocumentFrequency: 1,
    maxFeatures: 2_000,
  });
  const hydrated = hydrateRoleFamilyModel(result.artifact.model);
  assert.equal(hydrated.predict('Python SQL data warehouse'), 'data_engineering');

  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'jop-role-family-model-'));
  const artifactPath = path.join(directory, 'model.json.gz');
  fs.writeFileSync(artifactPath, gzipSync(Buffer.from(JSON.stringify(result.artifact))));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));

  const loaded = readRoleFamilyModelArtifact(artifactPath);
  assert.equal(loaded.artifact.targetField, 'role_family');
  assert.equal(loaded.model.predict('JavaScript React browser frontend'), 'software_engineering');
});
