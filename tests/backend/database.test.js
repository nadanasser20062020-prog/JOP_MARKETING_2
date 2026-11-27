'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { DatabaseSync } = require('node:sqlite');
const { openReadOnlyDatabase } = require('../../backend/node/database');
const { resolveDatabasePath } = require('../../backend/config/database');
const { normalizeExactLabel } = require('../../backend/node/queries');

const root = path.resolve(__dirname, '../..');

function applyMigrations(database) {
  for (const migration of [
    '001_initial_sqlite_schema.sql',
    '002_full_archive_provenance.sql',
    '003_node_api_query_indexes.sql',
    '004_node_api_rollups.sql',
    '005_node_api_role_skill_lookup.sql',
  ]) {
    database.exec(fs.readFileSync(path.join(root, 'database/migrations', migration), 'utf8'));
  }
}

test('Node API opens a local SQLite file read-only', () => {
  const temporaryDirectory = fs.mkdtempSync(path.join(root, '.jop-api-test-'));
  const databasePath = path.join(temporaryDirectory, 'test.sqlite3');
  const writable = new DatabaseSync(databasePath);
  applyMigrations(writable);
  writable.exec(`INSERT INTO data_sources (source_dataset, display_name) VALUES ('fixture', 'Fixture')`);
  writable.close();

  const readOnly = openReadOnlyDatabase(databasePath);
  try {
    assert.equal(readOnly.prepare('SELECT display_name FROM data_sources WHERE source_dataset = ?').get('fixture').display_name, 'Fixture');
    assert.throws(
      () => readOnly.prepare("INSERT INTO data_sources (source_dataset, display_name) VALUES ('blocked', 'Blocked')").run(),
      /readonly|read-only/i,
    );
  } finally {
    readOnly.close();
    fs.rmSync(temporaryDirectory, { recursive: true, force: true });
  }
});

test('exact query normalization mirrors SQLite lower(trim()) semantics', () => {
  const database = new DatabaseSync(':memory:');
  const sqliteLowerTrim = database.prepare('SELECT lower(trim(?)) AS value');
  for (const value of [' ÉCOLE Engineer ', '\tÉCOLE\t', '\u00a0ÉCOLE\u00a0']) {
    assert.equal(normalizeExactLabel(value), sqliteLowerTrim.get(value).value);
  }
  database.close();
});

test('database configuration rejects connection URLs and reports missing local files safely', () => {
  assert.throws(() => resolveDatabasePath('postgres://db.example/jobs'), /local SQLite filesystem path/);
  assert.throws(() => resolveDatabasePath('file:./job_market.sqlite3'), /local SQLite filesystem path/);
  assert.throws(() => resolveDatabasePath(path.join(path.dirname(root), `outside-${process.pid}.sqlite3`)), /inside the project root/);
  const missing = path.join(root, `.jop-missing-${process.pid}-${Date.now()}.sqlite3`);
  assert.throws(
    () => openReadOnlyDatabase(missing),
    (error) => error.code === 'DATABASE_UNAVAILABLE',
  );
});
