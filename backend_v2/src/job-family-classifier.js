import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import fs from 'node:fs';
import { TfidfMultinomialNB, evaluateClassifier, textGroupKey, tokenize } from './job-family-ml.js';
import { normalizeKey } from './normalize.js';

export const JOB_FAMILY_MODEL_VERSION = 'role-family-tfidf-mnb-v1';
export const DEFAULT_MODEL_OPTIONS = Object.freeze({
  alpha: 1,
  minDocumentFrequency: 2,
  maxFeatures: 20_000,
  maxDescriptionCharacters: 8_000,
  splitSalt: 'jop-role-family-v2',
});

function splitForGroupKey(groupKey, salt) {
  const digest = createHash('sha256').update(`${salt}:${groupKey}`).digest('hex');
  const bucket = Number.parseInt(digest.slice(0, 8), 16) % 100;
  return bucket < 80 ? 'train' : bucket < 90 ? 'validation' : 'test';
}

function rowSplit(row, salt) {
  const groupKey = textGroupKey({ title: row.title, description: row.description });
  return { groupKey, split: splitForGroupKey(groupKey, salt) };
}

function recordText(row) {
  return `${row.title ?? ''} ${row.description ?? ''}`.trim();
}

function countVocabularyTerms(text, vocabulary) {
  const counts = new Map();
  for (const term of tokenize(text)) {
    if (vocabulary.has(term)) counts.set(term, (counts.get(term) || 0) + 1);
  }
  return counts;
}

function addTrainingDocument(model, label, text) {
  const counts = countVocabularyTerms(text, model.vocabulary);
  const length = [...counts.values()].reduce((sum, value) => sum + value, 0) || 1;
  const classWeights = model.classFeatureWeights.get(label);
  let totalWeight = 0;
  for (const [term, termCount] of counts) {
    const idf = Math.log((1 + model.documentCount) / (1 + (model.documentFrequency.get(term) || 0))) + 1;
    const weight = (termCount / length) * idf;
    classWeights.set(term, (classWeights.get(term) || 0) + weight);
    totalWeight += weight;
  }
  model.classFeatureTotals.set(label, model.classFeatureTotals.get(label) + totalWeight);
}

function sourceRows(database, maxDescriptionCharacters) {
  return database.iterate(`
    SELECT title_clean AS title,
           SUBSTR(COALESCE(description_raw, ''), 1, ?) AS description,
           role_family AS label
    FROM job_cleaning_audit
    WHERE role_family IS NOT NULL AND TRIM(role_family) <> ''`, maxDescriptionCharacters);
}

function emitProgress(onProgress, stage, processed, total) {
  if (typeof onProgress === 'function') onProgress({ stage, processed, total });
}

export function trainRoleFamilyModel(database, options = {}) {
  const settings = { ...DEFAULT_MODEL_OPTIONS, ...options };
  const allClassCounts = new Map();
  const splitCounts = { train: 0, validation: 0, test: 0 };
  const trainClassCounts = new Map();
  const documentFrequency = new Map();
  const progressEvery = Math.max(1, Number(settings.progressEvery || 100_000));
  const expectedLabeledRecords = Number(database.get(`
    SELECT COUNT(*) AS count FROM job_cleaning_audit
    WHERE role_family IS NOT NULL AND TRIM(role_family) <> ''`)?.count ?? 0);
  let totalLabeledRecords = 0;
  let titleTextRecords = 0;
  let descriptionTextRecords = 0;
  let processed = 0;

  for (const row of sourceRows(database, settings.maxDescriptionCharacters)) {
    const label = normalizeKey(row.label);
    if (!label) continue;
    const { split } = rowSplit(row, settings.splitSalt);
    totalLabeledRecords += 1;
    processed += 1;
    allClassCounts.set(label, (allClassCounts.get(label) || 0) + 1);
    splitCounts[split] += 1;
    if (String(row.title ?? '').trim()) titleTextRecords += 1;
    if (String(row.description ?? '').trim()) descriptionTextRecords += 1;

    if (split === 'train') {
      trainClassCounts.set(label, (trainClassCounts.get(label) || 0) + 1);
      const uniqueTerms = new Set(tokenize(recordText(row)));
      for (const term of uniqueTerms) documentFrequency.set(term, (documentFrequency.get(term) || 0) + 1);
    }
    if (processed % progressEvery === 0) emitProgress(settings.onProgress, 'document-frequency', processed, expectedLabeledRecords);
  }

  if (totalLabeledRecords !== expectedLabeledRecords) {
    throw new Error(`The role_family label count changed during training: expected ${expectedLabeledRecords}, read ${totalLabeledRecords}.`);
  }

  const candidates = [...documentFrequency.entries()]
    .filter(([, frequency]) => frequency >= settings.minDocumentFrequency)
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0], 'en'))
    .slice(0, settings.maxFeatures);
  const model = new TfidfMultinomialNB({
    alpha: settings.alpha,
    minDocumentFrequency: settings.minDocumentFrequency,
    maxFeatures: settings.maxFeatures,
  });
  model.vocabulary = new Map(candidates.map(([term], index) => [term, index]));
  model.documentFrequency = new Map(candidates);
  model.documentCount = splitCounts.train;
  model.classDocumentCounts = trainClassCounts;
  model.classFeatureWeights = new Map([...trainClassCounts.keys()].map((label) => [label, new Map()]));
  model.classFeatureTotals = new Map([...trainClassCounts.keys()].map((label) => [label, 0]));
  model.fitted = true;

  processed = 0;
  for (const row of sourceRows(database, settings.maxDescriptionCharacters)) {
    const label = normalizeKey(row.label);
    if (label && rowSplit(row, settings.splitSalt).split === 'train') addTrainingDocument(model, label, recordText(row));
    processed += 1;
    if (processed % progressEvery === 0) emitProgress(settings.onProgress, 'fit-class-weights', processed, totalLabeledRecords);
  }

  const actualLabels = [];
  const predictedLabels = [];
  const testGroupKeys = new Set();
  processed = 0;
  for (const row of sourceRows(database, settings.maxDescriptionCharacters)) {
    if (normalizeKey(row.label) && rowSplit(row, settings.splitSalt).split === 'test') {
      actualLabels.push(normalizeKey(row.label));
      predictedLabels.push(model.predict(recordText(row)));
      testGroupKeys.add(rowSplit(row, settings.splitSalt).groupKey);
    }
    processed += 1;
    if (processed % progressEvery === 0) emitProgress(settings.onProgress, 'evaluate-test-split', processed, totalLabeledRecords);
  }

  const metrics = evaluateClassifier(actualLabels, predictedLabels);
  const classCounts = Object.fromEntries([...allClassCounts.entries()].sort((a, b) => a[0].localeCompare(b[0], 'en')));
  const trainClassCountsObject = Object.fromEntries([...trainClassCounts.entries()].sort((a, b) => a[0].localeCompare(b[0], 'en')));
  const artifact = {
    schemaVersion: 1,
    modelVersion: JOB_FAMILY_MODEL_VERSION,
    trainedAtUtc: settings.trainedAtUtc || new Date().toISOString(),
    targetField: 'role_family',
    featureFields: ['title_clean', 'description_raw'],
    algorithm: 'TF-IDF word unigrams/bigrams + Multinomial Naive Bayes',
    training: {
      labeledRecords: totalLabeledRecords,
      classCounts,
      trainClassCounts: trainClassCountsObject,
      featureCoverage: {
        titleRecords: titleTextRecords,
        descriptionRecords: descriptionTextRecords,
        descriptionCoveragePct: totalLabeledRecords ? Number(((descriptionTextRecords / totalLabeledRecords) * 100).toFixed(4)) : 0,
      },
      splitCounts,
      uniqueTestTextGroups: testGroupKeys.size,
      splitSalt: settings.splitSalt,
      splitMethod: 'SHA-256 of normalized title/description token sequence; identical token sequences are assigned to one split',
      maxDescriptionCharacters: settings.maxDescriptionCharacters,
    },
    evaluation: {
      ...metrics,
      evaluationSplit: 'test',
      splitCounts,
    },
    model: serializeRoleFamilyModel(model),
  };

  return { artifact, model, metrics, splitCounts, vocabularySize: model.vocabulary.size };
}

export function serializeRoleFamilyModel(model) {
  return {
    algorithm: JOB_FAMILY_MODEL_VERSION,
    alpha: model.alpha,
    minDocumentFrequency: model.minDocumentFrequency,
    maxFeatures: model.maxFeatures,
    documentCount: model.documentCount,
    vocabulary: [...model.vocabulary.keys()],
    documentFrequency: [...model.documentFrequency.entries()],
    classDocumentCounts: [...model.classDocumentCounts.entries()],
    classFeatureTotals: [...model.classFeatureTotals.entries()],
    classFeatureWeights: [...model.classFeatureWeights.entries()].map(([label, weights]) => [label, [...weights.entries()]]),
  };
}

export function hydrateRoleFamilyModel(serialized) {
  if (!serialized || serialized.algorithm !== JOB_FAMILY_MODEL_VERSION || !Array.isArray(serialized.vocabulary)) {
    throw new Error('Unsupported or invalid role-family model artifact.');
  }
  const model = new TfidfMultinomialNB({
    alpha: Number(serialized.alpha ?? 1),
    minDocumentFrequency: Number(serialized.minDocumentFrequency ?? 2),
    maxFeatures: Number(serialized.maxFeatures ?? 20_000),
  });
  model.vocabulary = new Map(serialized.vocabulary.map((term, index) => [term, index]));
  model.documentFrequency = new Map(serialized.documentFrequency || []);
  model.documentCount = Number(serialized.documentCount || 0);
  model.classDocumentCounts = new Map(serialized.classDocumentCounts || []);
  model.classFeatureTotals = new Map(serialized.classFeatureTotals || []);
  model.classFeatureWeights = new Map((serialized.classFeatureWeights || []).map(([label, entries]) => [label, new Map(entries)]));
  model.fitted = model.documentCount > 0 && model.classDocumentCounts.size > 0 && model.vocabulary.size > 0;
  if (!model.fitted) throw new Error('Role-family model artifact is empty or incomplete.');
  return model;
}

export function readRoleFamilyModelArtifact(modelPath) {
  const stored = fs.readFileSync(modelPath);
  const jsonBytes = String(modelPath).toLowerCase().endsWith('.gz') ? gunzipSync(stored) : stored;
  const artifact = JSON.parse(jsonBytes.toString('utf8'));
  if (artifact.schemaVersion !== 1 || !artifact.model) throw new Error('Unsupported role-family model artifact schema.');
  return { artifact, model: hydrateRoleFamilyModel(artifact.model) };
}
