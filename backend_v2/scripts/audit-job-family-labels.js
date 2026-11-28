import fs from 'node:fs';
import path from 'node:path';
import { config, backendRoot } from '../src/config.js';
import { openReadOnlyDatabase } from '../src/database.js';
import { auditJobFamilyLabels } from '../src/job-family-ml.js';

const databasePath = process.env.DATASET_DB_PATH || config.databasePath;
const reportsDir = path.join(backendRoot, 'reports');
fs.mkdirSync(reportsDir, { recursive: true });
const db = openReadOnlyDatabase(databasePath);
let result;
try {
  result = auditJobFamilyLabels(db);
} finally {
  db.close();
}

const jsonPath = path.join(reportsDir, 'job-family-readiness.json');
const markdownPath = path.join(reportsDir, 'job-family-no-go.md');
const modelEvaluationPath = path.join(reportsDir, 'job-family-model-evaluation.json');
let modelEvaluation = null;
if (fs.existsSync(modelEvaluationPath)) {
  try {
    const parsed = JSON.parse(fs.readFileSync(modelEvaluationPath, 'utf8'));
    if (parsed?.evaluation && parsed?.modelVersion && parsed?.targetField) modelEvaluation = parsed;
  } catch {
    // The label audit remains useful if the separately generated model report is absent or corrupt.
  }
}
fs.writeFileSync(jsonPath, `${JSON.stringify(result, null, 2)}\n`);
const sourceRows = result.sourceCategoryClasses
  .map((item) => `| ${String(item.label).replaceAll('|', '\\|')} | ${item.records.toLocaleString('en-US')} |`)
  .join('\n');
const familyRows = result.roleFamilyClasses
  .map((item) => `| ${item.label} | ${item.records.toLocaleString('en-US')} |`)
  .join('\n');
const modelEvaluationLines = modelEvaluation
  ? [
      `- Model: **${modelEvaluation.modelVersion}**, target **${modelEvaluation.targetField}**.`,
      `- Test metrics on ${modelEvaluation.evaluation.evaluatedRecords.toLocaleString('en-US')} records: accuracy **${(modelEvaluation.evaluation.accuracy * 100).toFixed(4)}%**, Macro-F1 **${(modelEvaluation.evaluation.macroF1 * 100).toFixed(4)}%**, weighted-F1 **${(modelEvaluation.evaluation.weightedF1 * 100).toFixed(4)}%**.`,
      ...(modelEvaluation.training?.featureCoverage ? [`- Text coverage: title on ${modelEvaluation.training.featureCoverage.titleRecords.toLocaleString('en-US')} records; description on ${modelEvaluation.training.featureCoverage.descriptionRecords.toLocaleString('en-US')} (${modelEvaluation.training.featureCoverage.descriptionCoveragePct}% of the labeled set).`] : []),
      '- Metrics measure agreement with stored labels, not independent human-reviewed ground truth.',
      '- Full per-class scores and confusion matrix: `job-family-model-evaluation.json`.',
    ]
  : ['- No model evaluation report exists yet; this audit does not prevent training or prediction.'];
const markdown = [
  '# Job-family label-quality audit — non-blocking NO-GO',
  '',
  `**Audit decision:** ${result.decision} for label provenance only; it is not a training or prediction gate. The report uses the SQLite database reconstructed from only the 11 authorized NADA parts.`,
  '',
  '## Why the label-quality audit flags risks',
  '',
  ...result.reasons.map((reason) => `- ${reason}`),
  '',
  '## Label inventory',
  '',
  `- Total advertisements: **${result.totalAdvertisements.toLocaleString('en-US')}**`,
  `- Derived role_family labels: **${result.roleFamilyLabelCoverage.toLocaleString('en-US')}** across **${result.roleFamilyClassCount}** classes. The database has no human-review/provenance field for these labels, so the count alone is not evidence of a reviewed ground truth.`,
  `- Source category_raw labels: **${result.sourceCategoryLabelCount.toLocaleString('en-US')}** (**${result.sourceCategoryCoveragePct}%** coverage) across **${result.sourceCategoryClassCount}** values.`,
  `- Review/provenance columns available: **${result.labelReviewMetadata.length ? result.labelReviewMetadata.join(', ') : 'none'}**.`,
  `- Smallest source-category class: **${result.minimumSourceCategoryClassSupport}** examples.`,
  '',
  '### Existing derived role_family counts',
  '',
  '| Label | Records |',
  '|---|---:|',
  familyRows,
  '',
  '### Source category counts',
  '',
  '| Source category | Records |',
  '|---|---:|',
  sourceRows,
  '',
  '## Model evaluation and inference',
  '',
  ...modelEvaluationLines,
  '',
  'The label audit is informational. The API serves predictions whenever a valid `models/job-family-model.json.gz` artifact is present; missing/corrupt model files are reported independently from label provenance.',
  '',
  '## Non-blocking quality follow-up',
  '',

  ...result.nextSteps.map((step, index) => `${index + 1}. ${step}`),
  '',
].join('\n');
fs.writeFileSync(markdownPath, markdown);
console.log(`Wrote ${path.relative(backendRoot, jsonPath)} and ${path.relative(backendRoot, markdownPath)}; decision=${result.decision}.`);
