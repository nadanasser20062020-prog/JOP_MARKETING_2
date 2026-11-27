'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { createServer } = require('node:http');
const { DatabaseSync } = require('node:sqlite');
const { createApiHandler } = require('../../backend/node/api');

const root = path.resolve(__dirname, '../..');
const database = new DatabaseSync(':memory:');
database.exec('PRAGMA foreign_keys = ON');
for (const migration of [
  '001_initial_sqlite_schema.sql',
  '002_full_archive_provenance.sql',
  '003_node_api_query_indexes.sql',
  '004_node_api_rollups.sql',
  '005_node_api_role_skill_lookup.sql',
]) {
  database.exec(fs.readFileSync(path.join(root, 'database/migrations', migration), 'utf8'));
}

function seedDatabase() {
  const addSource = database.prepare(`
    INSERT INTO data_sources (source_dataset, display_name, notes, source_kind, snapshot_bucket, date_semantics, listing_status, source_file_count, source_row_count)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  addSource.run('merged_tech_jobs', 'Merged Tech Jobs', 'Fixture source', 'job_export', 'other_snapshots', 'unverified', 'unknown_not_verified', 1, 4);
  addSource.run('international_jobs', 'International Tech Jobs', 'Historical fixture source', 'job_export', 'historical_sample', 'explicit_posted_at_2023', 'unknown_not_verified', 1, 1);

  const addFile = database.prepare(`
    INSERT INTO source_files (source_dataset, source_file, snapshot_group, snapshot_type, notes)
    VALUES (?, ?, ?, ?, ?)
  `);
  addFile.run('merged_tech_jobs', 'merged.csv', 'other_snapshots', 'other_snapshot', 'fixture');
  addFile.run('international_jobs', 'international.csv', 'historical_sample', 'historical_sample', 'fixture');

  const addSkill = database.prepare(`
    INSERT INTO skills (skill_id, canonical_name, category, match_policy, review_status, notes)
    VALUES (?, ?, ?, ?, ?, ?)
  `);
  addSkill.run('skill:python', 'Python', 'Programming', 'approved_aliases', 'curated', 'Reviewed');
  addSkill.run('skill:sql', 'SQL', 'Data', 'approved_aliases', 'curated', 'Reviewed');
  addSkill.run('skill:aws', 'AWS', 'Cloud', 'approved_aliases', 'curated', 'Reviewed');
  addSkill.run('skill:needs-review', 'Unreviewed Term', 'uncategorized', 'exact_only', 'needs_review', 'Not approved for matching');
  addSkill.run('skill:exact', 'Exact Term', 'Data', 'exact_only', 'curated_exact_only', 'Reviewed exact-only');

  const addAlias = database.prepare(`
    INSERT INTO skill_aliases (alias_normalized, alias_label, skill_id, alias_type, match_policy, review_status)
    VALUES (?, ?, ?, ?, ?, ?)
  `);
  addAlias.run('python', 'Python', 'skill:python', 'canonical', 'approved_aliases', 'curated');
  addAlias.run('py', 'Py', 'skill:python', 'curated_alias', 'approved_aliases', 'curated');
  addAlias.run('sql', 'SQL', 'skill:sql', 'canonical', 'approved_aliases', 'curated');
  addAlias.run('aws', 'AWS', 'skill:aws', 'canonical', 'approved_aliases', 'curated');
  addAlias.run('unreviewed term', 'Unreviewed Term', 'skill:needs-review', 'observed_unreviewed_exact', 'exact_only', 'needs_review');
  addAlias.run('exact term', 'Exact Term', 'skill:exact', 'canonical', 'exact_only', 'curated_exact_only');

  const addJob = database.prepare(`
    INSERT INTO jobs (
      record_id, source_dataset, source_file, source_row_number, title, company, country, city,
      description, posted_at, source_date_field, salary_raw, salary_year_avg, salary_hour_avg,
      salary_currency, salary_basis, salary_provenance_status, skills, source_url,
      listing_status, snapshot_type, exact_duplicate_within_source
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  addJob.run('merged:1', 'merged_tech_jobs', 'merged.csv', 1, 'Data Engineer', 'Alpha', 'Egypt', 'Cairo', '<p>Raw source description</p>', null, 'not_available', 'Not disclosed', null, null, null, null, 'not_available', 'Python, SQL', 'https://jobs.example/1', 'unknown_not_verified', 'other_snapshot', 'no');
  addJob.run('merged:2', 'merged_tech_jobs', 'merged.csv', 2, 'Data Scientist', 'Beta', 'United States', 'Remote', null, null, 'not_available', null, null, null, null, null, 'not_available', 'Python, SQL', null, 'unknown_not_verified', 'other_snapshot', 'no');
  addJob.run('merged:3', 'merged_tech_jobs', 'merged.csv', 3, 'Data Engineer', 'Gamma', 'Egypt', 'Alexandria', null, null, 'not_available', null, null, null, null, null, 'not_available', 'Python, AWS', null, 'unknown_not_verified', 'other_snapshot', 'no');
  addJob.run('merged:4', 'merged_tech_jobs', 'merged.csv', 4, 'Data Engineer', 'Delta', 'Egypt', null, null, null, 'not_available', null, null, null, null, null, 'not_available', null, null, 'unknown_not_verified', 'other_snapshot', 'no');
  addJob.run('international:1', 'international_jobs', 'international.csv', 1, 'Data Engineer', 'Epsilon', 'Canada', 'Toronto', null, '2023-03-12', 'posted_at_or_job_posted_date', null, null, null, null, null, 'not_available', 'Python', 'https://jobs.example/5', 'unknown_not_verified', 'historical_2023', 'no');

  const addLink = database.prepare(`
    INSERT INTO job_skills (
      record_id, source_dataset, source_file, skill_raw, skill_normalized, skill_id,
      skill_category, skill_match_policy, skill_review_status, skill_provenance, skill_status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  const link = (recordId, dataset, skillId, raw, policy = 'approved_aliases', review = 'curated', category = 'Programming') => {
    addLink.run(recordId, dataset, dataset === 'merged_tech_jobs' ? 'merged.csv' : 'international.csv', raw, raw.toLowerCase(), skillId, category, policy, review, 'fixture', 'present_in_base_export');
  };
  link('merged:1', 'merged_tech_jobs', 'skill:python', 'Python');
  link('merged:1', 'merged_tech_jobs', 'skill:sql', 'SQL', 'approved_aliases', 'curated', 'Data');
  link('merged:1', 'merged_tech_jobs', 'skill:needs-review', 'Unreviewed Term', 'exact_only', 'needs_review', 'uncategorized');
  link('merged:2', 'merged_tech_jobs', 'skill:python', 'Python');
  link('merged:2', 'merged_tech_jobs', 'skill:sql', 'SQL', 'approved_aliases', 'curated', 'Data');
  link('merged:3', 'merged_tech_jobs', 'skill:python', 'Python');
  link('merged:3', 'merged_tech_jobs', 'skill:aws', 'AWS', 'approved_aliases', 'curated', 'Cloud');
  link('international:1', 'international_jobs', 'skill:python', 'Python');

  database.prepare(`
    INSERT INTO import_runs (
      run_status, started_at, finished_at, pipeline_version, source_archive_run_id,
      archive_generated_on_utc, archive_job_rows, archive_job_skill_rows
    ) VALUES ('succeeded', '2026-10-28T00:00:00Z', '2026-10-28T00:01:00Z', 'test', 'fixture_run', '2026-10-28', 5, 8)
  `).run();

  database.prepare(`
    INSERT INTO learning_resources (
      resource_id, title, provider, resource_type, level, access_status, cost_status,
      account_requirement, credential, resource_url, verification_status, verified_on, notes
    ) VALUES ('res:python', 'Python course', 'Example Academy', 'course', 'beginner', 'available_unverified',
      'free_verified', 'account_required', 'none', 'https://learn.example/python', 'source_recorded', '2026-01-01', 'Fixture resource')
  `).run();
  database.prepare('INSERT INTO learning_resource_skills (resource_id, skill_id) VALUES (?, ?)').run('res:python', 'skill:python');
  database.prepare('INSERT INTO learning_resource_languages (resource_id, language_label) VALUES (?, ?)').run('res:python', 'English');
}

seedDatabase();
database.exec(fs.readFileSync(path.join(root, 'database/migrations/refresh_api_rollups.sql'), 'utf8'));
const server = createServer(createApiHandler({ getDatabase: () => database, appUrl: 'http://frontend.test' }));
let baseUrl;

test.before(async () => {
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

test.after(async () => {
  await new Promise((resolve) => server.close(resolve));
  database.close();
});

async function request(pathname, options) {
  const response = await fetch(`${baseUrl}${pathname}`, options);
  const json = response.status === 204 ? null : await response.json();
  return { response, json };
}

test('health is ready only when the local relational schema is present', async () => {
  const { response, json } = await request('/health');
  assert.equal(response.status, 200);
  assert.equal(json.data.status, 'ok');
  assert.equal(json.data.database.storage, 'local_sqlite');
  assert.equal(json.data.database.jobRecordCount, 5);
  assert.ok(json.meta.snapshot.archiveRunId === 'fixture_run');
});

test('metadata reports coverage, provenance, and no active-listing claim', async () => {
  const { response, json } = await request('/api/v1/metadata');
  assert.equal(response.status, 200);
  assert.equal(json.data.appUrl, 'http://frontend.test');
  assert.equal(json.data.dataset.totals.jobRecords, 5);
  assert.equal(json.data.dataset.totals.eligibleSkillIds, 3);
  assert.equal(json.data.dataset.totals.recordsWithEligibleSkills, 4);
  assert.equal(json.data.dataset.reliableDateCoverage.sourceDataset, 'international_jobs');
  assert.equal(json.data.productRules.listingStatus, 'No record is confirmed active.');
});

test('overview shares use the eligible-skill denominator and preserve missingness', async () => {
  const { response, json } = await request('/api/v1/overview');
  assert.equal(response.status, 200);
  assert.equal(json.data.kpis.totalJobs, 5);
  assert.equal(json.data.kpis.totalSkills, 3);
  assert.equal(json.data.kpis.totalCountries, 3);
  assert.equal(json.data.kpis.recordsWithEligibleSkills, 4);
  const python = json.data.topSkills.find((skill) => skill.skillId === 'skill:python');
  assert.equal(python.jobRecordCount, 4);
  assert.equal(python.denominator, 4);
  assert.equal(python.sharePercent, 100);
  assert.equal(json.data.marketComparison.groups[0].recordsWithEligibleSkills, 2);
  assert.equal(json.data.marketComparison.groups[1].recordsWithEligibleSkills, 1);
  assert.equal(json.data.marketComparison.comparisonName, 'Arab markets vs other represented markets');
});

test('job and role searches return paginated rows and successful empty results', async () => {
  const { response, json } = await request('/api/v1/jobs?q=engineer&page=1&pageSize=2&sort=company');
  assert.equal(response.status, 200);
  assert.equal(json.data.items.length, 2);
  assert.equal(json.data.pagination.totalItems, 4);
  assert.equal(json.data.pagination.hasNextPage, true);

  const skillFiltered = await request('/api/v1/jobs?skillId=skill%3Asql');
  assert.equal(skillFiltered.response.status, 200);
  assert.equal(skillFiltered.json.data.pagination.totalItems, 2);

  const empty = await request('/api/v1/jobs?q=zzzz');
  assert.equal(empty.response.status, 200);
  assert.deepEqual(empty.json.data.items, []);
  assert.equal(empty.json.data.pagination.totalItems, 0);

  const roles = await request('/api/v1/roles?q=data%20eng');
  assert.equal(roles.response.status, 200);
  assert.equal(roles.json.data.items[0].roleId, 'data engineer');
});

test('job details keep description as source text and expose only eligible reviewed skills', async () => {
  const { response, json } = await request('/api/v1/jobs/merged%3A1');
  assert.equal(response.status, 200);
  assert.equal(json.data.description, '<p>Raw source description</p>');
  assert.equal(json.data.sourceUrl, 'https://jobs.example/1');
  assert.deepEqual(json.data.reviewedSkills.map((skill) => skill.skillId), ['skill:python', 'skill:sql']);
  assert.equal(json.data.listingStatus, 'unknown_not_verified');
});

test('role analysis reports country and reviewed-skill denominators without unsupported salary estimates', async () => {
  const { response, json } = await request('/api/v1/roles/data%20engineer/analysis');
  assert.equal(response.status, 200);
  assert.equal(json.data.role.jobRecordCount, 4);
  assert.equal(json.data.role.recordsWithEligibleSkills, 3);
  assert.equal(json.data.countryDistribution.denominator, 4);
  assert.equal(json.data.salary.available, false);
  assert.equal(json.data.salary.recordsWithAnySalaryField, 1);
  assert.equal(json.data.salary.recordsWithUnavailableProvenance, 1);
  assert.equal(json.data.salary.annualValuesWithCurrencyAndMatchingPeriod, 0);
  const egyptSalaryCoverage = json.data.salary.byCountryCoverage.find((item) => item.country === 'Egypt');
  assert.equal(egyptSalaryCoverage.roleCountryRecordCount, 3);
  assert.equal(egyptSalaryCoverage.recordsWithAnySalaryField, 1);
  assert.equal(egyptSalaryCoverage.salaryFieldCoveragePercent, 33.33);
  assert.equal(egyptSalaryCoverage.recordsWithUnavailableProvenance, 1);
  assert.ok(json.data.skills.overall.some((skill) => skill.name === 'Python' && skill.denominator === 3));

  const emptyScope = await request('/api/v1/roles/data%20engineer/analysis?country=Japan');
  assert.equal(emptyScope.response.status, 200);
  assert.equal(emptyScope.json.data.role.jobRecordCount, 0);
  assert.deepEqual(emptyScope.json.data.skills.overall, []);
  assert.equal(emptyScope.json.data.salary.recordsWithAnySalaryField, 0);
  assert.deepEqual(emptyScope.json.data.salary.byCountryCoverage, []);

  const relatedAds = await request('/api/v1/roles/data%20engineer/ads?pageSize=2');
  assert.equal(relatedAds.response.status, 200);
  assert.equal(relatedAds.json.data.pagination.totalItems, 4);

  const unknownRole = await request('/api/v1/roles/imaginary%20role/analysis');
  assert.equal(unknownRole.response.status, 404);
});

test('skills, co-occurrence, and verified-free resource filter work', async () => {
  const skills = await request('/api/v1/skills?q=python');
  assert.equal(skills.response.status, 200);
  assert.equal(skills.json.data.items[0].skillId, 'skill:python');
  assert.equal(skills.json.data.denominator, 4);

  const related = await request('/api/v1/skills/co-occurrence?skillId=skill%3Apython');
  assert.equal(related.response.status, 200);
  assert.ok(related.json.data.skills.some((skill) => skill.skillId === 'skill:sql'));

  const resources = await request('/api/v1/skills/skill%3Apython/resources?freeOnly=true&language=English');
  assert.equal(resources.response.status, 200);
  assert.equal(resources.json.data.items.length, 1);
  assert.equal(resources.json.data.items[0].freeVerified, true);
});

test('historical trends are restricted to explicitly dated 2023 records', async () => {
  const { response, json } = await request('/api/v1/markets/trends?metric=jobRecords&year=2023&period=month');
  assert.equal(response.status, 200);
  assert.deepEqual(json.data.series, [{ month: '2023-03', jobRecordCount: 1 }]);
  const unsupported = await request('/api/v1/markets/trends?year=2024');
  assert.equal(unsupported.response.status, 422);
});

test('skill match returns a deterministic overlap explanation and rejects unreviewed aliases', async () => {
  const { response, json } = await request('/api/v1/matches', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ skills: ['Py', 'Python', 'unknown term'], limit: 10 }),
  });
  assert.equal(response.status, 200);
  assert.equal(json.data.input.recognizedSkills.length, 1);
  assert.deepEqual(json.data.input.recognizedSkills[0].inputLabels, ['Py', 'Python']);
  assert.equal(json.data.input.unrecognizedSkills[0].label, 'unknown term');
  assert.equal(json.data.results[0].roleId, 'data scientist');
  assert.equal(json.data.results[0].score, 0.5);
  assert.equal(json.data.algorithm.trainedModel, false);
  assert.match(json.data.warning, /not a hiring probability/);

  const unsupported = await request('/api/v1/matches', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ skills: ['Unreviewed Term'] }),
  });
  assert.equal(unsupported.response.status, 422);
  assert.equal(unsupported.json.error.code, 'NO_SUPPORTED_SKILLS');

  const invalidBody = await request('/api/v1/matches', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ skills: [] }),
  });
  assert.equal(invalidBody.response.status, 400);

  const wrongType = await request('/api/v1/matches', {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: 'skills=python',
  });
  assert.equal(wrongType.response.status, 415);
});

test('trained title-association model runs in Node and explains its uncalibrated score', async () => {
  const { response, json } = await request('/api/v1/models/role-title/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ skills: ['Python', 'SQL', 'unknown term'], limit: 3 }),
  });
  assert.equal(response.status, 200);
  assert.equal(json.data.model.trainedModel, true);
  assert.equal(json.data.model.id, 'positive_skill_naive_bayes_observed_title_v1');
  assert.equal(json.data.model.priorWeight, 2.5);
  assert.ok(json.data.model.heldOutTest.top1Accuracy > json.data.model.heldOutTest.priorOnlyTop1Accuracy);
  assert.ok(json.data.model.heldOutTest.top5Accuracy > json.data.model.heldOutTest.priorOnlyTop5Accuracy);
  assert.deepEqual(json.data.input.recognizedSkills.map((skill) => skill.name), ['Python', 'SQL']);
  assert.equal(json.data.input.unrecognizedSkills[0].label, 'unknown term');
  assert.equal(json.data.predictions.length, 3);
  assert.ok(json.data.predictions[0].trainingRecordCount >= 30);
  assert.ok(json.data.predictions[0].evidence.skillSignals.some((signal) => signal.name === 'Python'));
  assert.match(json.data.predictions[0].evidence.scoreSemantics, /uncalibrated/);
  assert.match(json.data.limitations[0], /does not assign a stable occupation/);

  const insufficient = await request('/api/v1/models/role-title/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ skills: ['Python', 'Unreviewed Term'] }),
  });
  assert.equal(insufficient.response.status, 422);
  assert.equal(insufficient.json.error.code, 'INSUFFICIENT_MODEL_SKILLS');
});

test('model status distinguishes trained ML from Jaccard and exploratory clustering', async () => {
  const { response, json } = await request('/api/v1/models/status');
  assert.equal(response.status, 200);
  assert.deepEqual(json.data.productionModels, []);
  assert.equal(json.data.servedModels.length, 1);
  assert.equal(json.data.servedModels[0].trainedModel, true);
  assert.equal(json.data.servedModels[0].priorWeight, 2.5);
  assert.ok(json.data.servedModels[0].heldOutTest.top1Accuracy > json.data.servedModels[0].heldOutTest.priorOnlyTop1Accuracy);
  assert.ok(json.data.servedModels[0].heldOutTest.top5Accuracy > json.data.servedModels[0].heldOutTest.priorOnlyTop5Accuracy);
  assert.ok(json.data.availableAlgorithms.some((item) => item.id === 'jaccard_skill_overlap' && item.trainedModel === false));
  assert.equal(json.data.offlineExperiments[0].serving, false);

  const methodology = await request('/api/v1/methodology');
  assert.equal(methodology.response.status, 200);
  assert.equal(methodology.json.data.machineLearning.route, 'POST /api/v1/models/role-title/predict');
  assert.match(methodology.json.data.salaries, /does not return a mean or median/);
});

test('validation, unsupported salary filters, and missing resources use documented error envelopes', async () => {
  const tooMany = await request('/api/v1/jobs?pageSize=101');
  assert.equal(tooMany.response.status, 400);
  assert.ok(tooMany.json.error.requestId);

  const salary = await request('/api/v1/jobs?minSalary=1000');
  assert.equal(salary.response.status, 422);
  assert.equal(salary.json.error.code, 'UNSUPPORTED_FILTER');

  const unsupported = await request('/api/v1/jobs?unsupported=yes');
  assert.equal(unsupported.response.status, 400);

  const missing = await request('/api/v1/jobs/not-a-record');
  assert.equal(missing.response.status, 404);
  assert.equal(missing.json.error.code, 'JOB_NOT_FOUND');
});

test('CORS allows only the configured app_url and preflight does not require request data', async () => {
  const { response } = await request('/api/v1/methodology', {
    method: 'OPTIONS',
    headers: { Origin: 'http://frontend.test' },
  });
  assert.equal(response.status, 204);
  assert.equal(response.headers.get('access-control-allow-origin'), 'http://frontend.test');

  const denied = await request('/api/v1/methodology', {
    method: 'OPTIONS',
    headers: { Origin: 'https://untrusted.example' },
  });
  assert.equal(denied.response.status, 204);
  assert.equal(denied.response.headers.get('access-control-allow-origin'), null);
});
