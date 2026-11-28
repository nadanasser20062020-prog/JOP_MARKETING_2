import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { DatabaseSync } from 'node:sqlite';
import { createGzip } from 'node:zlib';
import { pipeline } from 'node:stream/promises';
import { config } from '../src/config.js';
import { openReadOnlyDatabase } from '../src/database.js';

const sourcePath = path.resolve(process.env.DATASET_DB_PATH || config.databasePath);
const destinationPath = path.resolve(process.env.DEPLOYMENT_DB_PATH || config.deploymentDatabasePath);
const temporaryPath = `${destinationPath}.tmp`;
const compressedPath = `${destinationPath}.gz`;
const compressedTemporaryPath = `${compressedPath}.tmp`;
const salaryColumns = [
  'salary_annual_min_usd', 'salary_annual_salary_usd', 'salary_annual_max_usd',
  'salary_annual_min_egp', 'salary_annual_salary_egp', 'salary_annual_max_egp',
  'salary_annual_min_sar', 'salary_annual_salary_sar', 'salary_annual_max_sar',
];
fs.mkdirSync(path.dirname(destinationPath), { recursive: true });
for (const candidate of [temporaryPath, `${temporaryPath}-journal`, compressedTemporaryPath]) {
  if (fs.existsSync(candidate)) fs.rmSync(candidate, { force: true });
}

const sourceCheck = openReadOnlyDatabase(sourcePath);
sourceCheck.close();
const output = new DatabaseSync(temporaryPath);
let attached = false;
try {
  output.exec('PRAGMA page_size = 4096; PRAGMA journal_mode = DELETE; PRAGMA synchronous = OFF; PRAGMA foreign_keys = ON;');
  const sourceUri = `${pathToFileURL(sourcePath).href}?mode=ro`;
  output.prepare('ATTACH DATABASE ? AS nada_source').run(sourceUri);
  attached = true;
  output.exec('BEGIN IMMEDIATE');
  output.exec(`
    CREATE TABLE role_dimension (
      role_id INTEGER PRIMARY KEY,
      role_key TEXT NOT NULL UNIQUE,
      title_display TEXT NOT NULL
    );
    CREATE TABLE country_dimension (
      country_id INTEGER PRIMARY KEY,
      country_key TEXT NOT NULL UNIQUE
    );
    CREATE TABLE family_dimension (
      family_id INTEGER PRIMARY KEY,
      family_key TEXT NOT NULL UNIQUE
    );
    CREATE TABLE mode_dimension (
      mode_id INTEGER PRIMARY KEY,
      mode_key TEXT NOT NULL UNIQUE
    );
    CREATE TABLE source_dimension (
      source_id INTEGER PRIMARY KEY,
      source_dataset TEXT NOT NULL UNIQUE
    );
    CREATE TABLE salary_status_dimension (
      status_id INTEGER PRIMARY KEY,
      status_value TEXT NOT NULL UNIQUE
    );
    CREATE TABLE skill_dimension (
      skill_ref INTEGER PRIMARY KEY,
      source_skill_id TEXT NOT NULL UNIQUE,
      canonical_name TEXT NOT NULL,
      category TEXT NOT NULL
    );
    CREATE TABLE skill_alias_dimension (
      alias_normalized TEXT NOT NULL,
      skill_ref INTEGER NOT NULL,
      match_policy TEXT NOT NULL,
      PRIMARY KEY (alias_normalized, skill_ref)
    ) WITHOUT ROWID;
    CREATE TABLE jobs (
      job_id INTEGER PRIMARY KEY,
      role_id INTEGER,
      country_id INTEGER NOT NULL,
      family_id INTEGER,
      mode_id INTEGER NOT NULL,
      source_id INTEGER,
      salary_status_id INTEGER NOT NULL,
      salary_annual_min_usd REAL,
      salary_annual_salary_usd REAL,
      salary_annual_max_usd REAL,
      salary_annual_min_egp REAL,
      salary_annual_salary_egp REAL,
      salary_annual_max_egp REAL,
      salary_annual_min_sar REAL,
      salary_annual_salary_sar REAL,
      salary_annual_max_sar REAL
    );
    CREATE TABLE job_skill_link (
      job_id INTEGER NOT NULL,
      skill_ref INTEGER NOT NULL,
      PRIMARY KEY (job_id, skill_ref)
    ) WITHOUT ROWID;
    CREATE TABLE source_job_map (
      source_record_key TEXT PRIMARY KEY,
      job_id INTEGER NOT NULL UNIQUE
    ) WITHOUT ROWID;
    CREATE TABLE dataset_metadata (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    ) WITHOUT ROWID;

    INSERT INTO role_dimension(role_key, title_display)
    SELECT title_key, MIN(title_clean)
    FROM nada_source.job_cleaning_audit
    WHERE title_key IS NOT NULL AND TRIM(title_key) <> ''
    GROUP BY title_key
    ORDER BY title_key;

    INSERT INTO country_dimension(country_key)
    SELECT COALESCE(NULLIF(TRIM(country_standardized), ''), '[unknown]')
    FROM nada_source.job_cleaning_audit
    GROUP BY COALESCE(NULLIF(TRIM(country_standardized), ''), '[unknown]')
    ORDER BY 1;

    INSERT INTO family_dimension(family_key)
    SELECT COALESCE(NULLIF(TRIM(role_family), ''), '[unlabeled]')
    FROM nada_source.job_cleaning_audit
    GROUP BY COALESCE(NULLIF(TRIM(role_family), ''), '[unlabeled]')
    ORDER BY 1;

    INSERT INTO mode_dimension(mode_key)
    SELECT COALESCE(NULLIF(TRIM(work_mode_standardized), ''), 'unknown_or_unmapped')
    FROM nada_source.job_cleaning_audit
    GROUP BY COALESCE(NULLIF(TRIM(work_mode_standardized), ''), 'unknown_or_unmapped')
    ORDER BY 1;

    INSERT INTO source_dimension(source_dataset)
    SELECT DISTINCT source_dataset FROM nada_source.job_cleaning_audit
    WHERE source_dataset IS NOT NULL
    ORDER BY source_dataset;

    INSERT INTO salary_status_dimension(status_value)
    SELECT COALESCE(NULLIF(TRIM(salary_estimation_status), ''), 'unknown')
    FROM nada_source.job_cleaning_audit
    GROUP BY COALESCE(NULLIF(TRIM(salary_estimation_status), ''), 'unknown')
    ORDER BY 1;

    INSERT INTO skill_dimension(source_skill_id, canonical_name, category)
    SELECT s.skill_id,
           COALESCE(NULLIF(s.canonical_name, ''), CAST(s.skill_id AS TEXT)),
           COALESCE(NULLIF(s.category, ''), 'uncategorized')
    FROM nada_source.skills AS s
    ORDER BY s.skill_id;

    INSERT OR IGNORE INTO skill_dimension(source_skill_id, canonical_name, category)
    SELECT DISTINCT js.skill_id,
           CAST(js.skill_id AS TEXT),
           'uncategorized'
    FROM nada_source.job_skills AS js
    LEFT JOIN skill_dimension AS d ON d.source_skill_id = js.skill_id
    WHERE d.source_skill_id IS NULL;

    INSERT OR IGNORE INTO skill_alias_dimension(alias_normalized, skill_ref, match_policy)
    SELECT a.alias_normalized, d.skill_ref, MAX(a.match_policy)
    FROM nada_source.skill_aliases AS a
    JOIN skill_dimension AS d ON d.source_skill_id = a.skill_id
    WHERE a.alias_normalized IS NOT NULL AND TRIM(a.alias_normalized) <> ''
    GROUP BY a.alias_normalized, d.skill_ref;

    INSERT OR IGNORE INTO skill_alias_dimension(alias_normalized, skill_ref, match_policy)
    SELECT LOWER(TRIM(canonical_name)), skill_ref, 'canonical_name'
    FROM skill_dimension
    WHERE canonical_name IS NOT NULL AND TRIM(canonical_name) <> '';

    INSERT INTO source_job_map(source_record_key, job_id)
    SELECT record_id, ROW_NUMBER() OVER (ORDER BY record_id)
    FROM nada_source.job_cleaning_audit;

    INSERT INTO jobs(
      job_id, role_id, country_id, family_id, mode_id, source_id, salary_status_id,
      salary_annual_min_usd, salary_annual_salary_usd, salary_annual_max_usd,
      salary_annual_min_egp, salary_annual_salary_egp, salary_annual_max_egp,
      salary_annual_min_sar, salary_annual_salary_sar, salary_annual_max_sar
    )
    SELECT m.job_id, r.role_id, c.country_id, f.family_id, w.mode_id, src.source_id, st.status_id,
      ${numericProjection('a.salary_annual_min_usd')},
      ${numericProjection('a.salary_annual_salary_usd')},
      ${numericProjection('a.salary_annual_max_usd')},
      ${numericProjection('a.salary_annual_min_egp')},
      ${numericProjection('a.salary_annual_salary_egp')},
      ${numericProjection('a.salary_annual_max_egp')},
      ${numericProjection('a.salary_annual_min_sar')},
      ${numericProjection('a.salary_annual_salary_sar')},
      ${numericProjection('a.salary_annual_max_sar')}
    FROM nada_source.job_cleaning_audit AS a
    JOIN source_job_map AS m ON m.source_record_key = a.record_id
    LEFT JOIN role_dimension AS r ON r.role_key = a.title_key
    JOIN country_dimension AS c ON c.country_key = COALESCE(NULLIF(TRIM(a.country_standardized), ''), '[unknown]')
    LEFT JOIN family_dimension AS f ON f.family_key = COALESCE(NULLIF(TRIM(a.role_family), ''), '[unlabeled]')
    JOIN mode_dimension AS w ON w.mode_key = COALESCE(NULLIF(TRIM(a.work_mode_standardized), ''), 'unknown_or_unmapped')
    LEFT JOIN source_dimension AS src ON src.source_dataset = a.source_dataset
    JOIN salary_status_dimension AS st ON st.status_value = COALESCE(NULLIF(TRIM(a.salary_estimation_status), ''), 'unknown');

    INSERT INTO job_skill_link(job_id, skill_ref)
    SELECT m.job_id, d.skill_ref
    FROM nada_source.job_skills AS js
    JOIN source_job_map AS m ON m.source_record_key = js.record_id
    JOIN skill_dimension AS d ON d.source_skill_id = js.skill_id;

    DROP TABLE source_job_map;

    CREATE INDEX idx_jobs_role_country ON jobs(role_id, country_id);
    CREATE INDEX idx_jobs_country_role ON jobs(country_id, role_id);
    CREATE INDEX idx_jobs_mode_role ON jobs(mode_id, role_id);
    CREATE INDEX idx_jobs_family ON jobs(family_id);
    CREATE INDEX idx_job_skill_link_skill_job ON job_skill_link(skill_ref, job_id);

    CREATE VIEW job_cleaning_audit AS
    SELECT j.job_id AS record_id,
           src.source_dataset AS source_dataset,
           r.title_display AS title_clean,
           r.role_key AS title_key,
           c.country_key AS country_standardized,
           f.family_key AS role_family,
           w.mode_key AS work_mode_standardized,
           st.status_value AS salary_estimation_status,
           j.salary_annual_min_usd,
           j.salary_annual_salary_usd,
           j.salary_annual_max_usd,
           j.salary_annual_min_egp,
           j.salary_annual_salary_egp,
           j.salary_annual_max_egp,
           j.salary_annual_min_sar,
           j.salary_annual_salary_sar,
           j.salary_annual_max_sar
    FROM jobs AS j
    LEFT JOIN role_dimension AS r ON r.role_id = j.role_id
    LEFT JOIN country_dimension AS c ON c.country_id = j.country_id
    LEFT JOIN family_dimension AS f ON f.family_id = j.family_id
    LEFT JOIN mode_dimension AS w ON w.mode_id = j.mode_id
    LEFT JOIN source_dimension AS src ON src.source_id = j.source_id
    LEFT JOIN salary_status_dimension AS st ON st.status_id = j.salary_status_id;

    CREATE VIEW job_skills AS
    SELECT l.job_id AS record_id, d.source_skill_id AS skill_id
    FROM job_skill_link AS l
    JOIN skill_dimension AS d ON d.skill_ref = l.skill_ref;

    CREATE VIEW skills AS
    SELECT source_skill_id AS skill_id, canonical_name, category
    FROM skill_dimension;

    CREATE VIEW skill_aliases AS
    SELECT a.alias_normalized, d.source_skill_id AS skill_id, a.match_policy
    FROM skill_alias_dimension AS a
    JOIN skill_dimension AS d ON d.skill_ref = a.skill_ref;
  `);
  output.exec('COMMIT');
  output.exec('ANALYZE main;');

  const sourceCounts = output.prepare(`
    SELECT (SELECT COUNT(*) FROM nada_source.jobs) AS jobs,
           (SELECT COUNT(*) FROM nada_source.job_cleaning_audit) AS audit_rows,
           (SELECT COUNT(*) FROM nada_source.job_skills) AS links,
           (SELECT COUNT(*) FROM nada_source.skills) AS skills`).get();
  const compactCounts = output.prepare(`
    SELECT (SELECT COUNT(*) FROM jobs) AS jobs,
           (SELECT COUNT(*) FROM job_cleaning_audit) AS audit_rows,
           (SELECT COUNT(*) FROM job_skills) AS links,
           (SELECT COUNT(*) FROM skills) AS skills`).get();
  const sourceSalarySignature = output.prepare(`
    SELECT ${salarySignatureProjection('a')}
    FROM nada_source.job_cleaning_audit AS a`).get();
  const compactSalarySignature = output.prepare(`
    SELECT ${salarySignatureProjection('a')}
    FROM job_cleaning_audit AS a`).get();
  const sourceSalaryStatuses = output.prepare(`
    SELECT COALESCE(NULLIF(TRIM(salary_estimation_status), ''), 'unknown') AS status,
           COUNT(*) AS count
    FROM nada_source.job_cleaning_audit
    GROUP BY 1 ORDER BY 1`).all().map((row) => ({ status: row.status, count: Number(row.count) }));
  const compactSalaryStatuses = output.prepare(`
    SELECT COALESCE(NULLIF(TRIM(salary_estimation_status), ''), 'unknown') AS status,
           COUNT(*) AS count
    FROM job_cleaning_audit
    GROUP BY 1 ORDER BY 1`).all().map((row) => ({ status: row.status, count: Number(row.count) }));
  const salaryCounts = output.prepare(`
    SELECT COUNT(*) AS rows_with_usd_center FROM job_cleaning_audit
    WHERE salary_annual_salary_usd IS NOT NULL`).get();
  const result = output.prepare('PRAGMA quick_check(1)').get();
  const quickCheck = result?.quick_check ?? Object.values(result ?? {})[0];
  const tableCountsReconciled = Object.keys(sourceCounts).every((key) => Number(sourceCounts[key]) === Number(compactCounts[key]));
  const salaryReconciled = salaryColumns.every((column) => {
    const countKey = `${column}_count`;
    const sumKey = `${column}_sum`;
    return Number(sourceSalarySignature[countKey] ?? 0) === Number(compactSalarySignature[countKey] ?? 0)
      && nearlyEqual(sourceSalarySignature[sumKey], compactSalarySignature[sumKey]);
  }) && JSON.stringify(sourceSalaryStatuses) === JSON.stringify(compactSalaryStatuses);
  const reconciled = tableCountsReconciled && salaryReconciled;
  output.prepare('INSERT INTO dataset_metadata(key,value) VALUES (?,?)').run('source_rows', String(sourceCounts.jobs));
  output.prepare('INSERT INTO dataset_metadata(key,value) VALUES (?,?)').run('source_skill_links', String(sourceCounts.links));
  output.prepare('INSERT INTO dataset_metadata(key,value) VALUES (?,?)').run('salary_rows_with_annual_usd', String(salaryCounts.rows_with_usd_center));
  output.prepare('INSERT INTO dataset_metadata(key,value) VALUES (?,?)').run('generated_from', 'NADA 11-part jobs_cleaned_audited.sqlite3.gz reconstruction');
  output.prepare('INSERT INTO dataset_metadata(key,value) VALUES (?,?)').run('generated_at_utc', new Date().toISOString());
  if (quickCheck !== 'ok' || !reconciled) {
    throw new Error(`Deployment database validation failed: quick_check=${quickCheck}; tableCountsReconciled=${tableCountsReconciled}; salaryReconciled=${salaryReconciled}; source=${JSON.stringify(sourceCounts)}; compact=${JSON.stringify(compactCounts)}`);
  }
  output.exec('DETACH DATABASE nada_source');
  attached = false;
  output.close();
  fs.renameSync(temporaryPath, destinationPath);
  await pipeline(
    fs.createReadStream(destinationPath),
    createGzip({ level: 9 }),
    fs.createWriteStream(compressedTemporaryPath, { flags: 'wx' }),
  );
  fs.renameSync(compressedTemporaryPath, compressedPath);
  const outputBytes = fs.statSync(destinationPath).size;
  const compressedBytes = fs.statSync(compressedPath).size;
  console.log(JSON.stringify({
    destinationPath,
    compressedPath,
    sourcePath,
    quickCheck,
    reconciled,
    tableCountsReconciled,
    salaryReconciled,
    sourceSalaryStatusCounts: sourceSalaryStatuses,
    compactSalaryStatusCounts: compactSalaryStatuses,
    sourceCounts: Object.fromEntries(Object.entries(sourceCounts).map(([key, value]) => [key, Number(value)])),
    compactCounts: Object.fromEntries(Object.entries(compactCounts).map(([key, value]) => [key, Number(value)])),
    salaryRowsWithAnnualUsd: Number(salaryCounts.rows_with_usd_center),
    outputBytes,
    compressedBytes,
    vercelFunctionBundleBudgetBytes: 250 * 1024 * 1024,
    withinVercelUncompressedBundleTarget: compressedBytes < 200 * 1024 * 1024,
  }, null, 2));
  if (compressedBytes >= 200 * 1024 * 1024) process.exitCode = 2;
} catch (error) {
  try { output.exec('ROLLBACK'); } catch { /* no active transaction */ }
  if (attached) {
    try { output.exec('DETACH DATABASE nada_source'); } catch { /* connection is closing */ }
  }
  try { output.close(); } catch { /* already closed after successful database validation */ }
  for (const candidate of [temporaryPath, `${temporaryPath}-journal`, compressedTemporaryPath]) {
    if (fs.existsSync(candidate)) fs.rmSync(candidate, { force: true });
  }
  throw error;
}

function numericProjection(expression) {
  return `CASE WHEN ${expression} IS NOT NULL AND TRIM(CAST(${expression} AS TEXT)) <> '' THEN CAST(${expression} AS REAL) ELSE NULL END`;
}

function salarySignatureProjection(alias) {
  return salaryColumns.flatMap((column) => [
    `COUNT(CASE WHEN ${alias}.${column} IS NOT NULL AND TRIM(CAST(${alias}.${column} AS TEXT)) <> '' THEN 1 END) AS ${column}_count`,
    `SUM(CAST(${alias}.${column} AS REAL)) AS ${column}_sum`,
  ]).join(',\n');
}

function nearlyEqual(left, right) {
  const first = Number(left ?? 0);
  const second = Number(right ?? 0);
  return Math.abs(first - second) <= Math.max(1, Math.abs(first), Math.abs(second)) * 1e-12;
}
