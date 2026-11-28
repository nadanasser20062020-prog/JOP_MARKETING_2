import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';

const AUDIT_FIELDS = [
  'record_id', 'source_dataset', 'title_clean', 'title_key', 'country_standardized', 'role_family',
  'work_mode_standardized', 'salary_estimation_status',
  'salary_annual_min_usd', 'salary_annual_salary_usd', 'salary_annual_max_usd',
  'salary_annual_min_egp', 'salary_annual_salary_egp', 'salary_annual_max_egp',
  'salary_annual_min_sar', 'salary_annual_salary_sar', 'salary_annual_max_sar', 'category_raw',
];

const FIXTURE_JOBS = [
  { id: 'job-1', title: 'Data Engineer', key: 'data engineer', country: 'Egypt', family: 'data_engineering', mode: 'remote', status: 'Estimated', usd: [120000, 135000, 150000], egp: [6000000, 6750000, 7500000], sar: [450000, 506250, 562500], category: 'Data & AI', skills: ['py', 'sql'] },
  { id: 'job-2', title: 'Data Engineer', key: 'data engineer', country: 'Egypt', family: 'data_engineering', mode: 'not_remote_explicit', status: 'Estimated', usd: [90000, 100000, 110000], egp: [4500000, 5000000, 5500000], sar: [337500, 375000, 412500], category: 'Data & AI', skills: ['sql', 'spark'] },
  { id: 'job-3', title: 'Data Engineer', key: 'data engineer', country: 'United States', family: 'data_engineering', mode: 'remote', status: 'Actual', usd: [100000, 100000, 100000], egp: [5000000, 5000000, 5000000], sar: [375000, 375000, 375000], category: 'Data & AI', skills: ['py', 'aws'] },
  { id: 'job-4', title: 'Software Engineer', key: 'software engineer', country: 'Egypt', family: 'software_engineering', mode: 'not_remote_explicit', status: 'Estimated', usd: [80000, 90000, 100000], egp: [4000000, 4500000, 5000000], sar: [300000, 337500, 375000], category: 'Software', skills: ['js', 'sql'] },
  { id: 'job-5', title: 'Software Engineer', key: 'software engineer', country: '', family: 'software_engineering', mode: 'unknown_or_unmapped', status: 'Not disclosed', usd: [null, null, null], egp: [null, null, null], sar: [null, null, null], category: '', skills: ['js'] },
];

const SKILLS = [
  { id: 'py', name: 'Python', category: 'Programming' },
  { id: 'sql', name: 'SQL', category: 'Data' },
  { id: 'spark', name: 'Apache Spark', category: 'Data' },
  { id: 'aws', name: 'AWS', category: 'Cloud' },
  { id: 'js', name: 'JavaScript', category: 'Programming' },
];

export function createFixtureDatabase() {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'jop-backend-v2-'));
  const databasePath = path.join(directory, 'fixture.sqlite3');
  const db = new DatabaseSync(databasePath);
  db.exec(`
    CREATE TABLE job_cleaning_audit (
      record_id TEXT PRIMARY KEY,
      source_dataset TEXT NOT NULL,
      title_clean TEXT,
      title_key TEXT,
      country_standardized TEXT,
      role_family TEXT,
      work_mode_standardized TEXT,
      salary_estimation_status TEXT,
      salary_annual_min_usd REAL,
      salary_annual_salary_usd REAL,
      salary_annual_max_usd REAL,
      salary_annual_min_egp REAL,
      salary_annual_salary_egp REAL,
      salary_annual_max_egp REAL,
      salary_annual_min_sar REAL,
      salary_annual_salary_sar REAL,
      salary_annual_max_sar REAL,
      category_raw TEXT
    );
    CREATE INDEX idx_job_cleaning_audit_title_key ON job_cleaning_audit(title_key);
    CREATE INDEX idx_job_cleaning_audit_country ON job_cleaning_audit(country_standardized);
    CREATE TABLE job_skills (
      record_id TEXT NOT NULL,
      skill_id TEXT NOT NULL,
      skill_normalized TEXT NOT NULL,
      skill_raw TEXT NOT NULL,
      skill_category TEXT NOT NULL,
      PRIMARY KEY(record_id, skill_id)
    ) WITHOUT ROWID;
    CREATE INDEX idx_job_skills_skill_id ON job_skills(skill_id, record_id);
    CREATE TABLE skills (skill_id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL, category TEXT NOT NULL);
    CREATE TABLE skill_aliases (alias_normalized TEXT NOT NULL, skill_id TEXT NOT NULL, match_policy TEXT NOT NULL DEFAULT 'exact_only', PRIMARY KEY(alias_normalized, skill_id));
  `);

  const insertAudit = db.prepare(`INSERT INTO job_cleaning_audit (${AUDIT_FIELDS.join(',')}) VALUES (${AUDIT_FIELDS.map(() => '?').join(',')})`);
  const skillNames = new Map(SKILLS.map((skill) => [skill.id, skill]));
  const insertSkill = db.prepare('INSERT INTO skills(skill_id, canonical_name, category) VALUES (?, ?, ?)');
  for (const skill of SKILLS) insertSkill.run(skill.id, skill.name, skill.category);
  const insertAlias = db.prepare('INSERT INTO skill_aliases(alias_normalized, skill_id) VALUES (?, ?)');
  for (const [alias, id] of [['python', 'py'], ['py', 'py'], ['sql', 'sql'], ['spark', 'spark'], ['aws', 'aws'], ['javascript', 'js'], ['js', 'js'], ['common', 'py'], ['common', 'sql']]) insertAlias.run(alias, id);
  const insertJobSkill = db.prepare('INSERT INTO job_skills(record_id, skill_id, skill_normalized, skill_raw, skill_category) VALUES (?, ?, ?, ?, ?)');

  db.exec('BEGIN');
  try {
    for (const job of FIXTURE_JOBS) {
      const values = [
        job.id, 'fixture', job.title, job.key, job.country, job.family, job.mode, job.status,
        ...job.usd, ...job.egp, ...job.sar, job.category,
      ];
      insertAudit.run(...values);
      for (const skillKey of job.skills) {
        const skill = skillNames.get(skillKey);
        insertJobSkill.run(job.id, skill.id, skill.name.toLowerCase(), skill.name, skill.category);
      }
    }
    db.exec('COMMIT');
  } catch (error) {
    db.exec('ROLLBACK');
    db.close();
    fs.rmSync(directory, { recursive: true, force: true });
    throw error;
  }
  db.close();
  return {
    databasePath,
    cleanup() { fs.rmSync(directory, { recursive: true, force: true }); },
  };
}

export { FIXTURE_JOBS };
