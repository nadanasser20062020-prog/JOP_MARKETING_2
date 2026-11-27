'use strict';

const roleTitleModel = require('./role_title_model');

const ARAB_COUNTRIES = Object.freeze([
  'algeria', 'bahrain', 'comoros', 'djibouti', 'egypt', 'iraq', 'jordan', 'kuwait',
  'lebanon', 'libya', 'mauritania', 'morocco', 'oman', 'palestine', 'qatar',
  'saudi arabia', 'somalia', 'sudan', 'syria', 'tunisia', 'united arab emirates', 'yemen',
]);
const NON_GEOGRAPHIC_COUNTRIES = Object.freeze(['remote (anywhere)', 'worldwide', 'other/unknown']);
const ELIGIBLE_SKILL_POLICY_SQL = `(
  (js.skill_match_policy = 'approved_aliases' AND js.skill_review_status = 'curated'
    AND s.match_policy = 'approved_aliases' AND s.review_status = 'curated')
  OR
  (js.skill_match_policy = 'exact_only' AND js.skill_review_status = 'curated_exact_only'
    AND s.match_policy = 'exact_only' AND s.review_status = 'curated_exact_only')
)`;
const FILTER_ELIGIBLE_SKILL_POLICY_SQL = `(
  (filter_js.skill_match_policy = 'approved_aliases' AND filter_js.skill_review_status = 'curated'
    AND filter_s.match_policy = 'approved_aliases' AND filter_s.review_status = 'curated')
  OR
  (filter_js.skill_match_policy = 'exact_only' AND filter_js.skill_review_status = 'curated_exact_only'
    AND filter_s.match_policy = 'exact_only' AND filter_s.review_status = 'curated_exact_only')
)`;

function plain(row) {
  return row == null ? row : { ...row };
}

function all(db, sql, parameters = []) {
  return db.prepare(sql).all(...parameters).map(plain);
}

function one(db, sql, parameters = []) {
  return plain(db.prepare(sql).get(...parameters));
}

function foldCase(value) {
  return String(value || '').toLowerCase()
    .replace(/\u00df/g, 'ss')
    .replace(/\u03c2/g, '\u03c3')
    .replace(/\u017f/g, 's')
    .replace(/\u00b5/g, '\u03bc')
    .replace(/[\uFB00-\uFB06]/g, (ligature) => ({
      '\uFB00': 'ff', '\uFB01': 'fi', '\uFB02': 'fl', '\uFB03': 'ffi',
      '\uFB04': 'ffl', '\uFB05': 'st', '\uFB06': 'st',
    })[ligature]);
}

function normalizeLabel(value) {
  return foldCase(value).trim().replace(/\s+/g, ' ');
}

function normalizeExactLabel(value) {
  // Match SQLite's built-in lower(trim(...)) exactly: SQLite lower() folds ASCII only,
  // and trim() removes U+0020 spaces by default (not all Unicode whitespace).
  return String(value || '')
    .replace(/[A-Z]/g, (character) => character.toLowerCase())
    .replace(/^ +| +$/g, '');
}

function roundPercent(numerator, denominator) {
  if (!denominator) return 0;
  return Math.round((10000 * numerator) / denominator) / 100;
}

function makePage(items, page, pageSize, totalItems) {
  return {
    items,
    pagination: {
      page,
      pageSize,
      totalItems,
      totalPages: totalItems === 0 ? 0 : Math.ceil(totalItems / pageSize),
      hasNextPage: page * pageSize < totalItems,
      hasPreviousPage: page > 1 && totalItems > 0,
    },
  };
}

function pageOffset(page, pageSize) {
  return (page - 1) * pageSize;
}

function jobWhere(filters = {}, alias = 'j') {
  const clauses = ['1 = 1'];
  const parameters = [];
  if (filters.sourceDataset) {
    clauses.push(`${alias}.source_dataset = ?`);
    parameters.push(filters.sourceDataset);
  }
  if (filters.country) {
    clauses.push(`lower(trim(coalesce(${alias}.country, ''))) = ?`);
    parameters.push(normalizeExactLabel(filters.country));
  }
  if (filters.roleId) {
    clauses.push(`lower(trim(coalesce(${alias}.title, ''))) = ?`);
    parameters.push(normalizeExactLabel(filters.roleId));
  }
  if (filters.workMode) {
    clauses.push(`lower(trim(coalesce(${alias}.work_mode_raw, ''))) = ?`);
    parameters.push(normalizeExactLabel(filters.workMode));
  }
  if (filters.experience) {
    clauses.push(`lower(trim(coalesce(${alias}.experience_raw, ''))) = ?`);
    parameters.push(normalizeExactLabel(filters.experience));
  }
  if (filters.skillId) {
    clauses.push(`EXISTS (
      SELECT 1
      FROM job_skills AS filter_js
      JOIN skills AS filter_s ON filter_s.skill_id = filter_js.skill_id
      WHERE filter_js.record_id = ${alias}.record_id
        AND filter_js.skill_id = ?
        AND ${FILTER_ELIGIBLE_SKILL_POLICY_SQL}
    )`);
    parameters.push(filters.skillId);
  }
  return { sql: clauses.join(' AND '), parameters };
}

function rollupWhere(filters = {}, alias = 'r') {
  const clauses = ['1 = 1'];
  const parameters = [];
  if (filters.sourceDataset) {
    clauses.push(`${alias}.source_dataset = ?`);
    parameters.push(filters.sourceDataset);
  }
  if (filters.country) {
    clauses.push(`${alias}.country_key = ?`);
    parameters.push(normalizeExactLabel(filters.country));
  }
  if (filters.roleId) {
    clauses.push(`${alias}.role_id = ?`);
    parameters.push(normalizeExactLabel(filters.roleId));
  }
  if (filters.workMode) {
    clauses.push(`${alias}.work_mode_key = ?`);
    parameters.push(normalizeExactLabel(filters.workMode));
  }
  if (filters.experience) {
    clauses.push(`${alias}.experience_key = ?`);
    parameters.push(normalizeExactLabel(filters.experience));
  }
  return { sql: clauses.join(' AND '), parameters };
}

function eligibleJoin(alias = 'j') {
  return `
    JOIN job_skills AS js ON js.record_id = ${alias}.record_id
    JOIN skills AS s ON s.skill_id = js.skill_id
      AND js.skill_match_policy = s.match_policy
      AND js.skill_review_status = s.review_status
      AND ${ELIGIBLE_SKILL_POLICY_SQL}
  `;
}

function eligibleSkillById(db, skillId) {
  return one(db, `
    SELECT s.skill_id AS skillId, s.canonical_name AS canonicalName,
           s.category, s.match_policy AS matchPolicy, s.review_status AS reviewStatus
    FROM skills AS s
    WHERE s.skill_id = ?
      AND (
        (s.match_policy = 'approved_aliases' AND s.review_status = 'curated')
        OR (s.match_policy = 'exact_only' AND s.review_status = 'curated_exact_only')
      )
  `, [skillId]);
}

function buildEligibleQuery(filters = {}, options = {}) {
  const alias = options.alias || 'j';
  const where = jobWhere(filters, alias);
  if (where.sql === '1 = 1') {
    return {
      from: `job_skills AS js
        JOIN skills AS s ON s.skill_id = js.skill_id
          AND js.skill_match_policy = s.match_policy
          AND js.skill_review_status = s.review_status
          AND ${ELIGIBLE_SKILL_POLICY_SQL}`,
      where: '1 = 1',
      parameters: [],
    };
  }
  return {
    from: `jobs AS ${alias} ${eligibleJoin(alias)}`,
    where: where.sql,
    parameters: where.parameters,
  };
}

function getEligibleDenominator(db, filters = {}) {
  const table = filters.roleId ? 'api_role_scope_rollups' : 'api_scope_rollups';
  const where = rollupWhere(filters);
  const row = one(db, `
    SELECT COALESCE(SUM(eligible_job_record_count), 0) AS count
    FROM ${table} AS r
    WHERE ${where.sql}
  `, where.parameters);
  return Number(row?.count || 0);
}

function getMarketComparison(db, limit = 10) {
  const arabValues = ARAB_COUNTRIES.map((country) => `'${country.replaceAll("'", "''")}'`).join(', ');
  const invalidValues = NON_GEOGRAPHIC_COUNTRIES.map((country) => `'${country.replaceAll("'", "''")}'`).join(', ');
  const countryScope = `
    r.source_dataset = 'merged_tech_jobs'
    AND r.country_key <> ''
    AND r.country_key NOT IN (${invalidValues})
  `;
  const marketKey = `CASE WHEN r.country_key IN (${arabValues})
    THEN 'arabMarkets' ELSE 'otherRepresentedMarkets' END`;
  const populationRows = all(db, `
    SELECT ${marketKey} AS marketKey,
           SUM(r.job_record_count) AS countryMappedJobRecords,
           SUM(r.eligible_job_record_count) AS recordsWithEligibleSkills
    FROM api_scope_rollups AS r
    WHERE ${countryScope}
    GROUP BY marketKey
  `);
  const skillRows = all(db, `
    SELECT ${marketKey} AS marketKey,
           r.skill_id AS skillId,
           MIN(r.canonical_name) AS skillName,
           MIN(r.category) AS category,
           SUM(r.job_record_count) AS jobRecordCount
    FROM api_scope_skill_rollups AS r
    WHERE ${countryScope}
    GROUP BY marketKey, r.skill_id
    ORDER BY marketKey, jobRecordCount DESC, skillName COLLATE NOCASE
  `);
  const observedCountries = new Set(all(db, `
    SELECT DISTINCT r.country_key AS countryKey
    FROM api_scope_rollups AS r
    WHERE ${countryScope}
  `).map((row) => row.countryKey));
  const groupDefinitions = [
    { key: 'arabMarkets', label: 'Arab markets' },
    { key: 'otherRepresentedMarkets', label: 'Other represented markets' },
  ];
  const groups = groupDefinitions.map((definition) => {
    const population = populationRows.find((row) => row.marketKey === definition.key);
    const denominator = Number(population?.recordsWithEligibleSkills || 0);
    const skills = skillRows
      .filter((row) => row.marketKey === definition.key)
      .slice(0, limit)
      .map((row) => ({
        skillId: row.skillId,
        name: row.skillName,
        category: row.category,
        jobRecordCount: Number(row.jobRecordCount),
        denominator,
        sharePercent: roundPercent(Number(row.jobRecordCount), denominator),
      }));
    return {
      key: definition.key,
      label: definition.label,
      sourceDataset: 'merged_tech_jobs',
      countryMappedJobRecords: Number(population?.countryMappedJobRecords || 0),
      recordsWithEligibleSkills: denominator,
      skills,
    };
  });
  return {
    comparisonName: 'Arab markets vs other represented markets',
    sourceDataset: 'merged_tech_jobs',
    denominatorDefinition: 'Country-mapped job records with at least one eligible, reviewed skill link in each cohort.',
    dateSemantics: 'Source date semantics are not sufficient to describe either cohort as current.',
    groups,
    unrepresentedArabCountryLabels: ARAB_COUNTRIES.filter((country) => !observedCountries.has(country)),
    limitations: [
      'This is a descriptive comparison of records in one shared source, not a census or a current-market estimate.',
      'Unrepresented country labels indicate missing coverage, not zero opportunities.',
      'A skill association is not proof that an employer requires that skill.',
    ],
  };
}

function getOverview(db, filters = {}) {
  const where = rollupWhere(filters);
  const invalidValues = NON_GEOGRAPHIC_COUNTRIES.map((country) => `'${country.replaceAll("'", "''")}'`).join(', ');
  const totals = one(db, `
    SELECT COALESCE(SUM(r.job_record_count), 0) AS totalJobs,
           COUNT(DISTINCT CASE
             WHEN r.country_key <> '' AND r.country_key NOT IN (${invalidValues})
             THEN r.country_key END) AS totalCountries
    FROM api_scope_rollups AS r
    WHERE ${where.sql}
  `, where.parameters);
  const denominator = getEligibleDenominator(db, filters);
  const totalSkillsRow = one(db, `
    SELECT COUNT(DISTINCT r.skill_id) AS count
    FROM api_scope_skill_rollups AS r
    WHERE ${where.sql}
  `, where.parameters);
  const countryRows = all(db, `
    SELECT r.country_key AS countryKey,
           MIN(r.country_label) AS country,
           SUM(r.job_record_count) AS jobRecordCount
    FROM api_scope_rollups AS r
    WHERE ${where.sql}
      AND r.country_key <> '' AND r.country_key NOT IN (${invalidValues})
    GROUP BY r.country_key
    ORDER BY jobRecordCount DESC, country COLLATE NOCASE
  `, where.parameters);
  const skillRows = all(db, `
    SELECT r.skill_id AS skillId, MIN(r.canonical_name) AS name,
           MIN(r.category) AS category, SUM(r.job_record_count) AS jobRecordCount
    FROM api_scope_skill_rollups AS r
    WHERE ${where.sql}
    GROUP BY r.skill_id
    ORDER BY jobRecordCount DESC, name COLLATE NOCASE
    LIMIT 10
  `, where.parameters);
  return {
    filters: {
      sourceDataset: filters.sourceDataset || null,
      country: filters.country || null,
    },
    kpis: {
      totalJobs: Number(totals?.totalJobs || 0),
      totalSkills: Number(totalSkillsRow?.count || 0),
      totalCountries: Number(totals?.totalCountries || 0),
      recordsWithEligibleSkills: denominator,
    },
    countryMap: countryRows.map((row) => ({
      countryKey: row.countryKey,
      country: row.country,
      jobRecordCount: Number(row.jobRecordCount),
    })),
    topSkills: skillRows.map((row) => ({
      skillId: row.skillId,
      name: row.name,
      category: row.category,
      jobRecordCount: Number(row.jobRecordCount),
      denominator,
      sharePercent: roundPercent(Number(row.jobRecordCount), denominator),
    })),
    marketComparison: getMarketComparison(db, 10),
    metricNotes: {
      totalJobs: 'Retained source job-ad rows in the selected scope; not unique vacancies.',
      totalSkills: 'Distinct eligible skill IDs observed in the selected scope, not job-skill assignments.',
      totalCountries: 'Distinct non-empty country labels after case/outer-space normalization and removal of known non-geographic labels; labels are not ISO-normalized.',
      skillShare: 'Skill-linked records divided by selected-scope records with at least one eligible skill link.',
    },
  };
}

function getSnapshot(db) {
  try {
    const row = one(db, `
      SELECT import_run_id AS importRunId,
             pipeline_version AS pipelineVersion,
             source_archive_run_id AS archiveRunId,
             archive_generated_on_utc AS archiveGeneratedOnUtc,
             archive_job_rows AS archivedJobRows,
             archive_job_skill_rows AS archivedJobSkillRows
      FROM import_runs
      WHERE run_status = 'succeeded'
      ORDER BY import_run_id DESC
      LIMIT 1
    `);
    if (!row) return null;
    return {
      importRunId: Number(row.importRunId),
      pipelineVersion: row.pipelineVersion || null,
      archiveRunId: row.archiveRunId || null,
      generatedOnUtc: row.archiveGeneratedOnUtc || null,
      archivedJobRows: row.archivedJobRows == null ? null : Number(row.archivedJobRows),
      archivedJobSkillRows: row.archivedJobSkillRows == null ? null : Number(row.archivedJobSkillRows),
    };
  } catch {
    return null;
  }
}

function getDatabaseHealth(db) {
  const requiredTables = [
    'jobs', 'job_skills', 'skills', 'skill_aliases', 'data_sources', 'import_runs',
    'learning_resources', 'learning_resource_skills', 'learning_resource_languages',
    'api_scope_rollups', 'api_scope_skill_rollups', 'api_role_scope_rollups',
    'api_role_skill_rollups', 'api_source_field_coverage', 'api_historical_month_rollups',
  ];
  const existingTables = new Set(all(db, `
    SELECT name FROM sqlite_master WHERE type = 'table'
  `).map((row) => row.name));
  const missingTables = requiredTables.filter((tableName) => !existingTables.has(tableName));
  if (missingTables.length) {
    const error = new Error('The local data file does not have the required application schema.');
    error.code = 'DATABASE_SCHEMA_UNAVAILABLE';
    throw error;
  }
  const row = one(db, 'SELECT COUNT(*) AS count FROM jobs');
  return { status: 'ok', storage: 'local_sqlite', jobRecordCount: Number(row?.count || 0) };
}

function getMetadata(db, appUrl) {
  const totals = one(db, `
    SELECT COALESCE(SUM(job_record_count), 0) AS totalJobs,
           COUNT(*) AS sourceDatasetCount
    FROM api_source_field_coverage
  `);
  const invalidValues = NON_GEOGRAPHIC_COUNTRIES.map((country) => `'${country.replaceAll("'", "''")}'`).join(', ');
  const countryRow = one(db, `
    SELECT COUNT(DISTINCT r.country_key) AS count
    FROM api_scope_rollups AS r
    WHERE r.country_key <> ''
      AND r.country_key NOT IN (${invalidValues})
  `);
  const skillTotals = one(db, `
    SELECT (SELECT COUNT(DISTINCT skill_id) FROM api_scope_skill_rollups) AS distinctSkills,
           (SELECT COALESCE(SUM(eligible_job_record_count), 0) FROM api_scope_rollups) AS recordsWithEligibleSkills,
           (SELECT COALESCE(SUM(job_record_count), 0) FROM api_scope_skill_rollups) AS eligibleJobSkillLinks
  `);
  const sources = all(db, `
    SELECT d.source_dataset AS sourceDataset,
           d.display_name AS displayName,
           d.source_kind AS sourceKind,
           d.snapshot_bucket AS snapshotBucket,
           d.date_semantics AS dateSemantics,
           d.listing_status AS listingStatus,
           COALESCE(c.job_record_count, 0) AS jobRecordCount
    FROM data_sources AS d
    LEFT JOIN api_source_field_coverage AS c ON c.source_dataset = d.source_dataset
    ORDER BY jobRecordCount DESC, d.source_dataset
  `).map((row) => ({ ...row, jobRecordCount: Number(row.jobRecordCount) }));
  const fields = [
    ['title', 'title_records'], ['company', 'company_records'], ['country', 'country_records'],
    ['city', 'city_records'], ['description', 'description_records'], ['sourceUrl', 'source_url_records'],
    ['salaryRaw', 'salary_raw_records'], ['postedAt', 'posted_at_records'], ['workModeRaw', 'work_mode_raw_records'],
  ];
  const coverageSelect = fields.map(([key, column]) =>
    `COALESCE(SUM(${column}), 0) AS ${key}`
  ).join(',\n');
  const coverageRow = one(db, `SELECT ${coverageSelect} FROM api_source_field_coverage`);
  const fieldCoverage = Object.fromEntries(fields.map(([key]) => [
    key,
    {
      availableRecords: Number(coverageRow?.[key] || 0),
      denominator: Number(totals?.totalJobs || 0),
      sharePercent: roundPercent(Number(coverageRow?.[key] || 0), Number(totals?.totalJobs || 0)),
    },
  ]));
  const historicalDates = one(db, `
    SELECT COUNT(*) AS datedRecords,
           MIN(substr(posted_at, 1, 10)) AS firstDate,
           MAX(substr(posted_at, 1, 10)) AS lastDate
    FROM jobs
    WHERE source_dataset = 'international_jobs'
      AND source_date_field = 'posted_at_or_job_posted_date'
      AND posted_at IS NOT NULL AND trim(posted_at) <> ''
      AND substr(posted_at, 1, 4) = '2023'
  `);
  const listingStatuses = all(db, `
    SELECT coalesce(nullif(trim(listing_status), ''), 'not_available') AS status,
           COUNT(*) AS jobRecordCount
    FROM jobs
    GROUP BY coalesce(nullif(trim(listing_status), ''), 'not_available')
    ORDER BY jobRecordCount DESC, status
  `).map((row) => ({ ...row, jobRecordCount: Number(row.jobRecordCount) }));
  return {
    apiVersion: 'v1',
    appUrl,
    storage: { engine: 'SQLite', mode: 'local_file', readOnlyFromApi: true, networkDatabase: false },
    dataset: {
      snapshot: getSnapshot(db),
      totals: {
        jobRecords: Number(totals?.totalJobs || 0),
        sourceDatasets: Number(totals?.sourceDatasetCount || 0),
        representedCountryLabels: Number(countryRow?.count || 0),
        eligibleSkillIds: Number(skillTotals?.distinctSkills || 0),
        eligibleJobSkillLinks: Number(skillTotals?.eligibleJobSkillLinks || 0),
        recordsWithEligibleSkills: Number(skillTotals?.recordsWithEligibleSkills || 0),
      },
      sources,
      fieldCoverage,
      listingStatuses,
      reliableDateCoverage: {
        sourceDataset: 'international_jobs',
        from: historicalDates?.firstDate || null,
        to: historicalDates?.lastDate || null,
        datedRecords: Number(historicalDates?.datedRecords || 0),
        interpretation: 'Explicit source posting-date fields from the historical 2023 sample only; not a current trend.',
      },
    },
    supportedFilters: {
      jobSearch: ['q', 'sourceDataset', 'country', 'roleId', 'skillId', 'workModeRaw', 'experienceRaw', 'page', 'pageSize', 'sort', 'order'],
      salaryFiltering: false,
      activeListingFiltering: false,
      salaryReason: 'Salary units, currencies, and provenance are not sufficiently comparable for a product filter.',
    },
    productRules: {
      eligibleSkillPairs: [
        ['approved_aliases', 'curated'],
        ['exact_only', 'curated_exact_only'],
      ],
      aliasNormalization: 'Case-fold and collapse whitespace only; no fuzzy matching.',
      missingValues: 'Unavailable or missing values are not zero and are not inferred.',
      listingStatus: 'No record is confirmed active.',
      marketResults: 'Describe the collected sample only, not the complete labor market.',
      requestPrivacy: 'Skill-match input is processed in memory for this request only and is not stored or logged.',
    },
  };
}

function safeExternalUrl(value) {
  if (!value) return null;
  try {
    const parsed = new URL(String(value));
    return ['https:', 'http:'].includes(parsed.protocol) ? parsed.toString() : null;
  } catch {
    return null;
  }
}

function formatJob(row, includeDescription = false) {
  if (!row) return null;
  return {
    recordId: row.record_id,
    sourceDataset: row.source_dataset,
    sourceFile: row.source_file,
    sourceRecordId: row.source_record_id,
    title: row.title,
    titleShort: row.title_short,
    company: row.company,
    country: row.country,
    city: row.city,
    region: row.region,
    locationRaw: row.location_raw,
    workModeRaw: row.work_mode_raw,
    remoteFlag: row.remote_flag,
    employmentTypeRaw: row.employment_type_raw,
    experienceRaw: row.experience_raw,
    categoryRaw: row.category_raw,
    ...(includeDescription ? { description: row.description } : {}),
    postedAt: row.posted_at,
    sourceUpdatedAt: row.source_updated_at,
    sourceDateField: row.source_date_field,
    salary: {
      raw: row.salary_raw,
      annualValueRaw: row.salary_year_avg,
      hourlyValueRaw: row.salary_hour_avg,
      currency: row.salary_currency,
      basis: row.salary_basis,
      provenance: row.salary_provenance_status,
      comparisonAvailable: false,
    },
    skillsRaw: row.skills,
    skillsSource: row.skills_source,
    skillsEnrichmentStatus: row.skills_enrichment_status,
    sourceUrl: safeExternalUrl(row.source_url),
    listingStatus: row.listing_status || 'unknown_not_verified',
    snapshotType: row.snapshot_type,
    exactDuplicateWithinSource: row.exact_duplicate_within_source,
    dataQualityFlags: row.data_quality_flags,
  };
}

function getJobs(db, filters, page, pageSize, searchTerm, sort, order) {
  const where = jobWhere(filters);
  const clauses = [where.sql];
  const parameters = [...where.parameters];
  if (searchTerm) {
    const escaped = `%${searchTerm.replace(/[\\%_]/g, '\\$&')}%`;
    clauses.push(`(
      lower(coalesce(j.title, '')) LIKE ? ESCAPE '\\'
      OR lower(coalesce(j.company, '')) LIKE ? ESCAPE '\\'
      OR lower(coalesce(j.city, '')) LIKE ? ESCAPE '\\'
      OR lower(coalesce(j.country, '')) LIKE ? ESCAPE '\\'
    )`);
    parameters.push(escaped, escaped, escaped, escaped);
  }
  const whereSql = clauses.join(' AND ');
  const sortColumns = {
    title: 'j.title COLLATE NOCASE',
    company: 'j.company COLLATE NOCASE',
    country: 'j.country COLLATE NOCASE',
    sourceDataset: 'j.source_dataset COLLATE NOCASE',
  };
  const sortSql = sortColumns[sort] || sortColumns.title;
  const direction = order === 'desc' ? 'DESC' : 'ASC';
  const count = one(db, `SELECT COUNT(*) AS count FROM jobs AS j WHERE ${whereSql}`, parameters);
  const rows = all(db, `
    SELECT j.*
    FROM jobs AS j
    WHERE ${whereSql}
    ORDER BY ${sortSql} ${direction}, j.record_id ASC
    LIMIT ? OFFSET ?
  `, [...parameters, pageSize, pageOffset(page, pageSize)]);
  return makePage(rows.map((row) => formatJob(row, false)), page, pageSize, Number(count?.count || 0));
}

function getJobById(db, recordId) {
  const row = one(db, 'SELECT * FROM jobs WHERE record_id = ?', [recordId]);
  if (!row) return null;
  const skillRows = all(db, `
    SELECT s.skill_id AS skillId, s.canonical_name AS name, s.category,
           js.skill_raw AS sourceLabel, js.skill_provenance AS provenance
    FROM jobs AS j
    ${eligibleJoin('j')}
    WHERE j.record_id = ?
    GROUP BY s.skill_id, s.canonical_name, s.category, js.skill_raw, js.skill_provenance
    ORDER BY s.canonical_name COLLATE NOCASE
  `, [recordId]);
  return {
    ...formatJob(row, true),
    reviewedSkills: skillRows,
    detailNotes: [
      'Skill links are source/enrichment evidence and are not independently verified job requirements.',
      'The source listing status is not verified as active.',
      'The description and source fields are untrusted source text; render them as text, not executable HTML.',
    ],
  };
}

function getRoles(db, filters, page, pageSize, searchTerm) {
  const where = rollupWhere(filters);
  const clauses = [where.sql, "r.role_id <> ''"];
  const parameters = [...where.parameters];
  if (searchTerm) {
    clauses.push("r.role_id LIKE ? ESCAPE '\\'");
    parameters.push(`${searchTerm.replace(/[\\%_]/g, '\\$&')}%`);
  }
  const whereSql = clauses.join(' AND ');
  const count = one(db, `
    SELECT COUNT(*) AS count FROM (
      SELECT r.role_id
      FROM api_role_scope_rollups AS r
      WHERE ${whereSql}
      GROUP BY r.role_id
    )
  `, parameters);
  const rows = all(db, `
    SELECT r.role_id AS roleId,
           MIN(r.role_display_title) AS displayTitle,
           SUM(r.job_record_count) AS jobRecordCount
    FROM api_role_scope_rollups AS r
    WHERE ${whereSql}
    GROUP BY r.role_id
    ORDER BY jobRecordCount DESC, roleId
    LIMIT ? OFFSET ?
  `, [...parameters, pageSize, pageOffset(page, pageSize)]);
  return makePage(rows.map((row) => ({
    roleId: row.roleId,
    displayTitle: row.displayTitle,
    jobRecordCount: Number(row.jobRecordCount),
  })), page, pageSize, Number(count?.count || 0));
}

function emptySalarySummary(reason) {
  return {
    available: false,
    recordsWithSalaryText: 0,
    recordsWithAnySalaryField: 0,
    salaryFieldDefinition: 'A role record with a non-empty salary_raw, salary_year_avg, or salary_hour_avg field; raw text and non-disclosure strings are not assumed to be numeric amounts.',
    byCountryCoverageDefinition: 'Each geographic country group reports field coverage counts over roleCountryRecordCount; zero salary-field records are a sample-coverage count, not a zero salary value.',
    recordsWithExplicitCurrency: 0,
    annualValueRecords: 0,
    hourlyValueRecords: 0,
    recordsWithUnverifiedProvenance: 0,
    recordsWithEstimateOrResearchProvenance: 0,
    recordsWithUnavailableProvenance: 0,
    annualValuesWithCurrencyAndMatchingPeriod: 0,
    hourlyValuesWithCurrencyAndMatchingPeriod: 0,
    byCountryCoverage: [],
    comparisonRequirements: [
      'A numeric amount in a documented value field.',
      'An explicit currency for every contributing record.',
      'A declared pay period matching the annual or hourly amount field.',
      'Reviewed source provenance and an adequate sample for each displayed group.',
    ],
    reason,
  };
}

function getRoleAnalysis(db, roleId, filters = {}) {
  const normalizedRoleId = normalizeExactLabel(roleId);
  const globalRole = one(db, `
    SELECT MIN(role_display_title) AS displayTitle
    FROM api_role_scope_rollups
    WHERE role_id = ?
    GROUP BY role_id
  `, [normalizedRoleId]);
  if (!globalRole) return null;

  const scopedFilters = { ...filters, roleId: normalizedRoleId };
  const where = rollupWhere(scopedFilters);
  const totalRow = one(db, `
    SELECT COALESCE(SUM(job_record_count), 0) AS count
    FROM api_role_scope_rollups AS r
    WHERE ${where.sql}
  `, where.parameters);
  const totalJobRecords = Number(totalRow?.count || 0);
  if (totalJobRecords === 0) {
    return {
      role: { roleId: normalizedRoleId, displayTitle: globalRole.displayTitle, jobRecordCount: 0, recordsWithEligibleSkills: 0 },
      countryDistribution: { denominator: 0, denominatorDefinition: 'Role records with a non-empty, non-placeholder country label in the selected scope.', countries: [] },
      skills: { denominator: 0, denominatorDefinition: 'Role records in the selected scope with at least one eligible, reviewed skill link.', overall: [], byCountry: [] },
      salary: emptySalarySummary('No records match the selected role and filters.'),
      relatedAdsPath: `/api/v1/roles/${encodeURIComponent(normalizedRoleId)}/ads`,
      limitations: [
        'No records match the selected scope; an empty result is not evidence of zero demand in the wider market.',
        'Exact role matching normalizes case and outer whitespace only; seniority, punctuation, and semantic title variants remain distinct.',
      ],
    };
  }
  const denominator = getEligibleDenominator(db, scopedFilters);
  const role = one(db, `
    SELECT r.role_id AS roleId,
           MIN(r.role_display_title) AS displayTitle,
           SUM(r.job_record_count) AS jobRecordCount
    FROM api_role_scope_rollups AS r
    WHERE ${where.sql}
    GROUP BY r.role_id
  `, where.parameters);
  const countryRows = all(db, `
    SELECT r.country_key AS countryKey,
           MIN(r.country_label) AS country,
           SUM(r.job_record_count) AS jobRecordCount
    FROM api_role_scope_rollups AS r
    WHERE ${where.sql}
      AND r.country_key <> ''
      AND r.country_key NOT IN ('remote (anywhere)', 'worldwide', 'other/unknown')
    GROUP BY r.country_key
    ORDER BY jobRecordCount DESC, country COLLATE NOCASE
  `, where.parameters);
  const countryDenominators = all(db, `
    SELECT r.country_key AS countryKey,
           SUM(r.eligible_job_record_count) AS recordsWithEligibleSkills
    FROM api_role_scope_rollups AS r
    WHERE ${where.sql}
      AND r.country_key <> ''
      AND r.country_key NOT IN ('remote (anywhere)', 'worldwide', 'other/unknown')
    GROUP BY r.country_key
  `, where.parameters);
  const denominatorByCountry = new Map(countryDenominators.map((row) => [row.countryKey, Number(row.recordsWithEligibleSkills)]));
  const skillRows = all(db, `
    SELECT r.skill_id AS skillId, MIN(r.canonical_name) AS name,
           MIN(r.category) AS category, SUM(r.job_record_count) AS jobRecordCount
    FROM api_role_skill_rollups AS r
    WHERE ${where.sql}
    GROUP BY r.skill_id
    ORDER BY jobRecordCount DESC, name COLLATE NOCASE
    LIMIT 50
  `, where.parameters);
  const skillByCountryRows = all(db, `
    SELECT r.country_key AS countryKey, r.skill_id AS skillId,
           MIN(r.canonical_name) AS name, MIN(r.category) AS category,
           SUM(r.job_record_count) AS jobRecordCount
    FROM api_role_skill_rollups AS r
    WHERE ${where.sql}
      AND r.country_key <> ''
      AND r.country_key NOT IN ('remote (anywhere)', 'worldwide', 'other/unknown')
    GROUP BY r.country_key, r.skill_id
    ORDER BY countryKey, jobRecordCount DESC, name COLLATE NOCASE
  `, where.parameters);
  const groupedSkillsByCountry = new Map();
  for (const row of skillByCountryRows) {
    const denominatorForCountry = denominatorByCountry.get(row.countryKey) || 0;
    const current = groupedSkillsByCountry.get(row.countryKey) || [];
    if (current.length < 20) {
      current.push({
        skillId: row.skillId,
        name: row.name,
        category: row.category,
        jobRecordCount: Number(row.jobRecordCount),
        denominator: denominatorForCountry,
        sharePercent: roundPercent(Number(row.jobRecordCount), denominatorForCountry),
      });
    }
    groupedSkillsByCountry.set(row.countryKey, current);
  }
  const salaryJobFilter = jobWhere(scopedFilters, 'j');
  const salaryRowsByCountry = all(db, `
    WITH scoped_salary AS (
      SELECT j.country,
             COALESCE(lower(trim(j.country)), '') AS countryKey,
             CASE WHEN (NULLIF(trim(j.salary_raw), '') IS NOT NULL
                        OR NULLIF(trim(j.salary_year_avg), '') IS NOT NULL
                        OR NULLIF(trim(j.salary_hour_avg), '') IS NOT NULL)
                  THEN 1 ELSE 0 END AS hasSalaryField,
             CASE WHEN (NULLIF(trim(j.salary_raw), '') IS NOT NULL
                        OR NULLIF(trim(j.salary_year_avg), '') IS NOT NULL
                        OR NULLIF(trim(j.salary_hour_avg), '') IS NOT NULL)
                        AND NULLIF(trim(j.salary_currency), '') IS NOT NULL
                  THEN 1 ELSE 0 END AS hasExplicitCurrency,
             CASE WHEN NULLIF(trim(j.salary_year_avg), '') IS NOT NULL
                  THEN 1 ELSE 0 END AS hasAnnualValue,
             CASE WHEN NULLIF(trim(j.salary_hour_avg), '') IS NOT NULL
                  THEN 1 ELSE 0 END AS hasHourlyValue,
             CASE WHEN (NULLIF(trim(j.salary_raw), '') IS NOT NULL
                        OR NULLIF(trim(j.salary_year_avg), '') IS NOT NULL
                        OR NULLIF(trim(j.salary_hour_avg), '') IS NOT NULL)
                        AND j.salary_provenance_status = 'source_or_origin_unverified'
                  THEN 1 ELSE 0 END AS hasUnverifiedProvenance,
             CASE WHEN (NULLIF(trim(j.salary_raw), '') IS NOT NULL
                        OR NULLIF(trim(j.salary_year_avg), '') IS NOT NULL
                        OR NULLIF(trim(j.salary_hour_avg), '') IS NOT NULL)
                        AND j.salary_provenance_status = 'estimate_or_research_indicated'
                  THEN 1 ELSE 0 END AS hasEstimateOrResearchProvenance,
             CASE WHEN (NULLIF(trim(j.salary_raw), '') IS NOT NULL
                        OR NULLIF(trim(j.salary_year_avg), '') IS NOT NULL
                        OR NULLIF(trim(j.salary_hour_avg), '') IS NOT NULL)
                        AND (j.salary_provenance_status IS NULL
                             OR trim(j.salary_provenance_status) = ''
                             OR j.salary_provenance_status = 'not_available')
                  THEN 1 ELSE 0 END AS hasUnavailableProvenance,
             CASE WHEN NULLIF(trim(j.salary_year_avg), '') IS NOT NULL
                        AND NULLIF(trim(j.salary_currency), '') IS NOT NULL
                        AND lower(trim(COALESCE(j.salary_basis, ''))) IN ('year', 'annual', 'yearly', 'per year')
                        AND lower(trim(COALESCE(j.salary_rate, ''))) IN ('year', 'annual', 'yearly', 'per year')
                  THEN 1 ELSE 0 END AS annualWithCurrencyAndPeriod,
             CASE WHEN NULLIF(trim(j.salary_hour_avg), '') IS NOT NULL
                        AND NULLIF(trim(j.salary_currency), '') IS NOT NULL
                        AND lower(trim(COALESCE(j.salary_basis, ''))) IN ('hour', 'hourly', 'per hour')
                        AND lower(trim(COALESCE(j.salary_rate, ''))) IN ('hour', 'hourly', 'per hour')
                  THEN 1 ELSE 0 END AS hourlyWithCurrencyAndPeriod
      FROM jobs AS j
      WHERE ${salaryJobFilter.sql}
    )
    SELECT countryKey,
           MIN(NULLIF(trim(country), '')) AS country,
           COUNT(*) AS roleCountryRecordCount,
           SUM(hasSalaryField) AS recordsWithAnySalaryField,
           SUM(hasExplicitCurrency) AS recordsWithExplicitCurrency,
           SUM(hasAnnualValue) AS annualValueRecords,
           SUM(hasHourlyValue) AS hourlyValueRecords,
           SUM(hasUnverifiedProvenance) AS recordsWithUnverifiedProvenance,
           SUM(hasEstimateOrResearchProvenance) AS recordsWithEstimateOrResearchProvenance,
           SUM(hasUnavailableProvenance) AS recordsWithUnavailableProvenance,
           SUM(annualWithCurrencyAndPeriod) AS annualValuesWithCurrencyAndMatchingPeriod,
           SUM(hourlyWithCurrencyAndPeriod) AS hourlyValuesWithCurrencyAndMatchingPeriod
    FROM scoped_salary
    GROUP BY countryKey
  `, salaryJobFilter.parameters);
  const salaryMetricFields = [
    'recordsWithAnySalaryField',
    'recordsWithExplicitCurrency',
    'annualValueRecords',
    'hourlyValueRecords',
    'recordsWithUnverifiedProvenance',
    'recordsWithEstimateOrResearchProvenance',
    'recordsWithUnavailableProvenance',
    'annualValuesWithCurrencyAndMatchingPeriod',
    'hourlyValuesWithCurrencyAndMatchingPeriod',
  ];
  const salaryTotals = Object.fromEntries(salaryMetricFields.map((field) => [field, 0]));
  for (const row of salaryRowsByCountry) {
    for (const field of salaryMetricFields) {
      salaryTotals[field] += Number(row[field] || 0);
    }
  }
  const salaryByCountryKey = new Map(salaryRowsByCountry.map((row) => [row.countryKey, row]));
  const salaryByCountryCoverage = countryRows.map((row) => {
    const salaryRow = salaryByCountryKey.get(row.countryKey);
    const roleCountryRecordCount = Number(row.jobRecordCount);
    const recordsWithAnySalaryField = Number(salaryRow?.recordsWithAnySalaryField || 0);
    return {
      countryKey: row.countryKey,
      country: row.country,
      roleCountryRecordCount,
      recordsWithAnySalaryField,
      salaryFieldCoveragePercent: roundPercent(recordsWithAnySalaryField, roleCountryRecordCount),
      recordsWithExplicitCurrency: Number(salaryRow?.recordsWithExplicitCurrency || 0),
      annualValueRecords: Number(salaryRow?.annualValueRecords || 0),
      hourlyValueRecords: Number(salaryRow?.hourlyValueRecords || 0),
      recordsWithUnverifiedProvenance: Number(salaryRow?.recordsWithUnverifiedProvenance || 0),
      recordsWithEstimateOrResearchProvenance: Number(salaryRow?.recordsWithEstimateOrResearchProvenance || 0),
      recordsWithUnavailableProvenance: Number(salaryRow?.recordsWithUnavailableProvenance || 0),
      annualValuesWithCurrencyAndMatchingPeriod: Number(salaryRow?.annualValuesWithCurrencyAndMatchingPeriod || 0),
      hourlyValuesWithCurrencyAndMatchingPeriod: Number(salaryRow?.hourlyValuesWithCurrencyAndMatchingPeriod || 0),
    };
  });
  const overallSkills = skillRows.map((row) => ({
    skillId: row.skillId,
    name: row.name,
    category: row.category,
    jobRecordCount: Number(row.jobRecordCount),
    denominator,
    sharePercent: roundPercent(Number(row.jobRecordCount), denominator),
  }));
  const skillByCountry = countryRows.map((row) => ({
    countryKey: row.countryKey,
    country: row.country,
    jobRecordCount: Number(row.jobRecordCount),
    denominator: denominatorByCountry.get(row.countryKey) || 0,
    skills: groupedSkillsByCountry.get(row.countryKey) || [],
  }));
  return {
    role: {
      roleId: role?.roleId || normalizeExactLabel(roleId),
      displayTitle: role?.displayTitle || roleId,
      jobRecordCount: totalJobRecords,
      recordsWithEligibleSkills: denominator,
    },
    countryDistribution: {
      denominator: countryRows.reduce((sum, row) => sum + Number(row.jobRecordCount), 0),
      denominatorDefinition: 'Role records with a non-empty, non-placeholder country label in the selected scope.',
      countries: countryRows.map((row) => ({
        countryKey: row.countryKey,
        country: row.country,
        jobRecordCount: Number(row.jobRecordCount),
        sharePercent: roundPercent(Number(row.jobRecordCount), countryRows.reduce((sum, item) => sum + Number(item.jobRecordCount), 0)),
      })),
    },
    skills: {
      denominator,
      denominatorDefinition: 'Role records in the selected scope with at least one eligible, reviewed skill link.',
      overall: overallSkills,
      byCountry: skillByCountry,
    },
    salary: {
      ...emptySalarySummary('Salary amount, currency, pay period, and source provenance do not pass the comparison gate; no mean or median is inferred.'),
      recordsWithSalaryText: salaryTotals.recordsWithAnySalaryField,
      recordsWithAnySalaryField: salaryTotals.recordsWithAnySalaryField,
      recordsWithExplicitCurrency: salaryTotals.recordsWithExplicitCurrency,
      annualValueRecords: salaryTotals.annualValueRecords,
      hourlyValueRecords: salaryTotals.hourlyValueRecords,
      recordsWithUnverifiedProvenance: salaryTotals.recordsWithUnverifiedProvenance,
      recordsWithEstimateOrResearchProvenance: salaryTotals.recordsWithEstimateOrResearchProvenance,
      recordsWithUnavailableProvenance: salaryTotals.recordsWithUnavailableProvenance,
      annualValuesWithCurrencyAndMatchingPeriod: salaryTotals.annualValuesWithCurrencyAndMatchingPeriod,
      hourlyValuesWithCurrencyAndMatchingPeriod: salaryTotals.hourlyValuesWithCurrencyAndMatchingPeriod,
      byCountryCoverage: salaryByCountryCoverage,
    },
    relatedAdsPath: `/api/v1/roles/${encodeURIComponent(role?.roleId || normalizeExactLabel(roleId))}/ads`,
    limitations: [
      'Exact role matching normalizes case and outer whitespace only; seniority, punctuation, and semantic title variants remain distinct.',
      'Counts describe retained source rows, not unique vacancies.',
      'Skill mentions are not proof of mandatory employer requirements.',
    ],
  };
}

function getSkills(db, filters, page, pageSize, searchTerm) {
  const where = rollupWhere(filters);
  const clauses = [where.sql];
  const parameters = [...where.parameters];
  if (searchTerm) {
    clauses.push(`(
      lower(s.canonical_name) LIKE ? ESCAPE '\\'
      OR EXISTS (
        SELECT 1 FROM skill_aliases AS a
        WHERE a.skill_id = r.skill_id AND lower(a.alias_label) LIKE ? ESCAPE '\\'
      )
    )`);
    const escaped = `%${searchTerm.replace(/[\\%_]/g, '\\$&')}%`;
    parameters.push(escaped, escaped);
  }
  const whereSql = clauses.join(' AND ');
  const denominator = getEligibleDenominator(db, filters);
  const rollupTable = filters.roleId ? 'api_role_skill_rollups' : 'api_scope_skill_rollups';
  const from = `${rollupTable} AS r JOIN skills AS s ON s.skill_id = r.skill_id`;
  const count = one(db, `
    SELECT COUNT(DISTINCT r.skill_id) AS count
    FROM ${from}
    WHERE ${whereSql}
  `, parameters);
  const rows = all(db, `
    SELECT r.skill_id AS skillId, MIN(s.canonical_name) AS name, MIN(s.category) AS category,
           MIN(s.match_policy) AS matchPolicy, MIN(s.review_status) AS reviewStatus,
           SUM(r.job_record_count) AS jobRecordCount
    FROM ${from}
    WHERE ${whereSql}
    GROUP BY r.skill_id
    ORDER BY jobRecordCount DESC, name COLLATE NOCASE
    LIMIT ? OFFSET ?
  `, [...parameters, pageSize, pageOffset(page, pageSize)]);
  return {
    ...makePage(rows.map((row) => ({
      skillId: row.skillId,
      name: row.name,
      category: row.category,
      matchPolicy: row.matchPolicy,
      reviewStatus: row.reviewStatus,
      jobRecordCount: Number(row.jobRecordCount),
      denominator,
      sharePercent: roundPercent(Number(row.jobRecordCount), denominator),
    })), page, pageSize, Number(count?.count || 0)),
    denominator,
    denominatorDefinition: 'Records in the selected scope with at least one eligible, reviewed skill link.',
  };
}

function getSkillCooccurrence(db, skillId, filters, limit) {
  const baseSkill = eligibleSkillById(db, skillId);
  if (!baseSkill) return null;
  const query = buildEligibleQuery(filters);
  const rows = all(db, `
    WITH eligible AS (
      SELECT js.record_id, js.skill_id, s.canonical_name, s.category
      FROM ${query.from}
      WHERE ${query.where}
    ), base_jobs AS (
      SELECT record_id FROM eligible WHERE skill_id = ?
    ), skill_totals AS (
      SELECT skill_id, canonical_name, category, COUNT(*) AS skillJobRecordCount
      FROM eligible GROUP BY skill_id, canonical_name, category
    ), cooccurrences AS (
      SELECT e.skill_id, COUNT(*) AS coOccurrenceCount
      FROM eligible AS e
      JOIN base_jobs AS b ON b.record_id = e.record_id
      WHERE e.skill_id <> ?
      GROUP BY e.skill_id
    )
    SELECT t.skill_id AS skillId, t.canonical_name AS name, t.category,
           t.skillJobRecordCount, c.coOccurrenceCount,
           (SELECT COUNT(*) FROM base_jobs) AS baseSkillJobRecordCount
    FROM cooccurrences AS c
    JOIN skill_totals AS t ON t.skill_id = c.skill_id
    ORDER BY c.coOccurrenceCount DESC, t.canonical_name COLLATE NOCASE
    LIMIT ?
  `, [...query.parameters, skillId, skillId, limit]);
  return {
    baseSkill: { skillId: baseSkill.skillId, name: baseSkill.canonicalName },
    denominatorDefinition: 'Distinct job records with at least one eligible, reviewed skill link in the selected scope.',
    measure: 'Jaccard similarity between the sets of records linked to each pair of skills.',
    skills: rows.map((row) => {
      const baseCount = Number(row.baseSkillJobRecordCount);
      const coCount = Number(row.coOccurrenceCount);
      const skillCount = Number(row.skillJobRecordCount);
      const union = baseCount + skillCount - coCount;
      return {
        skillId: row.skillId,
        name: row.name,
        category: row.category,
        baseSkillJobRecordCount: baseCount,
        otherSkillJobRecordCount: skillCount,
        coOccurrenceJobRecordCount: coCount,
        jaccard: union ? Math.round((coCount / union) * 10000) / 10000 : 0,
      };
    }),
    limitations: ['Co-occurrence is descriptive and can reflect source coverage or duplicate records; it is not a causal relation.'],
  };
}

function getResourcesForSkill(db, skillId, options) {
  const skill = eligibleSkillById(db, skillId);
  if (!skill) return null;
  const clauses = ['lrs.skill_id = ?'];
  const parameters = [skillId];
  if (options.freeOnly) clauses.push("lr.cost_status = 'free_verified'");
  if (options.language) {
    clauses.push(`EXISTS (
      SELECT 1 FROM learning_resource_languages AS lang_filter
      WHERE lang_filter.resource_id = lr.resource_id
        AND lower(trim(lang_filter.language_label)) = ?
    )`);
    parameters.push(normalizeExactLabel(options.language));
  }
  const whereSql = clauses.join(' AND ');
  const totalRow = one(db, `
    SELECT COUNT(DISTINCT lr.resource_id) AS count
    FROM learning_resources AS lr
    JOIN learning_resource_skills AS lrs ON lrs.resource_id = lr.resource_id
    WHERE ${whereSql}
  `, parameters);
  const rows = all(db, `
    SELECT lr.resource_id AS resourceId, lr.title, lr.provider,
           lr.resource_type AS resourceType, lr.level,
           lr.access_status AS accessStatus, lr.cost_status AS costStatus,
           lr.account_requirement AS accountRequirement, lr.credential,
           lr.resource_url AS resourceUrl, lr.verification_status AS verificationStatus,
           lr.verified_on AS verifiedOn, lr.notes,
           GROUP_CONCAT(DISTINCT lrl.language_label) AS languageLabels
    FROM learning_resources AS lr
    JOIN learning_resource_skills AS lrs ON lrs.resource_id = lr.resource_id
    LEFT JOIN learning_resource_languages AS lrl ON lrl.resource_id = lr.resource_id
    WHERE ${whereSql}
    GROUP BY lr.resource_id
    ORDER BY lr.title COLLATE NOCASE
    LIMIT ? OFFSET ?
  `, [...parameters, options.pageSize, pageOffset(options.page, options.pageSize)]);
  return {
    skill: { skillId: skill.skillId, name: skill.canonicalName },
    ...makePage(rows.map((row) => ({
      resourceId: row.resourceId,
      title: row.title,
      provider: row.provider,
      resourceType: row.resourceType,
      level: row.level,
      languages: row.languageLabels ? row.languageLabels.split(',').filter(Boolean) : [],
      accessStatus: row.accessStatus,
      costStatus: row.costStatus,
      accountRequirement: row.accountRequirement,
      credential: row.credential,
      resourceUrl: safeExternalUrl(row.resourceUrl),
      verificationStatus: row.verificationStatus,
      verifiedOn: row.verifiedOn,
      notes: row.notes,
      freeVerified: row.costStatus === 'free_verified',
    })), options.page, options.pageSize, Number(totalRow?.count || 0)),
    freeOnly: options.freeOnly,
    note: 'Cost and access fields are recorded per item and may be stale; only free_verified entries meet the free-only filter.',
  };
}

function getHistoricalTrends(db, filters = {}) {
  const clauses = ["r.source_dataset = 'international_jobs'"];
  const parameters = [];
  if (filters.country) {
    clauses.push('r.country_key = ?');
    parameters.push(normalizeExactLabel(filters.country));
  }
  const rows = all(db, `
    SELECT r.month, SUM(r.job_record_count) AS jobRecordCount
    FROM api_historical_month_rollups AS r
    WHERE ${clauses.join(' AND ')}
    GROUP BY r.month
    ORDER BY r.month
  `, parameters);
  return {
    metric: 'historical_job_record_count',
    sourceDataset: 'international_jobs',
    year: 2023,
    period: 'month',
    country: filters.country || null,
    denominator: rows.reduce((sum, row) => sum + Number(row.jobRecordCount), 0),
    series: rows.map((row) => ({ month: row.month, jobRecordCount: Number(row.jobRecordCount) })),
    interpretation: 'Historical distribution of explicit source posting dates in the 2023 sample; not a current-market trend or forecast.',
  };
}

function getModelStatus() {
  return roleTitleModel.getModelStatus();
}

function predictObservedRoleTitles(db, request) {
  const normalizedInputs = [];
  const seenInputs = new Set();
  for (const label of request.skills) {
    const normalized = normalizeLabel(label);
    if (seenInputs.has(normalized)) continue;
    seenInputs.add(normalized);
    normalizedInputs.push({ label: String(label).trim(), normalized });
  }

  const recognized = [];
  const unrecognized = [];
  for (const entry of normalizedInputs) {
    const candidates = all(db, `
      SELECT DISTINCT s.skill_id AS skillId, s.canonical_name AS name
      FROM skill_aliases AS a
      JOIN skills AS s ON s.skill_id = a.skill_id
      WHERE a.alias_normalized = ?
        AND a.match_policy = s.match_policy
        AND a.review_status = s.review_status
        AND (
          (a.match_policy = 'approved_aliases' AND a.review_status = 'curated'
            AND s.match_policy = 'approved_aliases' AND s.review_status = 'curated')
          OR
          (a.match_policy = 'exact_only' AND a.review_status = 'curated_exact_only'
            AND s.match_policy = 'exact_only' AND s.review_status = 'curated_exact_only')
        )
      ORDER BY s.skill_id
    `, [entry.normalized]);
    if (candidates.length === 1) {
      recognized.push({ ...candidates[0], inputLabel: entry.label });
    } else {
      unrecognized.push({
        label: entry.label,
        reason: candidates.length > 1 ? 'ambiguous_alias' : 'not_in_reviewed_skill_catalogue',
      });
    }
  }

  const recognizedById = new Map();
  for (const row of recognized) {
    if (!recognizedById.has(row.skillId)) {
      recognizedById.set(row.skillId, { skillId: row.skillId, name: row.name, inputLabels: [] });
    }
    recognizedById.get(row.skillId).inputLabels.push(row.inputLabel);
  }
  if (recognizedById.size === 0) {
    const error = new Error('No submitted skill could be resolved to a reviewed skill in the catalogue.');
    error.code = 'NO_SUPPORTED_SKILLS';
    error.statusCode = 422;
    error.safeDetails = { unrecognizedSkills: unrecognized };
    throw error;
  }

  const modelResult = roleTitleModel.predictRoleTitles([...recognizedById.values()], request.limit);
  return {
    input: {
      recognizedSkills: modelResult.recognizedSkills.map((skill) => ({
        ...skill,
        inputLabels: recognizedById.get(skill.skillId)?.inputLabels || [],
      })),
      unmodeledSkills: modelResult.unmodeledSkills,
      unrecognizedSkills: unrecognized,
    },
    ...modelResult,
  };
}

function getMethodology() {
  return {
    recordUnit: 'One retained source job-ad row (jobs.record_id); it is not guaranteed to be one unique vacancy.',
    skillEligibility: {
      pairs: [
        { policy: 'approved_aliases', reviewStatus: 'curated' },
        { policy: 'exact_only', reviewStatus: 'curated_exact_only' },
      ],
      bothLinkAndCatalogMustAgree: true,
      normalization: 'Case-fold and collapse whitespace only; no fuzzy matching.',
      excluded: ['needs_review', 'needs_owner_review', 'exclude_pending_review', 'policy/status mismatches'],
    },
    skillShare: 'Distinct records linked to a skill divided by records with at least one eligible reviewed skill, in the same cohort.',
    titleMatching: 'Case and surrounding whitespace only; title semantics, punctuation, and seniority variants remain distinct.',
    arabMarketComparison: 'Only merged_tech_jobs; Arab labels use an explicit 22-country list. The comparison cohort named other represented markets is not a full global market.',
    timeTrends: 'Only explicit posted_at values from international_jobs in 2023. source_updated_at is not treated as a posting date.',
    salaries: 'Role analysis returns field-coverage counts overall and by geographic country, including source/provenance categories. It does not return a mean or median: current salary fields do not provide a sufficient set of records with an explicit currency and a matching annual/hourly pay period, and provenance remains unverified or estimate/research-indicated.',
    matching: {
      score: 'Jaccard(U,J) = |U ∩ J| / |U ∪ J|.',
      directionalCoverage: 'User coverage = |U ∩ J| / |U|; role coverage = |U ∩ J| / |J|.',
      interpretation: 'Similarity of reviewed skill sets in collected records only; not a hiring probability.',
      inputRetention: 'Transient in-memory request processing; request bodies are not persisted or logged.',
    },
    machineLearning: {
      modelId: roleTitleModel.getModelStatus().servedModels[0].id,
      route: 'POST /api/v1/models/role-title/predict',
      method: 'Positive-evidence Bernoulli Naive Bayes with additive smoothing; score is priorWeight × log(title prior) plus log-likelihood terms for submitted skill presences.',
      target: 'Exact lower(trim(title)) strings observed in the retained sample; not a curated job-family taxonomy.',
      missingInputSkills: 'Not interpreted as absent skills or negative evidence.',
      evaluation: roleTitleModel.getModelStatus().servedModels[0].heldOutTest,
      scoreMeaning: 'Softmax-normalized relative model score over trained labels; uncalibrated and not an employment probability.',
      runtime: 'Node.js inference in the API process; Python training is offline only.',
    },
    missingness: 'Missing values mean unavailable, not zero, and are not inferred.',
    listingStatus: 'No record is confirmed active.',
    redistribution: 'Source-data redistribution rights have not been assessed; review source terms before public deployment.',
  };
}

function matchSkills(db, request) {
  const normalizedInputs = [];
  const seen = new Set();
  for (const label of request.skills) {
    const normalized = normalizeLabel(label);
    if (!seen.has(normalized)) {
      normalizedInputs.push({ label: String(label).trim(), normalized });
      seen.add(normalized);
    }
  }
  const recognized = [];
  const unrecognized = [];
  for (const entry of normalizedInputs) {
    const candidates = all(db, `
      SELECT DISTINCT s.skill_id AS skillId, s.canonical_name AS name,
             s.match_policy AS matchPolicy, s.review_status AS reviewStatus
      FROM skill_aliases AS a
      JOIN skills AS s ON s.skill_id = a.skill_id
      WHERE a.alias_normalized = ?
        AND a.match_policy = s.match_policy
        AND a.review_status = s.review_status
        AND (
          (a.match_policy = 'approved_aliases' AND a.review_status = 'curated'
            AND s.match_policy = 'approved_aliases' AND s.review_status = 'curated')
          OR
          (a.match_policy = 'exact_only' AND a.review_status = 'curated_exact_only'
            AND s.match_policy = 'exact_only' AND s.review_status = 'curated_exact_only')
        )
      ORDER BY s.skill_id
    `, [entry.normalized]);
    if (candidates.length === 1) {
      recognized.push({ ...candidates[0], inputLabel: entry.label });
    } else {
      unrecognized.push({
        label: entry.label,
        reason: candidates.length > 1 ? 'ambiguous_alias' : 'not_in_reviewed_skill_catalogue',
      });
    }
  }
  const recognizedById = new Map();
  for (const row of recognized) {
    const current = recognizedById.get(row.skillId) || {
      skillId: row.skillId,
      name: row.name,
      inputLabels: [],
    };
    current.inputLabels.push(row.inputLabel);
    recognizedById.set(row.skillId, current);
  }
  const recognizedUnique = [...recognizedById.values()];
  const distinctSkillIds = recognizedUnique.map((row) => row.skillId);
  if (distinctSkillIds.length === 0) {
    const error = new Error('No submitted skill could be resolved to a reviewed skill in the catalogue.');
    error.code = 'NO_SUPPORTED_SKILLS';
    error.statusCode = 422;
    error.safeDetails = { unrecognizedSkills: unrecognized };
    throw error;
  }
  const filters = {
    sourceDataset: request.sourceDataset,
    country: request.country,
    workMode: request.workMode,
  };
  const roleFilters = rollupWhere(filters);
  const inputSkillValues = distinctSkillIds.map(() => '(?)').join(', ');
  const roleRows = all(db, `
    WITH input_skills(skill_id) AS (VALUES ${inputSkillValues}),
    candidate_roles AS MATERIALIZED (
      SELECT DISTINCT r.role_id AS roleId
      FROM api_role_skill_rollups AS r
      JOIN input_skills AS i ON i.skill_id = r.skill_id
      WHERE ${roleFilters.sql}
        AND r.role_id <> ''
    ), role_skill_stats AS (
      SELECT r.role_id AS roleId,
             COUNT(DISTINCT r.skill_id) AS roleSkillCount,
             COUNT(DISTINCT i.skill_id) AS matchedSkillCount
      FROM candidate_roles AS c
      CROSS JOIN api_role_skill_rollups AS r
      LEFT JOIN input_skills AS i ON i.skill_id = r.skill_id
      WHERE r.role_id = c.roleId
        AND ${roleFilters.sql}
      GROUP BY r.role_id
    ), role_totals AS (
      SELECT r.role_id AS roleId,
             MIN(r.role_display_title) AS displayTitle,
             SUM(r.eligible_job_record_count) AS recordsWithEligibleSkills
      FROM candidate_roles AS c
      CROSS JOIN api_role_scope_rollups AS r
      WHERE r.role_id = c.roleId
        AND ${roleFilters.sql}
      GROUP BY r.role_id
    ), ranked_roles AS (
      SELECT s.roleId, t.displayTitle, t.recordsWithEligibleSkills,
             s.roleSkillCount, s.matchedSkillCount
      FROM role_skill_stats AS s
      JOIN role_totals AS t ON t.roleId = s.roleId
    )
    SELECT roleId, displayTitle, recordsWithEligibleSkills, roleSkillCount,
           matchedSkillCount,
           CASE WHEN roleSkillCount + (SELECT COUNT(*) FROM input_skills) - matchedSkillCount = 0
             THEN 0.0
             ELSE CAST(matchedSkillCount AS REAL) /
               (roleSkillCount + (SELECT COUNT(*) FROM input_skills) - matchedSkillCount)
           END AS score,
           COUNT(*) OVER () AS totalCandidates
    FROM ranked_roles
    ORDER BY score DESC, matchedSkillCount DESC,
             recordsWithEligibleSkills DESC, roleId
    LIMIT ?
  `, [
    ...distinctSkillIds,
    ...roleFilters.parameters,
    ...roleFilters.parameters,
    ...roleFilters.parameters,
    request.limit,
  ]);
  const profiles = new Map(roleRows.map((row) => [row.roleId, {
    roleId: row.roleId,
    displayTitle: row.displayTitle,
    recordsWithEligibleSkills: Number(row.recordsWithEligibleSkills),
    roleSkillCount: Number(row.roleSkillCount),
    matchedSkillCount: Number(row.matchedSkillCount),
    skills: [],
  }]));
  const selectedRoleIds = [...profiles.keys()];
  if (selectedRoleIds.length) {
    const rolePlaceholders = selectedRoleIds.map(() => '?').join(', ');
    const skillRows = all(db, `
      SELECT r.role_id AS roleId, r.skill_id AS skillId,
             MIN(r.canonical_name) AS name, MIN(r.category) AS category,
             SUM(r.job_record_count) AS jobRecordCount
      FROM api_role_skill_rollups AS r
      WHERE r.role_id IN (${rolePlaceholders})
        AND ${roleFilters.sql}
      GROUP BY r.role_id, r.skill_id
      ORDER BY r.role_id, jobRecordCount DESC, name COLLATE NOCASE
    `, [...selectedRoleIds, ...roleFilters.parameters]);
    for (const row of skillRows) {
      profiles.get(row.roleId).skills.push({
        skillId: row.skillId,
        name: row.name,
        category: row.category,
        jobRecordCount: Number(row.jobRecordCount),
      });
    }
  }
  const userSet = new Set(distinctSkillIds);
  const results = [...profiles.values()].map((profile) => {
    const candidateSet = new Set(profile.skills.map((skill) => skill.skillId));
    const matched = profile.skills.filter((skill) => userSet.has(skill.skillId));
    const missing = profile.skills.filter((skill) => !userSet.has(skill.skillId));
    const userOnly = recognizedUnique.filter((skill) => !candidateSet.has(skill.skillId));
    const unionCount = userSet.size + candidateSet.size - matched.length;
    const score = unionCount ? matched.length / unionCount : 0;
    const roleSkillCount = candidateSet.size;
    return {
      roleId: profile.roleId,
      displayTitle: profile.displayTitle,
      scoreName: 'jaccard_skill_overlap',
      score: Math.round(score * 10000) / 10000,
      scorePercent: roundPercent(matched.length, unionCount),
      matchedSkills: matched.map(({ skillId, name }) => ({ skillId, name })),
      missingSkills: missing.slice(0, 10),
      userOnlySkills: userOnly.map(({ skillId, name }) => ({ skillId, name })),
      userSkillCoverage: userSet.size ? matched.length / userSet.size : 0,
      roleSkillCoverage: roleSkillCount ? matched.length / roleSkillCount : 0,
      userSkillCount: userSet.size,
      roleSkillCount,
      matchedSkillCount: matched.length,
      evidence: {
        recordsWithEligibleSkills: profile.recordsWithEligibleSkills,
        roleSkillProfile: 'Distinct reviewed skills observed in the selected source/country/work-mode scope.',
        missingSkillsRankedBy: 'Number of role records with an eligible association; not a required-skill certainty.',
      },
    };
  }).sort((left, right) => right.score - left.score
    || right.matchedSkillCount - left.matchedSkillCount
    || right.evidence.recordsWithEligibleSkills - left.evidence.recordsWithEligibleSkills
    || left.roleId.localeCompare(right.roleId));
  return {
    input: {
      recognizedSkills: recognizedUnique,
      unrecognizedSkills: unrecognized,
      filters: {
        sourceDataset: filters.sourceDataset || null,
        country: filters.country || null,
        workModeRaw: filters.workMode || null,
      },
    },
    results: results.slice(0, request.limit),
    pagination: { limit: request.limit, totalCandidates: Number(roleRows[0]?.totalCandidates || 0) },
    algorithm: {
      id: 'jaccard_skill_overlap',
      type: 'deterministic_similarity_baseline',
      trainedModel: false,
      definition: '|user skills ∩ role skills| / |user skills ∪ role skills|',
    },
    warning: 'This score is skill overlap in the collected records, not a hiring probability, guarantee, or complete suitability assessment.',
  };
}

module.exports = {
  ARAB_COUNTRIES,
  NON_GEOGRAPHIC_COUNTRIES,
  ELIGIBLE_SKILL_POLICY_SQL,
  all,
  one,
  normalizeLabel,
  normalizeExactLabel,
  roundPercent,
  makePage,
  jobWhere,
  eligibleSkillById,
  getEligibleDenominator,
  getMarketComparison,
  getOverview,
  getSnapshot,
  getDatabaseHealth,
  getMetadata,
  formatJob,
  getJobs,
  getJobById,
  getRoles,
  getRoleAnalysis,
  getSkills,
  getSkillCooccurrence,
  getResourcesForSkill,
  getHistoricalTrends,
  getModelStatus,
  getMethodology,
  predictObservedRoleTitles,
  matchSkills,
};
