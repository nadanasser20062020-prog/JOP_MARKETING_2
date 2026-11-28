import { normalizeKey, safePercentage } from './normalize.js';
import { badRequest } from './errors.js';

const MAX_INPUT_SKILLS = 40;
const MAX_AD_LIMIT = 20;
const MAX_PROFILE_LIMIT = 20;

function placeholders(values) {
  return values.map(() => '?').join(', ');
}

function toCount(value) {
  return Number(value ?? 0);
}

function workModeFilter(value) {
  if (!value) return null;
  const normalized = normalizeKey(value).replaceAll('-', '_').replaceAll(' ', '_');
  const aliases = {
    remote: 'remote',
    hybrid: 'hybrid',
    onsite: 'not_remote_explicit',
    'on_site': 'not_remote_explicit',
    non_remote: 'not_remote_explicit',
    not_remote: 'not_remote_explicit',
    not_remote_explicit: 'not_remote_explicit',
    unknown: 'unknown_or_unmapped',
    unknown_or_unmapped: 'unknown_or_unmapped',
  };
  const mapped = aliases[normalized];
  if (!mapped) throw badRequest('workMode must be remote, hybrid, non_remote, or unknown.');
  return mapped;
}

export class SkillMatchingService {
  constructor(database) {
    this.database = database;
  }

  resolveSkills(inputSkills) {
    if (!Array.isArray(inputSkills) || inputSkills.length === 0) {
      throw badRequest('skills must be a non-empty array of skill names or skill IDs.');
    }
    if (inputSkills.length > MAX_INPUT_SKILLS) {
      throw badRequest(`Provide no more than ${MAX_INPUT_SKILLS} skills per request.`);
    }
    const unique = [...new Set(inputSkills.map((skill) => String(skill ?? '').trim()).filter(Boolean))];
    if (unique.length === 0) throw badRequest('skills must contain at least one non-empty value.');

    const known = new Map();
    const unknownSkills = [];
    const ambiguousSkills = [];
    for (const raw of unique) {
      const normalized = normalizeKey(raw);
      if (!normalized) continue;

      const byId = this.database.get(
        'SELECT skill_id, canonical_name FROM skills WHERE skill_id = ?',
        raw,
      );
      if (byId) {
        known.set(byId.skill_id, byId.canonical_name);
        continue;
      }

      const aliasRows = this.database.all(`
        SELECT DISTINCT a.skill_id, s.canonical_name
        FROM skill_aliases AS a
        JOIN skills AS s ON s.skill_id = a.skill_id
        WHERE a.alias_normalized = ? COLLATE NOCASE
        ORDER BY a.skill_id`, normalized);
      if (aliasRows.length === 1) {
        known.set(aliasRows[0].skill_id, aliasRows[0].canonical_name);
        continue;
      }
      if (aliasRows.length > 1) {
        ambiguousSkills.push({ input: raw, choices: aliasRows.map((row) => ({ skillId: row.skill_id, skill: row.canonical_name })) });
        continue;
      }

      const canonicalRows = this.database.all(`
        SELECT skill_id, canonical_name
        FROM skills
        WHERE canonical_name = ? COLLATE NOCASE
        ORDER BY skill_id`, raw.trim());
      if (canonicalRows.length === 1) {
        known.set(canonicalRows[0].skill_id, canonicalRows[0].canonical_name);
      } else if (canonicalRows.length > 1) {
        ambiguousSkills.push({ input: raw, choices: canonicalRows.map((row) => ({ skillId: row.skill_id, skill: row.canonical_name })) });
      } else {
        unknownSkills.push(raw);
      }
    }
    return { skills: [...known].map(([skillId, skill]) => ({ skillId, skill })), unknownSkills, ambiguousSkills };
  }

  #filters(options, params) {
    const clauses = [];
    if (options.country) {
      clauses.push('LOWER(TRIM(COALESCE(a.country_standardized, \'\'))) = ?');
      params.push(normalizeKey(options.country));
    }
    if (options.workMode) {
      clauses.push('LOWER(TRIM(COALESCE(a.work_mode_standardized, \'unknown_or_unmapped\'))) = ?');
      params.push(workModeFilter(options.workMode));
    }
    if (options.roleFamily) {
      clauses.push('LOWER(TRIM(COALESCE(a.role_family, \'\'))) = ?');
      params.push(normalizeKey(options.roleFamily));
    }
    return clauses.length ? ` AND ${clauses.join(' AND ')}` : '';
  }

  #matchingAds(skillIds, options, limit) {
    const skillMarks = placeholders(skillIds);
    const params = [...skillIds];
    const filterClause = this.#filters(options, params);
    params.push(limit);
    return this.database.all(`
      SELECT a.record_id, a.title_clean AS title, a.title_key AS role_key,
             COALESCE(NULLIF(TRIM(a.country_standardized), ''), 'Unknown / not specified') AS country,
             COALESCE(NULLIF(TRIM(a.work_mode_standardized), ''), 'unknown_or_unmapped') AS work_mode,
             a.source_dataset,
             COUNT(DISTINCT js.skill_id) AS matched_skill_count
      FROM job_skills AS js
      JOIN job_cleaning_audit AS a ON a.record_id = js.record_id
      WHERE js.skill_id IN (${skillMarks})${filterClause}
      GROUP BY a.record_id
      ORDER BY matched_skill_count DESC, a.title_key ASC, a.record_id ASC
      LIMIT ?`, ...params);
  }

  #profileCandidates(skillIds, options, limit) {
    const skillMarks = placeholders(skillIds);
    const params = [...skillIds];
    const filterClause = this.#filters(options, params);
    params.push(limit);
    return this.database.all(`
      SELECT a.title_key AS role_key,
             MIN(a.title_clean) AS title,
             COUNT(DISTINCT js.skill_id) AS matched_user_skill_count,
             COUNT(DISTINCT a.record_id) AS matching_advertisement_count
      FROM job_skills AS js
      JOIN job_cleaning_audit AS a ON a.record_id = js.record_id
      WHERE js.skill_id IN (${skillMarks})${filterClause}
        AND a.title_key IS NOT NULL AND a.title_key <> ''
      GROUP BY a.title_key
      ORDER BY matched_user_skill_count DESC, matching_advertisement_count DESC, a.title_key ASC
      LIMIT ?`, ...params);
  }

  #profileSkills(roleKey, options, limit) {
    const params = [roleKey];
    const clauses = [];
    if (options.country) {
      clauses.push('LOWER(TRIM(COALESCE(a.country_standardized, \'\'))) = ?');
      params.push(normalizeKey(options.country));
    }
    if (options.workMode) {
      clauses.push('LOWER(TRIM(COALESCE(a.work_mode_standardized, \'unknown_or_unmapped\'))) = ?');
      params.push(workModeFilter(options.workMode));
    }
    if (options.roleFamily) {
      clauses.push('LOWER(TRIM(COALESCE(a.role_family, \'\'))) = ?');
      params.push(normalizeKey(options.roleFamily));
    }
    params.push(limit);
    return this.database.all(`
      SELECT js.skill_id,
             COALESCE(NULLIF(MAX(s.canonical_name), ''), CAST(js.skill_id AS TEXT)) AS skill,
             COUNT(*) AS advertisement_count
      FROM job_cleaning_audit AS a
      JOIN job_skills AS js ON js.record_id = a.record_id
      LEFT JOIN skills AS s ON s.skill_id = js.skill_id
      WHERE a.title_key = ?${clauses.length ? ` AND ${clauses.join(' AND ')}` : ''}
      GROUP BY js.skill_id
      ORDER BY advertisement_count DESC, skill COLLATE NOCASE ASC
      LIMIT ?`, ...params);
  }

  #skillsForAds(recordIds) {
    if (!recordIds.length) return new Map();
    const marks = placeholders(recordIds);
    const result = new Map(recordIds.map((id) => [id, []]));
    for (const row of this.database.all(`
      SELECT js.record_id, js.skill_id,
             COALESCE(NULLIF(s.canonical_name, ''), CAST(js.skill_id AS TEXT)) AS skill
      FROM job_skills AS js
      LEFT JOIN skills AS s ON s.skill_id = js.skill_id
      WHERE js.record_id IN (${marks})
      ORDER BY js.record_id, skill COLLATE NOCASE`, ...recordIds)) {
      result.get(row.record_id)?.push({ skillId: row.skill_id, skill: row.skill });
    }
    return result;
  }

  match({ skills: inputSkills, country = '', workMode = '', roleFamily = '', limit = 10 } = {}) {
    const resolved = this.resolveSkills(inputSkills);
    const options = {
      country: String(country || '').trim(),
      workMode: workMode ? String(workMode).trim() : '',
      roleFamily: String(roleFamily || '').trim(),
    };
    const safeAdLimit = Math.min(Math.max(Number(limit) || 10, 1), MAX_AD_LIMIT);
    const safeProfileLimit = Math.min(safeAdLimit, MAX_PROFILE_LIMIT);
    const requested = resolved.skills;
    if (requested.length === 0) {
      return {
        scoringMethod: 'matched_user_skills / submitted_user_skills',
        hiringProbability: false,
        inputSkillCount: 0,
        matchedCanonicalSkills: [],
        unknownSkills: resolved.unknownSkills,
        ambiguousSkills: resolved.ambiguousSkills,
        advertisements: [],
        roleProfiles: [],
        message: 'No submitted skill resolved to a database skill ID; use an exact canonical skill or a listed alias.',
      };
    }

    const skillIds = requested.map((skill) => skill.skillId);
    const userIds = new Set(skillIds);
    const adRows = this.#matchingAds(skillIds, options, safeAdLimit);
    const adSkills = this.#skillsForAds(adRows.map((row) => row.record_id));
    const advertisements = adRows.map((row) => {
      const required = adSkills.get(row.record_id) || [];
      const matched = required.filter((item) => userIds.has(item.skillId));
      const missing = required.filter((item) => !userIds.has(item.skillId));
      return {
        advertisementId: row.record_id,
        title: row.title,
        roleKey: row.role_key,
        country: row.country,
        workMode: row.work_mode,
        sourceDataset: row.source_dataset,
        matchedSkills: matched,
        missingSkills: missing,
        userSkillCoveragePct: safePercentage(matched.length, requested.length),
        advertisementSkillCoveragePct: safePercentage(matched.length, required.length),
        matchedSkillCount: matched.length,
        requiredSkillCount: required.length,
      };
    });

    const profiles = this.#profileCandidates(skillIds, options, safeProfileLimit).map((row) => {
      const profileSkills = this.#profileSkills(row.role_key, options, 100);
      const profileSkillIds = new Set(profileSkills.map((item) => item.skill_id));
      const matched = requested.filter((item) => profileSkillIds.has(item.skillId));
      const missingCommon = profileSkills
        .filter((item) => !userIds.has(item.skill_id))
        .slice(0, 10)
        .map((item) => ({
          skillId: item.skill_id,
          skill: item.skill,
          advertisementCount: toCount(item.advertisement_count),
        }));
      const profileAdCount = profileSkills.length
        ? Number(this.database.get(`
            SELECT COUNT(DISTINCT a.record_id) AS n
            FROM job_cleaning_audit AS a
            WHERE a.title_key = ?${this.#profileFilterSql(options)}`, row.role_key, ...this.#profileFilterParams(options))?.n ?? 0)
        : 0;
      return {
        roleKey: row.role_key,
        title: row.title,
        matchingAdvertisementCount: toCount(row.matching_advertisement_count),
        profileAdvertisementCount: profileAdCount,
        matchedUserSkills: matched,
        missingCommonSkills: missingCommon,
        userSkillCoveragePct: safePercentage(matched.length, requested.length),
        scoreExplanation: 'Percentage of submitted user skills found in the role profile; missing skills are the most common remaining skills in that profile.',
      };
    });

    return {
      scoringMethod: 'matched_user_skills / submitted_user_skills; no probability calibration',
      hiringProbability: false,
      userSuitabilityJudgement: false,
      inputSkillCount: requested.length,
      matchedCanonicalSkills: requested,
      unknownSkills: resolved.unknownSkills,
      ambiguousSkills: resolved.ambiguousSkills,
      filters: options,
      advertisements,
      roleProfiles: profiles,
      limitations: [
        'Coverage is a transparent overlap score, not a hiring probability or a complete measure of candidate suitability.',
        'Missing-skill suggestions are the most frequent skills in matching database role profiles; they are not personalized learning recommendations.',
      ],
    };
  }

  #profileFilterSql(options) {
    const clauses = [];
    if (options.country) clauses.push('LOWER(TRIM(COALESCE(a.country_standardized, \'\'))) = ?');
    if (options.workMode) clauses.push('LOWER(TRIM(COALESCE(a.work_mode_standardized, \'unknown_or_unmapped\'))) = ?');
    if (options.roleFamily) clauses.push('LOWER(TRIM(COALESCE(a.role_family, \'\'))) = ?');
    return clauses.length ? ` AND ${clauses.join(' AND ')}` : '';
  }

  #profileFilterParams(options) {
    const params = [];
    if (options.country) params.push(normalizeKey(options.country));
    if (options.workMode) params.push(workModeFilter(options.workMode));
    if (options.roleFamily) params.push(normalizeKey(options.roleFamily));
    return params;
  }
}
