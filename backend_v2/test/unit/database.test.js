import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { gzipSync } from 'node:zlib';
import { openReadOnlyDatabase } from '../../src/database.js';
import { createFixtureDatabase } from '../helpers.js';

test('read-only adapter validates the required schema and cannot write', (t) => {
  const fixture = createFixtureDatabase();
  t.after(fixture.cleanup);
  const db = openReadOnlyDatabase(fixture.databasePath);
  t.after(() => db.close());
  assert.equal(db.get('SELECT COUNT(*) AS n FROM job_cleaning_audit').n, 5);
  assert.throws(() => db.rawConnectionForPreflight().exec("INSERT INTO job_cleaning_audit(record_id) VALUES ('not-allowed')"));
});

test('gzip-compressed SQLite deployment files materialize and pass the same read-only schema gate', (t) => {
  const fixture = createFixtureDatabase();
  t.after(fixture.cleanup);
  const archivePath = `${fixture.databasePath}.gz`;
  fs.writeFileSync(archivePath, gzipSync(fs.readFileSync(fixture.databasePath)));

  const db = openReadOnlyDatabase(archivePath);
  t.after(() => db.close());
  assert.equal(db.get('SELECT COUNT(*) AS n FROM job_cleaning_audit').n, 5);
  assert.throws(() => db.rawConnectionForPreflight().exec("INSERT INTO job_cleaning_audit(record_id) VALUES ('not-allowed')"));
});

test('schema preflight reports a clear error for a missing database', () => {
  assert.throws(() => openReadOnlyDatabase('/definitely/not/a/database.sqlite3'), { code: 'DATABASE_NOT_FOUND' });
});
