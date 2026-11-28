import { normalizeKey } from './normalize.js';

const ARAB_COUNTRIES = Object.freeze([
  'algeria', 'bahrain', 'comoros', 'djibouti', 'egypt', 'iraq', 'jordan', 'kuwait',
  'lebanon', 'libya', 'mauritania', 'morocco', 'oman', 'palestine', 'qatar',
  'saudi arabia', 'somalia', 'sudan', 'syria', 'tunisia', 'united arab emirates', 'yemen',
  'uae', 'u.a.e.', 'ksa', 'kingdom of saudi arabia',
]);
const NON_COUNTRY_SCOPES = Object.freeze([
  '', 'worldwide', 'remote', 'remote (anywhere)', 'anywhere', 'unknown', 'not stated', 'unspecified',
]);

const SALARY_FIELDS = Object.freeze({
  USD: { minimum: 'salary_annual_min_usd', center: 'salary_annual_salary_usd', maximum: 'salary_annual_max_usd' },
  EGP: { minimum: 'salary_annual_min_egp', center: 'salary_annual_salary_egp', maximum: 'salary_annual_max_egp' },
  SAR: { minimum: 'salary_annual_min_sar', center: 'salary_annual_salary_sar', maximum: 'salary_annual_max_sar' },
});

function finiteCount(row, key) {
  return Number(row?.[key] ?? 0);
}

function marketSql() {
  const arab = ARAB_COUNTRIES.map((country) => `'${country.replaceAll("'", "''")}'`).join(', ');
  const nonCountry = NON_COUNTRY_SCOPES.map((country) => `'${country.replaceAll("'", "''")}'`).join(', ');
  return `CASE
    WHEN LOWER(TRIM(COALESCE(country_standardized, ''))) IN (${arab}) THEN 'arab'
    WHEN LOWER(TRIM(COALESCE(country_standardized, ''))) IN (${nonCountry}) THEN 'unknown'
    ELSE 'international'
  END`;
}

function salaryProjectionSql() {
  const expressions = [];
  for (const [currency, fields] of Object.entries(SALARY_FIELDS)) {
    const min = `CAST("${fields.minimum}" AS REAL)`;
    const center = `CAST("${fields.center}" AS REAL)`;
    const max = `CAST("${fields.maximum}" AS REAL)`;
    const midpoint = `CASE WHEN ${center} > 0 THEN ${center} WHEN ${min} > 0 AND ${max} > 0 THEN (${min} + ${max}) / 2.0 ELSE NULL END`;
    expressions.push(`
      SUM(CASE WHEN ${midpoint} > 0 THEN 1 ELSE 0 END) AS ${currency.toLowerCase()}_salary_records,
      AVG(CASE WHEN ${midpoint} > 0 THEN ${midpoint} END) AS ${currency.toLowerCase()}_mean_annual,
      MIN(CASE WHEN ${min} > 0 THEN ${min} WHEN ${center} > 0 THEN ${center} END) AS ${currency.toLowerCase()}_range_min,
      MAX(CASE WHEN ${max} > 0 THEN ${max} WHEN ${center} > 0 THEN ${center} END) AS ${currency.toLowerCase()}_range_max,
      AVG(CASE WHEN ${min} > 0 THEN ${min} WHEN ${center} > 0 THEN ${center} END) AS ${currency.toLowerCase()}_mean_lower_bound,
      AVG(CASE WHEN ${max} > 0 THEN ${max} WHEN ${center} > 0 THEN ${center} END) AS ${currency.toLowerCase()}_mean_upper_bound,
      SUM(CASE WHEN ${midpoint} > 0 AND LOWER(TRIM(salary_estimation_status)) = 'estimated' THEN 1 ELSE 0 END) AS ${currency.toLowerCase()}_estimated_records,
      SUM(CASE WHEN ${midpoint} > 0 AND LOWER(TRIM(salary_estimation_status)) = 'actual' THEN 1 ELSE 0 END) AS ${currency.toLowerCase()}_actual_records,
      SUM(CASE WHEN ${midpoint} > 0 AND LOWER(TRIM(salary_estimation_status)) = 'unverified' THEN 1 ELSE 0 END) AS ${currency.toLowerCase()}_unverified_records`);
  }
  return expressions.join(',');
}

export class AnalyticsRepository {
  constructor(database) {
    this.database = database;
    this.marketExpression = marketSql();
  }

  getOverview() {
    const totals = this.database.get(`
      SELECT COUNT(*) AS total_jobs,
             COUNT(DISTINCT NULLIF(title_key, '')) AS distinct_roles,
             COUNT(DISTINCT NULLIF(country_standardized, '')) AS distinct_countries,
             COUNT(DISTINCT source_dataset) AS source_count
      FROM job_cleaning_audit`);
    const topRole = this.database.get(`
      SELECT title_key, MIN(title_clean) AS title, COUNT(*) AS ad_count
      FROM job_cleaning_audit
      WHERE title_key IS NOT NULL AND title_key <> ''
      GROUP BY title_key
      ORDER BY ad_count DESC, title_key ASC
      LIMIT 1`);
    const workModes = this.getWorkModes();
    const salaries = this.database.get(`
      SELECT ${salaryProjectionSql()}
      FROM job_cleaning_audit`);
    return {
      totalJobs: finiteCount(totals, 'total_jobs'),
      distinctRoles: finiteCount(totals, 'distinct_roles'),
      distinctCountries: finiteCount(totals, 'distinct_countries'),
      sourceCount: finiteCount(totals, 'source_count'),
      topRole: topRole ? {
        roleKey: topRole.title_key,
        title: topRole.title,
        advertisementCount: finiteCount(topRole, 'ad_count'),
      } : null,
      workModes,
      salaryCoverage: Object.fromEntries(Object.keys(SALARY_FIELDS).map((currency) => [
        currency,
        finiteCount(salaries, `${currency.toLowerCase()}_salary_records`),
      ])),
    };
  }

  searchRoles(query, limit) {
    const normalized = normalizeKey(query);
    if (!normalized) {
      return this.database.all(`
        SELECT title_key AS role_key, MIN(title_clean) AS title, COUNT(*) AS advertisement_count
        FROM job_cleaning_audit
        WHERE title_key IS NOT NULL AND title_key <> ''
        GROUP BY title_key
        ORDER BY advertisement_count DESC, title_key ASC
        LIMIT ?`, limit);
    }
    return this.database.all(`
      SELECT title_key AS role_key, MIN(title_clean) AS title, COUNT(*) AS advertisement_count
      FROM job_cleaning_audit
      WHERE title_key LIKE ? ESCAPE '\\'
      GROUP BY title_key
      ORDER BY advertisement_count DESC, title_key ASC
      LIMIT ?`, `${escapeLike(normalized)}%`, limit);
  }

  getRole(roleKey) {
    return this.database.get(`
      SELECT title_key AS role_key,
             MIN(title_clean) AS title,
             COUNT(*) AS advertisement_count,
             COUNT(DISTINCT source_dataset) AS source_count,
             SUM(CASE WHEN role_family IS NOT NULL AND TRIM(role_family) <> '' THEN 1 ELSE 0 END) AS labeled_advertisements
      FROM job_cleaning_audit
      WHERE title_key = ?
      GROUP BY title_key`, normalizeKey(roleKey));
  }

  getCountryTotals() {
    return this.database.all(`
      SELECT COALESCE(NULLIF(TRIM(country_standardized), ''), '[unknown]') AS country_key,
             COUNT(*) AS total_advertisements
      FROM job_cleaning_audit
      GROUP BY COALESCE(NULLIF(TRIM(country_standardized), ''), '[unknown]')`);
  }

  getRoleCountries(roleKey) {
    return this.database.all(`
      SELECT COALESCE(NULLIF(TRIM(country_standardized), ''), '[unknown]') AS country_key,
             COUNT(*) AS role_advertisements
      FROM job_cleaning_audit
      WHERE title_key = ?
      GROUP BY COALESCE(NULLIF(TRIM(country_standardized), ''), '[unknown]')
      ORDER BY role_advertisements DESC, country_key ASC`, normalizeKey(roleKey));
  }

  getCountryDistribution(limit = 25) {
    return this.database.all(`
      SELECT COALESCE(NULLIF(TRIM(country_standardized), ''), '[unknown]') AS country_key,
             COUNT(*) AS advertisement_count
      FROM job_cleaning_audit
      GROUP BY COALESCE(NULLIF(TRIM(country_standardized), ''), '[unknown]')
      ORDER BY advertisement_count DESC, country_key ASC
      LIMIT ?`, limit);
  }

  getRoleSkills(roleKey, limit = 50) {
    return this.database.all(`
      SELECT js.skill_id,
             COALESCE(NULLIF(MAX(s.canonical_name), ''), CAST(js.skill_id AS TEXT)) AS skill,
             COALESCE(MAX(s.category), 'uncategorized') AS category,
             COUNT(*) AS advertisement_count
      FROM job_cleaning_audit AS a
      JOIN job_skills AS js ON js.record_id = a.record_id
      LEFT JOIN skills AS s ON s.skill_id = js.skill_id
      WHERE a.title_key = ?
      GROUP BY js.skill_id
      ORDER BY advertisement_count DESC, skill COLLATE NOCASE ASC
      LIMIT ?`, normalizeKey(roleKey), limit);
  }

  getGlobalSkills(limit = 50) {
    return this.database.all(`
      SELECT js.skill_id,
             COALESCE(NULLIF(MAX(s.canonical_name), ''), CAST(js.skill_id AS TEXT)) AS skill,
             COALESCE(MAX(s.category), 'uncategorized') AS category,
             COUNT(*) AS advertisement_count
      FROM job_skills AS js
      LEFT JOIN skills AS s ON s.skill_id = js.skill_id
      GROUP BY js.skill_id
      ORDER BY advertisement_count DESC, skill COLLATE NOCASE ASC
      LIMIT ?`, limit);
  }

  getRoleSkillCombinations(roleKey, topSkillIds, limit = 30) {
    const ids = [...new Set(topSkillIds)].filter((id) => typeof id === 'string' && id.length > 0);
    if (ids.length < 2) return [];
    const placeholders = ids.map(() => '?').join(', ');
    return this.database.all(`
      SELECT first_skill.skill_id AS first_skill_id,
             COALESCE(NULLIF(MAX(first_catalog.canonical_name), ''), CAST(first_skill.skill_id AS TEXT)) AS first_skill,
             second_skill.skill_id AS second_skill_id,
             COALESCE(NULLIF(MAX(second_catalog.canonical_name), ''), CAST(second_skill.skill_id AS TEXT)) AS second_skill,
             COUNT(*) AS cooccurrence_count
      FROM job_cleaning_audit AS a
      JOIN job_skills AS first_skill ON first_skill.record_id = a.record_id
      JOIN job_skills AS second_skill
        ON second_skill.record_id = first_skill.record_id
       AND second_skill.skill_id > first_skill.skill_id
      LEFT JOIN skills AS first_catalog ON first_catalog.skill_id = first_skill.skill_id
      LEFT JOIN skills AS second_catalog ON second_catalog.skill_id = second_skill.skill_id
      WHERE a.title_key = ?
        AND first_skill.skill_id IN (${placeholders})
        AND second_skill.skill_id IN (${placeholders})
      GROUP BY first_skill.skill_id, second_skill.skill_id
      ORDER BY cooccurrence_count DESC, first_skill ASC, second_skill ASC
      LIMIT ?`, normalizeKey(roleKey), ...ids, ...ids, limit);
  }

  getWorkModes(roleKey = null) {
    const rows = roleKey
      ? this.database.all(`
          SELECT COALESCE(NULLIF(TRIM(work_mode_standardized), ''), 'unknown_or_unmapped') AS mode,
                 COUNT(*) AS advertisement_count
          FROM job_cleaning_audit
          WHERE title_key = ?
          GROUP BY COALESCE(NULLIF(TRIM(work_mode_standardized), ''), 'unknown_or_unmapped')
          ORDER BY advertisement_count DESC, mode ASC`, normalizeKey(roleKey))
      : this.database.all(`
          SELECT COALESCE(NULLIF(TRIM(work_mode_standardized), ''), 'unknown_or_unmapped') AS mode,
                 COUNT(*) AS advertisement_count
          FROM job_cleaning_audit
          GROUP BY COALESCE(NULLIF(TRIM(work_mode_standardized), ''), 'unknown_or_unmapped')
          ORDER BY advertisement_count DESC, mode ASC`);
    return rows;
  }

  getRoleSalary(roleKey) {
    return this.database.all(`
      SELECT COALESCE(NULLIF(TRIM(country_standardized), ''), '[unknown]') AS country_key,
             COUNT(*) AS role_advertisements,
             ${salaryProjectionSql()}
      FROM job_cleaning_audit
      WHERE title_key = ?
      GROUP BY COALESCE(NULLIF(TRIM(country_standardized), ''), '[unknown]')
      ORDER BY role_advertisements DESC, country_key ASC`, normalizeKey(roleKey));
  }

  getRoleFamilyDistribution(roleKey) {
    return this.database.all(`
      SELECT COALESCE(NULLIF(TRIM(role_family), ''), '[unlabeled]') AS family,
             COUNT(*) AS advertisement_count
      FROM job_cleaning_audit
      WHERE title_key = ?
      GROUP BY COALESCE(NULLIF(TRIM(role_family), ''), '[unlabeled]')
      ORDER BY advertisement_count DESC, family ASC`, normalizeKey(roleKey));
  }

  getMarketCounts() {
    const expression = this.marketExpression;
    return this.database.all(`
      WITH classified AS (
        SELECT ${expression} AS market, title_key
        FROM job_cleaning_audit
      )
      SELECT market,
             COUNT(*) AS advertisement_count,
             COUNT(DISTINCT NULLIF(title_key, '')) AS distinct_roles
      FROM classified
      GROUP BY market
      ORDER BY CASE market WHEN 'arab' THEN 1 WHEN 'international' THEN 2 ELSE 3 END`);
  }

  getMarketSalary() {
    const expression = this.marketExpression;
    return this.database.all(`
      WITH classified AS (
        SELECT ${expression} AS market, salary_estimation_status,
               salary_annual_min_usd, salary_annual_salary_usd, salary_annual_max_usd,
               salary_annual_min_egp, salary_annual_salary_egp, salary_annual_max_egp,
               salary_annual_min_sar, salary_annual_salary_sar, salary_annual_max_sar
        FROM job_cleaning_audit
      )
      SELECT market, ${salaryProjectionSql()}
      FROM classified
      GROUP BY market
      ORDER BY CASE market WHEN 'arab' THEN 1 WHEN 'international' THEN 2 ELSE 3 END`);
  }

  getMarketSkills(limit = 20) {
    const expression = this.marketExpression;
    return this.database.all(`
      WITH classified AS (
        SELECT record_id, ${expression} AS market
        FROM job_cleaning_audit
      ), ranked AS (
        SELECT c.market, js.skill_id,
               COALESCE(NULLIF(MAX(s.canonical_name), ''), CAST(js.skill_id AS TEXT)) AS skill,
               COUNT(*) AS advertisement_count,
               ROW_NUMBER() OVER (
                 PARTITION BY c.market
                 ORDER BY COUNT(*) DESC, MAX(s.canonical_name) COLLATE NOCASE ASC
               ) AS rank_in_market
        FROM classified AS c
        JOIN job_skills AS js ON js.record_id = c.record_id
        LEFT JOIN skills AS s ON s.skill_id = js.skill_id
        GROUP BY c.market, js.skill_id
      )
      SELECT market, skill_id, skill, advertisement_count
      FROM ranked
      WHERE rank_in_market <= ?
      ORDER BY CASE market WHEN 'arab' THEN 1 WHEN 'international' THEN 2 ELSE 3 END,
               advertisement_count DESC, skill COLLATE NOCASE ASC`, limit);
  }

  getMarketTopRoles(limit = 10) {
    const expression = this.marketExpression;
    return this.database.all(`
      WITH classified AS (
        SELECT ${expression} AS market, title_key, title_clean
        FROM job_cleaning_audit
        WHERE title_key IS NOT NULL AND title_key <> ''
      ), ranked AS (
        SELECT market, title_key,
               MIN(title_clean) AS title,
               COUNT(*) AS advertisement_count,
               ROW_NUMBER() OVER (
                 PARTITION BY market
                 ORDER BY COUNT(*) DESC, title_key ASC
               ) AS rank_in_market
        FROM classified
        GROUP BY market, title_key
      )
      SELECT market, title_key AS role_key, title, advertisement_count
      FROM ranked
      WHERE rank_in_market <= ?
      ORDER BY CASE market WHEN 'arab' THEN 1 WHEN 'international' THEN 2 ELSE 3 END,
               advertisement_count DESC, title_key ASC`, limit);
  }

  getRoleSalarySample(roleKey, countryKey, currency) {
    const fields = SALARY_FIELDS[currency];
    if (!fields) return null;
    const min = `CAST("${fields.minimum}" AS REAL)`;
    const center = `CAST("${fields.center}" AS REAL)`;
    const max = `CAST("${fields.maximum}" AS REAL)`;
    const midpoint = `CASE WHEN ${center} > 0 THEN ${center} WHEN ${min} > 0 AND ${max} > 0 THEN (${min} + ${max}) / 2.0 ELSE NULL END`;
    return this.database.all(`
      SELECT title_clean AS title, COALESCE(NULLIF(TRIM(country_standardized), ''), '[unknown]') AS country,
             ${min} AS minimum_annual, ${center} AS center_annual, ${max} AS maximum_annual,
             ${midpoint} AS midpoint_annual, salary_estimation_status AS estimate_status
      FROM job_cleaning_audit
      WHERE title_key = ?
        AND COALESCE(NULLIF(TRIM(country_standardized), ''), '[unknown]') = ?
        AND ${midpoint} > 0
      ORDER BY midpoint_annual DESC
      LIMIT 20`, normalizeKey(roleKey), countryKey);
  }

  static salaryCurrencies() {
    return Object.keys(SALARY_FIELDS);
  }
}

function escapeLike(value) {
  return String(value ?? '').replace(/[\\%_]/gu, '\\$&');
}

export { ARAB_COUNTRIES, SALARY_FIELDS, NON_COUNTRY_SCOPES };
