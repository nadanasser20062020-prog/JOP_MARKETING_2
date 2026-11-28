import { createHash } from 'node:crypto';
import { normalizeKey } from './normalize.js';

const WORD = /[\p{L}\p{N}+#.]+/gu;
const DEFAULT_STOPWORDS = new Set(['the', 'and', 'for', 'with', 'from', 'into', 'our', 'you', 'your', 'are', 'will', 'that', 'this', 'job', 'role', 'work', 'team']);

export function tokenize(text, { stopwords = DEFAULT_STOPWORDS } = {}) {
  const tokens = String(text ?? '').normalize('NFKC').toLocaleLowerCase('en-US').match(WORD) || [];
  const filtered = tokens.map((token) => token.trim()).filter((token) => token.length > 1 && !stopwords.has(token));
  const terms = [...filtered];
  for (let index = 0; index + 1 < filtered.length; index += 1) {
    terms.push(`${filtered[index]}_${filtered[index + 1]}`);
  }
  return terms;
}

export function textGroupKey({ title = '', description = '' } = {}) {
  const sequence = tokenize(`${title} ${description}`).join(' ');
  return createHash('sha256').update(sequence).digest('hex');
}

export function splitByTextGroup(records, { salt = 'jop-role-family-v2' } = {}) {
  const splits = new Map();
  return records.map((record) => {
    const key = textGroupKey(record);
    let split = splits.get(key);
    if (!split) {
      const digest = createHash('sha256').update(`${salt}:${key}`).digest('hex');
      const bucket = Number.parseInt(digest.slice(0, 8), 16) % 100;
      split = bucket < 80 ? 'train' : bucket < 90 ? 'validation' : 'test';
      splits.set(key, split);
    }
    return { ...record, groupKey: key, split };
  });
}

function termWeights(terms, vocabulary, documentFrequency, documentCount) {
  const counts = new Map();
  for (const term of terms) {
    if (vocabulary.has(term)) counts.set(term, (counts.get(term) || 0) + 1);
  }
  const length = [...counts.values()].reduce((sum, value) => sum + value, 0) || 1;
  const weights = new Map();
  for (const [term, termCount] of counts) {
    const idf = Math.log((1 + documentCount) / (1 + (documentFrequency.get(term) || 0))) + 1;
    weights.set(term, (termCount / length) * idf);
  }
  return weights;
}

function documentWeights(text, vocabulary, documentFrequency, documentCount) {
  return termWeights(tokenize(text), vocabulary, documentFrequency, documentCount);
}

export class TfidfMultinomialNB {
  constructor({ alpha = 1, minDocumentFrequency = 2, maxFeatures = 25_000 } = {}) {
    this.alpha = alpha;
    this.minDocumentFrequency = minDocumentFrequency;
    this.maxFeatures = maxFeatures;
    this.vocabulary = new Map();
    this.documentFrequency = new Map();
    this.classDocumentCounts = new Map();
    this.classFeatureWeights = new Map();
    this.classFeatureTotals = new Map();
    this.documentCount = 0;
    this.fitted = false;
  }

  fit(records) {
    if (!Array.isArray(records) || records.length === 0) throw new Error('Training requires at least one labeled record.');
    const docTerms = [];
    const df = new Map();
    const classCounts = new Map();
    for (const record of records) {
      const label = normalizeKey(record.label);
      if (!label) continue;
      const terms = tokenize(record.text);
      const unique = new Set(terms);
      docTerms.push({ label, terms });
      classCounts.set(label, (classCounts.get(label) || 0) + 1);
      for (const term of unique) df.set(term, (df.get(term) || 0) + 1);
    }
    if (docTerms.length === 0) throw new Error('Training requires at least one non-empty label.');

    const candidates = [...df.entries()]
      .filter(([, frequency]) => frequency >= this.minDocumentFrequency)
      .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0], 'en'))
      .slice(0, this.maxFeatures);
    this.vocabulary = new Map(candidates.map(([term], index) => [term, index]));
    this.documentFrequency = new Map(candidates);
    this.documentCount = docTerms.length;
    this.classDocumentCounts = classCounts;
    this.classFeatureWeights = new Map([...classCounts.keys()].map((label) => [label, new Map()]));
    this.classFeatureTotals = new Map([...classCounts.keys()].map((label) => [label, 0]));

    for (const { label, terms } of docTerms) {
      const weights = termWeights(terms, this.vocabulary, this.documentFrequency, this.documentCount);
      const aggregate = this.classFeatureWeights.get(label);
      for (const [term, weight] of weights) aggregate.set(term, (aggregate.get(term) || 0) + weight);
      this.classFeatureTotals.set(label, this.classFeatureTotals.get(label) + [...weights.values()].reduce((sum, value) => sum + value, 0));
    }
    this.fitted = true;
    return this;
  }

  predict(text) {
    if (!this.fitted) throw new Error('Classifier has not been fitted.');
    const weights = documentWeights(text, this.vocabulary, this.documentFrequency, this.documentCount);
    const classCount = this.classDocumentCounts.size;
    const scores = [];
    for (const [label, documentCount] of this.classDocumentCounts) {
      const featureCounts = this.classFeatureWeights.get(label);
      const total = this.classFeatureTotals.get(label);
      let score = Math.log((documentCount + this.alpha) / (this.documentCount + this.alpha * classCount));
      const denominator = total + this.alpha * Math.max(1, this.vocabulary.size);
      for (const [term, weight] of weights) {
        score += weight * Math.log(((featureCounts.get(term) || 0) + this.alpha) / denominator);
      }
      scores.push({ label, score });
    }
    scores.sort((left, right) => right.score - left.score || left.label.localeCompare(right.label, 'en'));
    return scores[0]?.label ?? null;
  }
}

export function evaluateClassifier(actualLabels, predictedLabels) {
  if (actualLabels.length !== predictedLabels.length) throw new Error('Actual and predicted arrays must have the same length.');
  const labels = [...new Set([...actualLabels, ...predictedLabels].map(normalizeKey).filter(Boolean))].sort();
  const matrix = Object.fromEntries(labels.map((actual) => [actual, Object.fromEntries(labels.map((predicted) => [predicted, 0]))]));
  const support = new Map(labels.map((label) => [label, 0]));
  const predictedCount = new Map(labels.map((label) => [label, 0]));
  let correct = 0;
  for (let index = 0; index < actualLabels.length; index += 1) {
    const actual = normalizeKey(actualLabels[index]);
    const predicted = normalizeKey(predictedLabels[index]);
    if (!actual || !predicted) continue;
    matrix[actual][predicted] += 1;
    support.set(actual, support.get(actual) + 1);
    predictedCount.set(predicted, predictedCount.get(predicted) + 1);
    if (actual === predicted) correct += 1;
  }
  const perClass = labels.map((label) => {
    const truePositive = matrix[label][label];
    const classSupport = support.get(label);
    const precision = predictedCount.get(label) ? truePositive / predictedCount.get(label) : 0;
    const recall = classSupport ? truePositive / classSupport : 0;
    const f1 = precision + recall ? (2 * precision * recall) / (precision + recall) : 0;
    return { label, support: classSupport, precision, recall, f1 };
  });
  const total = perClass.reduce((sum, item) => sum + item.support, 0);
  const macroF1 = perClass.length ? perClass.reduce((sum, item) => sum + item.f1, 0) / perClass.length : 0;
  const weightedF1 = total ? perClass.reduce((sum, item) => sum + item.f1 * item.support, 0) / total : 0;
  return {
    evaluatedRecords: actualLabels.length,
    accuracy: actualLabels.length ? correct / actualLabels.length : 0,
    macroF1,
    weightedF1,
    perClass,
    confusionMatrix: matrix,
  };
}

export function auditJobFamilyLabels(database) {
  const overview = database.get(`
    SELECT COUNT(*) AS total,
           SUM(CASE WHEN role_family IS NOT NULL AND TRIM(role_family) <> '' THEN 1 ELSE 0 END) AS role_family_labeled,
           COUNT(DISTINCT NULLIF(TRIM(role_family), '')) AS role_family_class_count,
           SUM(CASE WHEN category_raw IS NOT NULL AND TRIM(category_raw) <> '' THEN 1 ELSE 0 END) AS source_category_labeled,
           COUNT(DISTINCT NULLIF(TRIM(category_raw), '')) AS source_category_class_count
    FROM job_cleaning_audit`);
  const roleFamilyClasses = database.all(`
    SELECT role_family AS label, COUNT(*) AS records
    FROM job_cleaning_audit
    WHERE role_family IS NOT NULL AND TRIM(role_family) <> ''
    GROUP BY role_family
    ORDER BY records DESC, label ASC`);
  const sourceCategoryClasses = database.all(`
    SELECT category_raw AS label, COUNT(*) AS records
    FROM job_cleaning_audit
    WHERE category_raw IS NOT NULL AND TRIM(category_raw) <> ''
    GROUP BY category_raw
    ORDER BY records DESC, label ASC`);
  const reviewColumns = database.all(`PRAGMA table_info("job_cleaning_audit")`).map((row) => row.name)
    .filter((name) => /review|label_source|label_provenance|category_verified/i.test(name));
  const labelCoveragePct = overview.total ? (Number(overview.source_category_labeled) / Number(overview.total)) * 100 : 0;
  const reasons = [];
  if (reviewColumns.length === 0) reasons.push('The database has no label-review/provenance field to identify a human-reviewed training set.');
  if (Number(overview.source_category_labeled) < 5_000) reasons.push(`The source category field is populated on only ${Number(overview.source_category_labeled).toLocaleString()} of ${Number(overview.total).toLocaleString()} advertisements (${labelCoveragePct.toFixed(2)}%).`);
  if (sourceCategoryClasses.some((row) => Number(row.records) < 50)) reasons.push('Some source-category classes have fewer than 50 examples; rare labels cannot support reliable held-out evaluation.');
  reasons.push('The populated role_family field is a derived label and is not marked as independently reviewed in this database.');

  return {
    decision: 'NO_GO',
    auditScope: 'label quality/provenance only; not a training or prediction gate',
    targetField: 'role_family (active classifier target); category_raw is reported separately as a sparse source-label field',
    totalAdvertisements: Number(overview.total),
    roleFamilyLabelCoverage: Number(overview.role_family_labeled),
    roleFamilyClassCount: Number(overview.role_family_class_count),
    sourceCategoryLabelCount: Number(overview.source_category_labeled),
    sourceCategoryClassCount: Number(overview.source_category_class_count),
    sourceCategoryCoveragePct: Number(labelCoveragePct.toFixed(4)),
    labelReviewMetadata: reviewColumns,
    minimumSourceCategoryClassSupport: sourceCategoryClasses.length ? Math.min(...sourceCategoryClasses.map((row) => Number(row.records))) : 0,
    roleFamilyClasses: roleFamilyClasses.map((row) => ({ label: row.label, records: Number(row.records) })),
    sourceCategoryClasses: sourceCategoryClasses.map((row) => ({ label: row.label, records: Number(row.records) })),
    reasons,
    nextSteps: [
      'Treat the provenance warning as an interpretation caveat; it does not prevent fitting the stored role_family labels.',
      'Inspect per-class test metrics and manually review low-support/error cases in job-family-model-evaluation.json.',
      'If independent human-reviewed labels become available, evaluate them separately without disabling the existing classifier.',
    ],
  };
}

function textForRecord(record) {
  return record.text ?? `${record.title ?? ''} ${record.description ?? ''}`;
}

export function trainJobFamilyBaseline({ records, minimumExamplesPerClass = 50 } = {}) {
  const splitRecords = splitByTextGroup(records);
  const classCounts = new Map();
  for (const record of splitRecords) classCounts.set(normalizeKey(record.label), (classCounts.get(normalizeKey(record.label)) || 0) + 1);
  const lowSupportClasses = [...classCounts.entries()]
    .filter(([, value]) => value < minimumExamplesPerClass)
    .map(([label, recordsCount]) => ({ label, records: recordsCount }));
  const train = splitRecords.filter((record) => record.split === 'train');
  const test = splitRecords.filter((record) => record.split === 'test');
  if (!train.length || !test.length) throw new Error('Grouped split produced an empty train or test partition.');
  const model = new TfidfMultinomialNB().fit(train.map((record) => ({ text: textForRecord(record), label: record.label })));
  const predictions = test.map((record) => model.predict(textForRecord(record)));
  const evaluation = evaluateClassifier(test.map((record) => record.label), predictions);
  const groupAssignments = new Map();
  for (const row of splitRecords) {
    const prior = groupAssignments.get(row.groupKey);
    if (prior && prior !== row.split) throw new Error('Equivalent text group crossed train/validation/test boundaries.');
    groupAssignments.set(row.groupKey, row.split);
  }
  return {
    model,
    evaluation,
    splitCounts: Object.fromEntries(['train', 'validation', 'test'].map((split) => [split, splitRecords.filter((row) => row.split === split).length])),
    groupedTextCount: groupAssignments.size,
    lowSupportClasses,
    leakageCheck: 'passed: normalized title/description token sequences are assigned to one split',
  };
}
