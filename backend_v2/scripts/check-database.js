import { config } from '../src/config.js';
import { openReadOnlyDatabase } from '../src/database.js';

const databasePath = process.env.DATASET_DB_PATH || config.databasePath;
const db = openReadOnlyDatabase(databasePath);
try {
  const connection = db.rawConnectionForPreflight();
  const integrity = connection.prepare('PRAGMA quick_check(1)').get();
  const quickCheck = integrity?.quick_check ?? Object.values(integrity ?? {})[0];
  const tables = connection.prepare("SELECT type, COUNT(*) AS count FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' GROUP BY type ORDER BY type").all();
  const counts = {
    jobs: db.get('SELECT COUNT(*) AS count FROM jobs')?.count ?? null,
    auditRows: db.get('SELECT COUNT(*) AS count FROM job_cleaning_audit')?.count ?? null,
    jobSkillLinks: db.get('SELECT COUNT(*) AS count FROM job_skills')?.count ?? null,
    catalogSkills: db.get('SELECT COUNT(*) AS count FROM skills')?.count ?? null,
  };
  console.log(JSON.stringify({
    databasePath,
    readOnly: true,
    quickCheck,
    tables,
    counts,
    source: 'NADA 11-part SQLite reconstruction',
  }, null, 2));
  if (quickCheck !== 'ok') process.exitCode = 1;
} finally {
  db.close();
}
