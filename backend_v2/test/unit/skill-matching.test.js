import test from 'node:test';
import assert from 'node:assert/strict';
import { openReadOnlyDatabase } from '../../src/database.js';
import { SkillMatchingService } from '../../src/skill-matching.js';
import { createFixtureDatabase } from '../helpers.js';

test('matching resolves exact aliases and returns matched/missing skills with two explainable coverages', (t) => {
  const fixture = createFixtureDatabase();
  t.after(fixture.cleanup);
  const db = openReadOnlyDatabase(fixture.databasePath);
  t.after(() => db.close());
  const result = new SkillMatchingService(db).match({ skills: ['python', 'SQL'], limit: 5 });
  assert.equal(result.hiringProbability, false);
  assert.equal(result.userSuitabilityJudgement, false);
  assert.deepEqual(result.unknownSkills, []);
  const best = result.advertisements[0];
  assert.equal(best.advertisementId, 'job-1');
  assert.equal(best.userSkillCoveragePct, 100);
  assert.equal(best.advertisementSkillCoveragePct, 100);
  assert.deepEqual(best.missingSkills, []);
  assert.ok(result.roleProfiles.some((profile) => profile.title === 'Data Engineer'));
  const dataProfile = result.roleProfiles.find((profile) => profile.title === 'Data Engineer');
  assert.equal(dataProfile.userSkillCoveragePct, 100);
  assert.ok(dataProfile.missingCommonSkills.some((item) => item.skill === 'Apache Spark'));
});

test('unknown and ambiguous skills are reported instead of silently fuzzy-matched', (t) => {
  const fixture = createFixtureDatabase();
  t.after(fixture.cleanup);
  const db = openReadOnlyDatabase(fixture.databasePath);
  t.after(() => db.close());
  const service = new SkillMatchingService(db);
  const result = service.match({ skills: ['Quantum Not In Catalog'], limit: 5 });
  assert.deepEqual(result.unknownSkills, ['Quantum Not In Catalog']);
  assert.deepEqual(result.advertisements, []);
  const ambiguous = service.match({ skills: ['common'], limit: 5 });
  assert.equal(ambiguous.ambiguousSkills[0].input, 'common');
  assert.equal(ambiguous.ambiguousSkills[0].choices.length, 2);
});

test('filter validation rejects invalid work-mode values', (t) => {
  const fixture = createFixtureDatabase();
  t.after(fixture.cleanup);
  const db = openReadOnlyDatabase(fixture.databasePath);
  t.after(() => db.close());
  const service = new SkillMatchingService(db);
  assert.throws(() => service.match({ skills: ['SQL'], workMode: 'sometimes' }), { code: 'BAD_REQUEST' });
});
