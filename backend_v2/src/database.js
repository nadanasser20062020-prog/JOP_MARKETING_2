import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { gunzipSync } from 'node:zlib';

const SQLITE_HEADER = Buffer.from('SQLite format 3\u0000');
const MAX_DEPLOYMENT_DATABASE_BYTES = 512 * 1024 * 1024;

const REQUIRED_COLUMNS = Object.freeze({
  job_cleaning_audit: [
    'record_id', 'source_dataset', 'title_clean', 'title_key', 'country_standardized', 'role_family',
    'work_mode_standardized', 'salary_estimation_status', 'salary_annual_min_usd',
    'salary_annual_salary_usd', 'salary_annual_max_usd', 'salary_annual_min_egp',
    'salary_annual_salary_egp', 'salary_annual_max_egp', 'salary_annual_min_sar',
    'salary_annual_salary_sar', 'salary_annual_max_sar',
  ],
  job_skills: ['record_id', 'skill_id'],
  skills: ['skill_id', 'canonical_name', 'category'],
  skill_aliases: ['alias_normalized', 'skill_id'],
});

export class SqliteDatabase {
  #connection;
  #statements = new Map();

  constructor(connection) {
    this.#connection = connection;
  }

  #statement(sql) {
    let statement = this.#statements.get(sql);
    if (!statement) {
      statement = this.#connection.prepare(sql);
      this.#statements.set(sql, statement);
    }
    return statement;
  }

  get(sql, ...parameters) {
    return this.#statement(sql).get(...parameters) ?? null;
  }

  all(sql, ...parameters) {
    return this.#statement(sql).all(...parameters);
  }

  iterate(sql, ...parameters) {
    return this.#statement(sql).iterate(...parameters);
  }

  close() {
    this.#statements.clear();
    this.#connection.close();
  }

  rawConnectionForPreflight() {
    return this.#connection;
  }
}

function materializeDatabasePath(databasePath) {
  if (!databasePath.toLowerCase().endsWith('.gz')) return databasePath;

  const sourceStats = fs.statSync(databasePath);
  const cacheDirectory = path.join(os.tmpdir(), 'jop-marketing-backend-v2');
  const identity = `${sourceStats.size}-${Math.trunc(sourceStats.mtimeMs)}`;
  const materializedPath = path.join(
    cacheDirectory,
    `${path.basename(databasePath, '.gz')}-${identity}.sqlite3`,
  );
  if (fs.existsSync(materializedPath) && fs.statSync(materializedPath).size > 0) return materializedPath;

  fs.mkdirSync(cacheDirectory, { recursive: true });
  const temporaryPath = `${materializedPath}.${process.pid}.tmp`;
  try {
    const sqliteBytes = gunzipSync(fs.readFileSync(databasePath), {
      maxOutputLength: MAX_DEPLOYMENT_DATABASE_BYTES,
    });
    if (!sqliteBytes.subarray(0, SQLITE_HEADER.length).equals(SQLITE_HEADER)) {
      throw new Error('The decompressed file does not have a SQLite 3 header.');
    }
    fs.writeFileSync(temporaryPath, sqliteBytes, { flag: 'w', mode: 0o600 });
    fs.renameSync(temporaryPath, materializedPath);
    return materializedPath;
  } catch (cause) {
    fs.rmSync(temporaryPath, { force: true });
    const error = new Error(`Could not materialize the gzip-compressed SQLite database at ${databasePath}.`, { cause });
    error.code = 'DATABASE_DECOMPRESS_FAILED';
    throw error;
  }
}

export function openReadOnlyDatabase(databasePath) {
  if (!fs.existsSync(databasePath)) {
    const error = new Error(`SQLite database not found at ${databasePath}`);
    error.code = 'DATABASE_NOT_FOUND';
    throw error;
  }
  const sourceStats = fs.statSync(databasePath);
  if (!sourceStats.isFile() || sourceStats.size === 0) {
    const error = new Error(`SQLite database is empty or not a regular file: ${databasePath}`);
    error.code = 'DATABASE_INVALID_FILE';
    throw error;
  }

  const resolvedDatabasePath = materializeDatabasePath(databasePath);
  const stats = fs.statSync(resolvedDatabasePath);
  if (!stats.isFile() || stats.size === 0) {
    const error = new Error(`SQLite database is empty or not a regular file: ${resolvedDatabasePath}`);
    error.code = 'DATABASE_INVALID_FILE';
    throw error;
  }

  let connection;
  try {
    connection = new DatabaseSync(resolvedDatabasePath, { readOnly: true, timeout: 5_000 });
    connection.exec('PRAGMA query_only = ON; PRAGMA busy_timeout = 5000;');
    validateSchema(connection);
    return new SqliteDatabase(connection);
  } catch (error) {
    connection?.close();
    error.code ||= 'DATABASE_OPEN_FAILED';
    throw error;
  }
}

export function validateSchema(connection) {
  const tableRows = connection.prepare(
    "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'",
  ).all();
  const tableNames = new Set(tableRows.map((row) => row.name));
  const missingTables = Object.keys(REQUIRED_COLUMNS).filter((name) => !tableNames.has(name));
  if (missingTables.length) {
    const error = new Error(`NADA database is missing required tables: ${missingTables.join(', ')}`);
    error.code = 'DATABASE_SCHEMA_MISMATCH';
    throw error;
  }

  const missing = [];
  for (const [table, requiredColumns] of Object.entries(REQUIRED_COLUMNS)) {
    const actual = new Set(connection.prepare(`PRAGMA table_info("${table}")`).all().map((row) => row.name));
    for (const column of requiredColumns) {
      if (!actual.has(column)) missing.push(`${table}.${column}`);
    }
  }
  if (missing.length) {
    const error = new Error(`NADA database schema is missing required columns: ${missing.join(', ')}`);
    error.code = 'DATABASE_SCHEMA_MISMATCH';
    throw error;
  }

  return { tables: tableNames.size, requiredTables: Object.keys(REQUIRED_COLUMNS).length };
}
