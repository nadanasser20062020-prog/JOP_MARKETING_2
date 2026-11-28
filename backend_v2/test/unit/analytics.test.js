import test from 'node:test';
import assert from 'node:assert/strict';
import { openReadOnlyDatabase } from '../../src/database.js';
import { AnalyticsService } from '../../src/analytics-service.js';
import { createFixtureDatabase } from '../helpers.js';

test('overview counts all advertisements and identifies the most-advertised title', (t) => {
  const fixture = createFixtureDatabase();
  t.after(fixture.cleanup);
  const db = openReadOnlyDatabase(fixture.databasePath);
  t.after(() => db.close());
  const overview = new AnalyticsService(db).overview();
  assert.equal(overview.totalJobs, 5);
  assert.equal(overview.distinctRoles, 2);
  assert.equal(overview.topRole.title, 'Data Engineer');
  assert.equal(overview.topRole.advertisementCount, 3);
  assert.equal(overview.salaryCoverage.USD, 4);
});

test('role report returns both role share by country and role demand within each country', (t) => {
  const fixture = createFixtureDatabase();
  t.after(fixture.cleanup);
  const db = openReadOnlyDatabase(fixture.databasePath);
  t.after(() => db.close());
  const report = new AnalyticsService(db).roleReport(' DATA   ENGINEER ');
  assert.equal(report.advertisementCount, 3);
  const egypt = report.countryDemand.find((row) => row.country === 'Egypt');
  assert.equal(egypt.roleAdvertisements, 2);
  assert.equal(egypt.totalAdvertisementsInCountry, 3);
  assert.equal(egypt.roleShareOfItsAdvertisementsPct, 66.6667);
  assert.equal(egypt.roleDemandWithinCountryPct, 66.6667);
  assert.equal(report.mostDemandCountries[0].country, 'Egypt');
});

test('annual salary means and ranges use the populated currency-specific annual columns', (t) => {
  const fixture = createFixtureDatabase();
  t.after(fixture.cleanup);
  const db = openReadOnlyDatabase(fixture.databasePath);
  t.after(() => db.close());
  const report = new AnalyticsService(db).roleReport('data engineer');
  const egypt = report.annualSalaryByCountry.find((row) => row.country === 'Egypt');
  const usd = egypt.currencies.find((item) => item.currency === 'USD');
  assert.equal(usd.period, 'annual');
  assert.equal(usd.records, 2);
  assert.equal(usd.mean, 117500);
  assert.deepEqual(usd.range, { minimum: 90000, maximum: 150000 });
  assert.deepEqual(usd.estimateStatusCounts, { estimated: 2, actual: 0, unverified: 0 });
});

test('role skill frequencies, technology co-occurrence, and work-mode percentages are consistent', (t) => {
  const fixture = createFixtureDatabase();
  t.after(fixture.cleanup);
  const db = openReadOnlyDatabase(fixture.databasePath);
  t.after(() => db.close());
  const report = new AnalyticsService(db).roleReport('data engineer');
  assert.equal(report.skills.find((item) => item.skill === 'SQL').advertisementCount, 2);
  assert.equal(report.skills.find((item) => item.skill === 'SQL').appearancePctOfRoleAds, 66.6667);
  assert.ok(report.technologyCombinations.some((item) => item.firstSkill === 'Python' && item.secondSkill === 'SQL' && item.cooccurrenceAdvertisements === 1));
  assert.equal(report.workMode.remotePct, 66.6667);
  assert.equal(report.workMode.nonRemotePct, 33.3333);
  assert.equal(report.workMode.remotePct + report.workMode.nonRemotePct + report.workMode.hybridPct + report.workMode.unknownPct, 100);
});

test('Arab-versus-international comparison separates unknown locations and preserves currency', (t) => {
  const fixture = createFixtureDatabase();
  t.after(fixture.cleanup);
  const db = openReadOnlyDatabase(fixture.databasePath);
  t.after(() => db.close());
  const comparison = new AnalyticsService(db).arabVsInternational(10);
  assert.equal(comparison.counts.find((row) => row.market === 'arab').advertisementCount, 3);
  assert.equal(comparison.counts.find((row) => row.market === 'international').advertisementCount, 1);
  assert.equal(comparison.counts.find((row) => row.market === 'unknown').advertisementCount, 1);
  assert.ok(comparison.salaries.find((row) => row.market === 'arab').currencies.some((item) => item.currency === 'EGP' && item.records > 0));
});
