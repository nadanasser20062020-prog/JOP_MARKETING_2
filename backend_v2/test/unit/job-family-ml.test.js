import test from 'node:test';
import assert from 'node:assert/strict';
import { openReadOnlyDatabase } from '../../src/database.js';
import { auditJobFamilyLabels, evaluateClassifier, splitByTextGroup, textGroupKey, TfidfMultinomialNB, tokenize, trainJobFamilyBaseline } from '../../src/job-family-ml.js';
import { createFixtureDatabase } from '../helpers.js';

test('text tokenizer emits word and adjacent-token features', () => {
  const terms = tokenize('Data Engineer builds data pipelines');
  assert.ok(terms.includes('data'));
  assert.ok(terms.includes('engineer'));
  assert.ok(terms.includes('data_engineer'));
});

test('equivalent normalized title/description sequences never cross partitions', () => {
  const records = [
    { title: 'Data Engineer', description: 'Build SQL pipelines' },
    { title: ' data   engineer ', description: 'BUILD sql pipelines' },
    { title: 'Frontend Engineer', description: 'Build web interfaces' },
  ];
  assert.equal(textGroupKey(records[0]), textGroupKey(records[1]));
  const split = splitByTextGroup(records);
  assert.equal(split[0].split, split[1].split);
});

test('TF-IDF Multinomial Naive Bayes fits a baseline and produces class metrics', () => {
  const records = [
    { text: 'python warehouse data pipeline', label: 'data' },
    { text: 'sql analytics warehouse dashboard', label: 'data' },
    { text: 'javascript browser ui components', label: 'frontend' },
    { text: 'css browser web interface', label: 'frontend' },
  ];
  const model = new TfidfMultinomialNB({ minDocumentFrequency: 1 }).fit(records);
  assert.equal(model.predict('python data warehouse'), 'data');
  assert.equal(model.predict('javascript browser interface'), 'frontend');
  const metrics = evaluateClassifier(['data', 'frontend'], ['data', 'data']);
  assert.equal(metrics.evaluatedRecords, 2);
  assert.equal(metrics.perClass.find((item) => item.label === 'frontend').recall, 0);
  assert.ok(metrics.macroF1 < 1);
});

test('grouped baseline evaluates labels without review-approval or minimum-support gates', () => {
  const records = [];
  for (let index = 0; index < 160; index += 1) {
    const label = index % 2 ? 'frontend' : 'data';
    records.push({ title: `${label} role ${index}`, description: label === 'data' ? `python warehouse ${index}` : `javascript browser ${index}`, label });
  }
  const result = trainJobFamilyBaseline({ records, minimumExamplesPerClass: 10_000 });
  assert.equal(result.leakageCheck.startsWith('passed'), true);
  assert.equal(result.splitCounts.test > 0, true);
  assert.ok(result.lowSupportClasses.length > 0);
  assert.ok(result.evaluation.perClass.every((item) => 'precision' in item && 'recall' in item && 'f1' in item));
});

test('label audit reports missing review provenance without defining prediction availability', (t) => {
  const fixture = createFixtureDatabase();
  t.after(fixture.cleanup);
  const db = openReadOnlyDatabase(fixture.databasePath);
  t.after(() => db.close());
  const audit = auditJobFamilyLabels(db);
  assert.equal(audit.decision, 'NO_GO');
  assert.match(audit.auditScope, /not a training or prediction gate/);
  assert.match(audit.targetField, /role_family/);
  assert.ok(audit.reasons.length > 0);
});
