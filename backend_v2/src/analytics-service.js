import { AnalyticsRepository, SALARY_FIELDS } from './analytics-repository.js';
import { MemoryCache } from './cache.js';
import { normalizeKey, safePercentage } from './normalize.js';
import { notFound } from './errors.js';

function number(value) {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function count(value) {
  return Number(value ?? 0);
}

function salaryFor(row, currency) {
  const prefix = currency.toLowerCase();
  const records = count(row[`${prefix}_salary_records`]);
  if (records === 0) return { currency, period: 'annual', records: 0, mean: null, range: null };
  return {
    currency,
    period: 'annual',
    records,
    mean: number(row[`${prefix}_mean_annual`]),
    range: {
      minimum: number(row[`${prefix}_range_min`]),
      maximum: number(row[`${prefix}_range_max`]),
    },
    averageAdvertisedLowerBound: number(row[`${prefix}_mean_lower_bound`]),
    averageAdvertisedUpperBound: number(row[`${prefix}_mean_upper_bound`]),
    estimateStatusCounts: {
      estimated: count(row[`${prefix}_estimated_records`]),
      actual: count(row[`${prefix}_actual_records`]),
      unverified: count(row[`${prefix}_unverified_records`]),
    },
  };
}

function percentageRows(rows, countKey, denominator, outputKey = 'sharePct') {
  return rows.map((row) => ({
    ...row,
    [countKey]: count(row[countKey]),
    [outputKey]: safePercentage(row[countKey], denominator),
  }));
}

function workModeLabel(mode) {
  const labels = {
    remote: 'Remote',
    not_remote_explicit: 'Non-remote (not explicitly marked remote; not proof of onsite)',
    hybrid: 'Hybrid',
    unknown_or_unmapped: 'Unknown / unmapped',
  };
  return labels[mode] || mode || 'Unknown / unmapped';
}

export class AnalyticsService {
  constructor(database, { cacheTtlMs = 30_000, maxApiLimit = 100 } = {}) {
    this.repository = new AnalyticsRepository(database);
    this.cache = new MemoryCache({ ttlMs: cacheTtlMs, maxEntries: 80 });
    this.maxApiLimit = maxApiLimit;
  }

  overview() {
    return this.cache.getOrSet('analytics:overview', () => {
      const result = this.repository.getOverview();
      return {
        ...result,
        generatedAt: new Date().toISOString(),
        salaryBasis: 'Annual estimate/actual fields already present in the NADA database; amounts are kept in their stated reporting currency.',
      };
    });
  }

  searchRoles(query = '', limit = 25) {
    const safeLimit = Math.min(Math.max(Number(limit) || 25, 1), this.maxApiLimit);
    const normalizedQuery = normalizeKey(query);
    const cacheKey = `roles:${normalizedQuery}:${safeLimit}`;
    return this.cache.getOrSet(cacheKey, () => this.repository.searchRoles(normalizedQuery, safeLimit).map((row) => ({
      roleKey: row.role_key,
      title: row.title,
      advertisementCount: count(row.advertisement_count),
    })));
  }

  roleReport(role) {
    const roleKey = normalizeKey(role);
    if (!roleKey) throw notFound('Provide a non-empty role title.');
    return this.cache.getOrSet(`role:${roleKey}`, () => {
      const core = this.repository.getRole(roleKey);
      if (!core) throw notFound(`No advertisements were found for role title "${role}".`);

      const totalAds = count(core.advertisement_count);
      const countryTotals = new Map(this.repository.getCountryTotals().map((row) => [
        row.country_key,
        count(row.total_advertisements),
      ]));
      const countryRows = this.repository.getRoleCountries(roleKey).map((row) => {
        const roleAds = count(row.role_advertisements);
        const allCountryAds = countryTotals.get(row.country_key) || 0;
        return {
          country: row.country_key === '[unknown]' ? 'Unknown / not specified' : row.country_key,
          roleAdvertisements: roleAds,
          totalAdvertisementsInCountry: allCountryAds,
          roleShareOfItsAdvertisementsPct: safePercentage(roleAds, totalAds),
          roleDemandWithinCountryPct: safePercentage(roleAds, allCountryAds),
        };
      });

      const salaryByCountry = this.repository.getRoleSalary(roleKey).map((row) => ({
        country: row.country_key === '[unknown]' ? 'Unknown / not specified' : row.country_key,
        roleAdvertisements: count(row.role_advertisements),
        currencies: Object.keys(SALARY_FIELDS).map((currency) => salaryFor(row, currency)),
      }));

      const skills = this.repository.getRoleSkills(roleKey, this.maxApiLimit).map((row) => ({
        skillId: row.skill_id,
        skill: row.skill,
        category: row.category,
        advertisementCount: count(row.advertisement_count),
        appearancePctOfRoleAds: safePercentage(row.advertisement_count, totalAds),
      }));
      const combinations = this.repository.getRoleSkillCombinations(
        roleKey,
        skills.slice(0, 30).map((item) => item.skillId),
        Math.min(30, this.maxApiLimit),
      ).map((row) => ({
        firstSkill: row.first_skill,
        secondSkill: row.second_skill,
        cooccurrenceAdvertisements: count(row.cooccurrence_count),
        cooccurrencePctOfRoleAds: safePercentage(row.cooccurrence_count, totalAds),
      }));
      const workModeRows = this.repository.getWorkModes(roleKey).map((row) => ({
        mode: row.mode,
        label: workModeLabel(row.mode),
        advertisementCount: count(row.advertisement_count),
        percentageOfRoleAds: safePercentage(row.advertisement_count, totalAds),
      }));
      const familyRows = this.repository.getRoleFamilyDistribution(roleKey).map((row) => ({
        family: row.family,
        advertisementCount: count(row.advertisement_count),
        percentageOfRoleAds: safePercentage(row.advertisement_count, totalAds),
      }));

      return {
        role: { key: core.role_key, title: core.title },
        advertisementCount: totalAds,
        sourceCount: count(core.source_count),
        roleFamilyLabelsPresent: count(core.labeled_advertisements),
        countryDemand: countryRows,
        mostDemandCountries: countryRows.slice(0, 10),
        skills,
        technologyCombinations: combinations,
        annualSalaryByCountry: salaryByCountry,
        workMode: {
          denominatorAdvertisements: totalAds,
          categories: workModeRows,
          remotePct: workModeRows.find((item) => item.mode === 'remote')?.percentageOfRoleAds ?? 0,
          nonRemotePct: workModeRows.find((item) => item.mode === 'not_remote_explicit')?.percentageOfRoleAds ?? 0,
          hybridPct: workModeRows.find((item) => item.mode === 'hybrid')?.percentageOfRoleAds ?? 0,
          unknownPct: workModeRows.find((item) => item.mode === 'unknown_or_unmapped')?.percentageOfRoleAds ?? 0,
          interpretation: 'Non-remote means the database did not classify the advertisement as remote; it is not proof that the work is onsite.',
        },
        storedFamilyLabelDistribution: familyRows,
        charts: {
          countryDemand: { type: 'bar', unit: 'advertisements', labels: countryRows.map((item) => item.country), values: countryRows.map((item) => item.roleAdvertisements) },
          skillDemand: { type: 'bar', unit: 'advertisements', labels: skills.slice(0, 15).map((item) => item.skill), values: skills.slice(0, 15).map((item) => item.advertisementCount) },
          salary: Object.fromEntries(Object.keys(SALARY_FIELDS).map((currency) => [
            currency,
            { type: 'range', unit: `annual ${currency}`, labels: salaryByCountry.map((item) => item.country), means: salaryByCountry.map((item) => item.currencies.find((entry) => entry.currency === currency)?.mean ?? null), minimums: salaryByCountry.map((item) => item.currencies.find((entry) => entry.currency === currency)?.range?.minimum ?? null), maximums: salaryByCountry.map((item) => item.currencies.find((entry) => entry.currency === currency)?.range?.maximum ?? null) },
          ])),
          workMode: { type: 'bar', unit: 'advertisements', labels: workModeRows.map((item) => item.label), values: workModeRows.map((item) => item.advertisementCount) },
          technologyCombinations: { type: 'bar', unit: 'co-occurring advertisements', labels: combinations.map((item) => `${item.firstSkill} + ${item.secondSkill}`), values: combinations.map((item) => item.cooccurrenceAdvertisements) },
        },
      };
    });
  }

  globalSkills(limit = 25) {
    const safeLimit = Math.min(Math.max(Number(limit) || 25, 1), this.maxApiLimit);
    return this.cache.getOrSet(`skills:global:${safeLimit}`, () => {
      const denominator = this.overview().totalJobs;
      const rows = this.repository.getGlobalSkills(safeLimit).map((row) => ({
        skillId: row.skill_id,
        skill: row.skill,
        category: row.category,
        advertisementCount: count(row.advertisement_count),
        appearancePctOfAllAds: safePercentage(row.advertisement_count, denominator),
      }));
      return { denominatorAdvertisements: denominator, skills: rows };
    });
  }

  workMode(role = '') {
    const roleKey = normalizeKey(role);
    const total = roleKey ? this.repository.getRole(roleKey)?.advertisement_count : this.overview().totalJobs;
    if (roleKey && total === undefined) throw notFound(`No advertisements were found for role title "${role}".`);
    const categories = this.repository.getWorkModes(roleKey || null).map((row) => ({
      mode: row.mode,
      label: workModeLabel(row.mode),
      advertisementCount: count(row.advertisement_count),
      percentage: safePercentage(row.advertisement_count, total),
    }));
    return {
      role: roleKey ? { key: roleKey, title: this.repository.getRole(roleKey).title } : null,
      denominatorAdvertisements: count(total),
      categories,
      remotePct: categories.find((item) => item.mode === 'remote')?.percentage ?? 0,
      nonRemotePct: categories.find((item) => item.mode === 'not_remote_explicit')?.percentage ?? 0,
      hybridPct: categories.find((item) => item.mode === 'hybrid')?.percentage ?? 0,
      unknownPct: categories.find((item) => item.mode === 'unknown_or_unmapped')?.percentage ?? 0,
      interpretation: 'Non-remote means not explicitly classified as remote. It must not be described as confirmed onsite.',
    };
  }

  arabVsInternational(limit = 15) {
    const safeLimit = Math.min(Math.max(Number(limit) || 15, 1), this.maxApiLimit);
    return this.cache.getOrSet(`markets:arab-international:${safeLimit}`, () => {
      const counts = this.repository.getMarketCounts().map((row) => ({
        market: row.market,
        advertisementCount: count(row.advertisement_count),
        distinctRoles: count(row.distinct_roles),
      }));
      const marketCounts = new Map(counts.map((item) => [item.market, item.advertisementCount]));
      const salaries = this.repository.getMarketSalary().map((row) => ({
        market: row.market,
        currencies: Object.keys(SALARY_FIELDS).map((currency) => salaryFor(row, currency)),
      }));
      const skillRows = this.repository.getMarketSkills(safeLimit).map((row) => ({
        market: row.market,
        skillId: row.skill_id,
        skill: row.skill,
        advertisementCount: count(row.advertisement_count),
        appearancePctOfMarketAds: safePercentage(row.advertisement_count, marketCounts.get(row.market) || 0),
      }));
      const topRoles = this.repository.getMarketTopRoles(Math.min(safeLimit, 20)).map((row) => ({
        market: row.market,
        roleKey: row.role_key,
        title: row.title,
        advertisementCount: count(row.advertisement_count),
      }));
      return {
        counts,
        salaries,
        topSkillsByMarket: skillRows,
        topRolesByMarket: topRoles,
        marketDefinitions: {
          arab: 'Country labels in the configured 22 Arab-state list plus common UAE/KSA aliases.',
          international: 'Rows with a non-empty country label not mapped to the Arab-state list or a non-country scope.',
          unknown: 'Blank, worldwide, remote-anywhere, or otherwise non-country location labels.',
        },
        salaryBasis: 'All populated annual USD/EGP/SAR columns in the NADA database; status counts remain visible and currency columns are never combined.',
        charts: {
          advertisementCounts: { type: 'bar', unit: 'advertisements', labels: counts.map((item) => item.market), values: counts.map((item) => item.advertisementCount) },
          skills: Object.fromEntries(['arab', 'international'].map((market) => {
            const rows = skillRows.filter((item) => item.market === market);
            return [market, { type: 'bar', unit: 'advertisements', labels: rows.map((item) => item.skill), values: rows.map((item) => item.advertisementCount) }];
          })),
          salaries: Object.fromEntries(Object.keys(SALARY_FIELDS).map((currency) => [
            currency,
            { type: 'bar', unit: `annual ${currency}`, labels: salaries.filter((item) => item.market !== 'unknown').map((item) => item.market), values: salaries.filter((item) => item.market !== 'unknown').map((item) => item.currencies.find((entry) => entry.currency === currency)?.mean ?? null) },
          ])),
        },
      };
    });
  }

  dashboardData() {
    return this.cache.getOrSet('dashboard:data', () => {
      const overview = this.overview();
      const roles = this.searchRoles('', 12);
      const countries = this.repository.getCountryDistribution(12).map((row) => ({
        country: row.country_key === '[unknown]' ? 'Unknown / not specified' : row.country_key,
        advertisementCount: count(row.advertisement_count),
      }));
      const skills = this.globalSkills(15).skills;
      const markets = this.arabVsInternational(10);
      const workModes = this.workMode();
      return {
        generatedAt: new Date().toISOString(),
        overview,
        topRoles: roles,
        topCountries: countries,
        topSkills: skills,
        marketComparison: markets,
        workModes,
        charts: {
          roles: { type: 'bar', unit: 'advertisements', labels: roles.map((item) => item.title), values: roles.map((item) => item.advertisementCount) },
          countries: { type: 'bar', unit: 'advertisements', labels: countries.map((item) => item.country), values: countries.map((item) => item.advertisementCount) },
          skills: { type: 'bar', unit: 'advertisements', labels: skills.map((item) => item.skill), values: skills.map((item) => item.advertisementCount) },
          workModes: { type: 'bar', unit: 'advertisements', labels: workModes.categories.map((item) => item.label), values: workModes.categories.map((item) => item.advertisementCount) },
          marketAds: markets.charts.advertisementCounts,
        },
      };
    });
  }
}
