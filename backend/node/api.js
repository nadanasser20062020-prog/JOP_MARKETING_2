'use strict';

const { randomUUID } = require('node:crypto');
const { app_url, app_origin } = require('../config/app_url');
const { getDatabase } = require('./database');
const queries = require('./queries');

const JSON_BODY_LIMIT_BYTES = 32 * 1024;
const MAX_PAGE_SIZE = 100;

class ApiError extends Error {
  constructor(statusCode, code, message, safeDetails) {
    super(message);
    this.statusCode = statusCode;
    this.code = code;
    this.safeDetails = safeDetails;
  }
}

function requestIdFor(request) {
  const candidate = String(request.headers?.['x-request-id'] || '').trim();
  return /^[A-Za-z0-9._-]{1,64}$/.test(candidate) ? candidate : randomUUID();
}

function appendVaryHeader(response, value) {
  const current = String(response.getHeader?.('Vary') || '').split(',').map((part) => part.trim()).filter(Boolean);
  if (!current.includes(value)) current.push(value);
  response.setHeader('Vary', current.join(', '));
}

function setResponseHeaders(request, response, requestId, configuredAppOrigin) {
  response.setHeader('Content-Type', 'application/json; charset=utf-8');
  response.setHeader('X-Content-Type-Options', 'nosniff');
  response.setHeader('Cache-Control', 'no-store');
  response.setHeader('X-Request-Id', requestId);
  const origin = request.headers?.origin;
  if (origin && origin === configuredAppOrigin) {
    response.setHeader('Access-Control-Allow-Origin', configuredAppOrigin);
    appendVaryHeader(response, 'Origin');
  }
  if (String(request.method || '').toUpperCase() === 'OPTIONS') {
    response.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    response.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Request-Id');
    response.setHeader('Access-Control-Max-Age', '600');
  }
}

function sendJson(response, statusCode, payload) {
  if (response.writableEnded) return;
  response.statusCode = statusCode;
  response.end(JSON.stringify(payload));
}

function successPayload(data, requestId, db = null) {
  return {
    data,
    meta: {
      apiVersion: 'v1',
      requestId,
      snapshot: db ? queries.getSnapshot(db) : null,
      servedAt: new Date().toISOString(),
    },
  };
}

function parseRequestUrl(request, baseUrl) {
  try {
    return new URL(request.url || '/', baseUrl);
  } catch {
    throw new ApiError(400, 'INVALID_URL', 'The request URL is not valid.');
  }
}

function pathnameSegments(pathname) {
  try {
    return pathname.split('/').filter(Boolean).map((part) => decodeURIComponent(part));
  } catch {
    throw new ApiError(400, 'INVALID_PATH', 'A path segment is not valid URL encoding.');
  }
}

function queryParameters(url, allowedNames) {
  const result = new Map();
  for (const [name, value] of url.searchParams.entries()) {
    if (!allowedNames.has(name)) {
      if (['minSalary', 'maxSalary', 'salaryMin', 'salaryMax'].includes(name)) {
        throw new ApiError(422, 'UNSUPPORTED_FILTER', 'Salary filtering is disabled because salary comparability has not passed the data-quality gate.', { field: name });
      }
      throw new ApiError(400, 'UNKNOWN_QUERY_PARAMETER', `The query parameter '${name}' is not supported.`, { field: name });
    }
    if (result.has(name)) {
      throw new ApiError(400, 'DUPLICATE_QUERY_PARAMETER', `The query parameter '${name}' may be supplied only once.`, { field: name });
    }
    result.set(name, value);
  }
  return result;
}

function textParameter(parameters, name, options = {}) {
  if (!parameters.has(name)) return null;
  const value = parameters.get(name).trim();
  const minLength = options.minLength ?? 1;
  const maxLength = options.maxLength ?? 120;
  if (value.length < minLength || value.length > maxLength) {
    throw new ApiError(400, 'INVALID_QUERY_PARAMETER', `The '${name}' value must be between ${minLength} and ${maxLength} characters.`, { field: name });
  }
  return value;
}

function integerParameter(parameters, name, fallback, minimum, maximum) {
  if (!parameters.has(name)) return fallback;
  const raw = parameters.get(name).trim();
  if (!/^\d+$/.test(raw)) {
    throw new ApiError(400, 'INVALID_QUERY_PARAMETER', `The '${name}' value must be a whole number.`, { field: name });
  }
  const value = Number(raw);
  if (!Number.isSafeInteger(value) || value < minimum || value > maximum) {
    throw new ApiError(400, 'INVALID_QUERY_PARAMETER', `The '${name}' value must be between ${minimum} and ${maximum}.`, { field: name });
  }
  return value;
}

function booleanParameter(parameters, name, fallback = false) {
  if (!parameters.has(name)) return fallback;
  const value = parameters.get(name).trim().toLowerCase();
  if (value === 'true') return true;
  if (value === 'false') return false;
  throw new ApiError(400, 'INVALID_QUERY_PARAMETER', `The '${name}' value must be true or false.`, { field: name });
}

function searchParameter(parameters, name = 'q') {
  if (!parameters.has(name)) return null;
  const value = parameters.get(name).trim();
  if (value.length < 2 || value.length > 120) {
    throw new ApiError(400, 'INVALID_QUERY_PARAMETER', `The '${name}' value must be between 2 and 120 characters.`, { field: name });
  }
  return value.toLocaleLowerCase('en');
}

function parsePage(parameters) {
  const page = integerParameter(parameters, 'page', 1, 1, 1000000);
  const pageSize = integerParameter(parameters, 'pageSize', 20, 1, MAX_PAGE_SIZE);
  return { page, pageSize };
}

function parseSort(parameters) {
  const sort = textParameter(parameters, 'sort', { maxLength: 40 }) || 'title';
  const order = (textParameter(parameters, 'order', { maxLength: 4 }) || 'asc').toLowerCase();
  if (!['title', 'company', 'country', 'sourceDataset'].includes(sort)) {
    throw new ApiError(422, 'UNSUPPORTED_SORT', 'Sort must be one of title, company, country, or sourceDataset.', { field: 'sort' });
  }
  if (!['asc', 'desc'].includes(order)) {
    throw new ApiError(400, 'INVALID_QUERY_PARAMETER', 'Order must be asc or desc.', { field: 'order' });
  }
  return { sort, order };
}

function assertNoExtraBodyFields(body, allowedFields) {
  const extra = Object.keys(body).filter((key) => !allowedFields.has(key));
  if (extra.length) {
    throw new ApiError(400, 'UNKNOWN_BODY_FIELD', 'The request contains unsupported fields.', { fields: extra });
  }
}

function parseObservedTitleModelRequest(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    throw new ApiError(400, 'INVALID_BODY', 'The JSON body must be an object.');
  }
  assertNoExtraBodyFields(body, new Set(['skills', 'limit']));
  if (!Array.isArray(body.skills) || body.skills.length < 2 || body.skills.length > 50) {
    throw new ApiError(400, 'INVALID_SKILLS', 'Skills must be an array of 2 to 50 labels for this model.');
  }
  const skills = [];
  for (const label of body.skills) {
    if (typeof label !== 'string' || label.trim().length === 0 || label.trim().length > 80) {
      throw new ApiError(400, 'INVALID_SKILL_LABEL', 'Each skill must be a non-empty string of at most 80 characters.');
    }
    skills.push(label.trim());
  }
  const limit = body.limit === undefined ? 5 : body.limit;
  if (!Number.isInteger(limit) || limit < 1 || limit > 25) {
    throw new ApiError(400, 'INVALID_BODY_FIELD', 'limit must be an integer between 1 and 25.', { field: 'limit' });
  }
  return { skills, limit };
}

function parseMatchRequest(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    throw new ApiError(400, 'INVALID_BODY', 'The request body must be a JSON object.');
  }
  assertNoExtraBodyFields(body, new Set(['skills', 'country', 'workMode', 'sourceDataset', 'limit']));
  if (!Array.isArray(body.skills) || body.skills.length === 0 || body.skills.length > 50) {
    throw new ApiError(400, 'INVALID_SKILLS', 'Skills must be a non-empty array of at most 50 labels.');
  }
  const skills = [];
  for (const label of body.skills) {
    if (typeof label !== 'string' || label.trim().length === 0 || label.trim().length > 80) {
      throw new ApiError(400, 'INVALID_SKILL_LABEL', 'Each skill must be a non-empty string of at most 80 characters.');
    }
    skills.push(label.trim());
  }
  const optionalText = (name, maxLength) => {
    if (body[name] === undefined || body[name] === null) return null;
    if (typeof body[name] !== 'string' || body[name].trim().length === 0 || body[name].trim().length > maxLength) {
      throw new ApiError(400, 'INVALID_BODY_FIELD', `${name} must be a non-empty string of at most ${maxLength} characters.`, { field: name });
    }
    return body[name].trim();
  };
  const limitRaw = body.limit === undefined ? 10 : body.limit;
  if (!Number.isInteger(limitRaw) || limitRaw < 1 || limitRaw > 25) {
    throw new ApiError(400, 'INVALID_BODY_FIELD', 'limit must be an integer between 1 and 25.', { field: 'limit' });
  }
  return {
    skills,
    country: optionalText('country', 120),
    workMode: optionalText('workMode', 120),
    sourceDataset: optionalText('sourceDataset', 80),
    limit: limitRaw,
  };
}

async function readJsonBody(request) {
  if (request.body !== undefined) {
    if (typeof request.body === 'object' && request.body !== null && !Buffer.isBuffer(request.body)) return request.body;
    const rawValue = Buffer.isBuffer(request.body) ? request.body.toString('utf8') : String(request.body);
    if (Buffer.byteLength(rawValue, 'utf8') > JSON_BODY_LIMIT_BYTES) {
      throw new ApiError(413, 'PAYLOAD_TOO_LARGE', 'The JSON request body is too large.');
    }
    try {
      return JSON.parse(rawValue);
    } catch {
      throw new ApiError(400, 'INVALID_JSON', 'The request body is not valid JSON.');
    }
  }
  const declaredLength = Number(request.headers?.['content-length'] || 0);
  if (declaredLength > JSON_BODY_LIMIT_BYTES) {
    throw new ApiError(413, 'PAYLOAD_TOO_LARGE', 'The JSON request body is too large.');
  }
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += buffer.length;
    if (size > JSON_BODY_LIMIT_BYTES) {
      throw new ApiError(413, 'PAYLOAD_TOO_LARGE', 'The JSON request body is too large.');
    }
    chunks.push(buffer);
  }
  const rawValue = Buffer.concat(chunks).toString('utf8');
  if (!rawValue.trim()) throw new ApiError(400, 'EMPTY_BODY', 'A JSON request body is required.');
  try {
    return JSON.parse(rawValue);
  } catch {
    throw new ApiError(400, 'INVALID_JSON', 'The request body is not valid JSON.');
  }
}

function getDatabaseForRequest(getDb) {
  try {
    return getDb();
  } catch (error) {
    if (error?.code === 'DATABASE_UNAVAILABLE' || error?.code === 'DATABASE_SCHEMA_UNAVAILABLE') {
      throw new ApiError(503, 'DATA_UNAVAILABLE', 'The local application dataset is unavailable or is not initialized.');
    }
    throw new ApiError(503, 'DATA_UNAVAILABLE', 'The local application dataset could not be opened.');
  }
}

function validateSourceDataset(db, sourceDataset) {
  if (!sourceDataset) return null;
  const row = queries.one(db, 'SELECT 1 AS available FROM data_sources WHERE source_dataset = ?', [sourceDataset]);
  if (!row) throw new ApiError(400, 'INVALID_SOURCE_DATASET', 'The selected sourceDataset is not present in this dataset.', { field: 'sourceDataset' });
  return sourceDataset;
}

function parseJobFilters(db, parameters, options = {}) {
  const sourceName = options.sourceName || 'sourceDataset';
  const countryName = options.countryName || 'country';
  const sourceDataset = textParameter(parameters, sourceName, { maxLength: 80 });
  const country = textParameter(parameters, countryName, { maxLength: 120 });
  const roleId = options.roleId || textParameter(parameters, 'roleId', { maxLength: 120 });
  const skillId = textParameter(parameters, 'skillId', { maxLength: 100 });
  const workMode = textParameter(parameters, 'workModeRaw', { maxLength: 120 });
  const experience = textParameter(parameters, 'experienceRaw', { maxLength: 120 });
  validateSourceDataset(db, sourceDataset);
  if (skillId && !queries.eligibleSkillById(db, skillId)) {
    throw new ApiError(422, 'UNSUPPORTED_SKILL_FILTER', 'skillId must identify a reviewed skill supported by the current analytical rules.', { field: 'skillId' });
  }
  return { sourceDataset, country, roleId, skillId, workMode, experience };
}

function routeNotFound() {
  throw new ApiError(404, 'NOT_FOUND', 'The requested API resource was not found.');
}

function assertRoleExists(db, roleId) {
  if (!roleId || roleId.trim().length > 120) {
    throw new ApiError(400, 'INVALID_RESOURCE_ID', 'The normalized role title is not valid.');
  }
  const row = queries.one(db, `
    SELECT 1 AS found FROM jobs
    WHERE lower(trim(title)) = ?
    LIMIT 1
  `, [queries.normalizeExactLabel(roleId)]);
  if (!row) throw new ApiError(404, 'ROLE_NOT_FOUND', 'No job records exist for this normalized title.');
}

function methodNotAllowed(allow) {
  const error = new ApiError(405, 'METHOD_NOT_ALLOWED', 'This HTTP method is not supported for the requested API resource.');
  error.allow = allow;
  throw error;
}

function createApiHandler(options = {}) {
  const getDb = options.getDatabase || getDatabase;
  const configuredAppUrl = options.appUrl || app_url;
  const configuredAppOrigin = new URL(configuredAppUrl).origin;

  return async function apiHandler(request, response) {
    const requestId = requestIdFor(request);
    setResponseHeaders(request, response, requestId, configuredAppOrigin);
    const method = String(request.method || 'GET').toUpperCase();
    if (method === 'OPTIONS') {
      response.statusCode = 204;
      return response.end();
    }

    try {
      const url = parseRequestUrl(request, configuredAppUrl);
      const segments = pathnameSegments(url.pathname);
      if (segments.length === 1 && segments[0] === 'health' || segments.length === 2 && segments[0] === 'api' && segments[1] === 'health') {
        if (method !== 'GET') methodNotAllowed('GET, OPTIONS');
        queryParameters(url, new Set());
        const db = getDatabaseForRequest(getDb);
        let health;
        try {
          health = queries.getDatabaseHealth(db);
        } catch (error) {
          if (error?.code === 'DATABASE_SCHEMA_UNAVAILABLE') {
            throw new ApiError(503, 'DATA_UNAVAILABLE', 'The local application dataset is not initialized with the required schema.');
          }
          throw error;
        }
        return sendJson(response, 200, successPayload({ status: 'ok', database: health }, requestId, db));
      }
      if (segments.length === 1 && segments[0] === 'api' && method === 'GET') {
        queryParameters(url, new Set());
        return sendJson(response, 200, successPayload({
          name: 'JOP Marketing Intelligence API',
          version: 'v1',
          basePath: '/api/v1',
          documentation: '/api/v1/methodology',
        }, requestId));
      }
      if (segments[0] !== 'api' || segments[1] !== 'v1') routeNotFound();
      const resource = segments.slice(2);

      if (resource.length === 1 && resource[0] === 'methodology') {
        if (method !== 'GET') methodNotAllowed('GET, OPTIONS');
        queryParameters(url, new Set());
        return sendJson(response, 200, successPayload(queries.getMethodology(), requestId));
      }
      if (resource.length === 2 && resource[0] === 'models' && resource[1] === 'status') {
        if (method !== 'GET') methodNotAllowed('GET, OPTIONS');
        queryParameters(url, new Set());
        return sendJson(response, 200, successPayload(queries.getModelStatus(), requestId));
      }
      if (resource.length === 3 && resource[0] === 'models' && resource[1] === 'role-title' && resource[2] === 'predict') {
        if (method !== 'POST') methodNotAllowed('POST, OPTIONS');
        queryParameters(url, new Set());
        const contentType = String(request.headers?.['content-type'] || '').split(';')[0].trim().toLowerCase();
        if (contentType !== 'application/json') {
          throw new ApiError(415, 'UNSUPPORTED_MEDIA_TYPE', 'Content-Type must be application/json.');
        }
        const body = parseObservedTitleModelRequest(await readJsonBody(request));
        const db = getDatabaseForRequest(getDb);
        return sendJson(response, 200, successPayload(queries.predictObservedRoleTitles(db, body), requestId, db));
      }

      const db = getDatabaseForRequest(getDb);
      if (resource.length === 0) {
        if (method !== 'GET') methodNotAllowed('GET, OPTIONS');
        return sendJson(response, 200, successPayload({
          name: 'JOP Marketing Intelligence API',
          version: 'v1',
          resources: ['metadata', 'overview', 'roles', 'jobs', 'markets', 'skills', 'matches', 'models/status', 'models/role-title/predict', 'methodology'],
        }, requestId, db));
      }
      if (resource.length === 1 && resource[0] === 'metadata') {
        if (method !== 'GET') methodNotAllowed('GET, OPTIONS');
        queryParameters(url, new Set());
        return sendJson(response, 200, successPayload(queries.getMetadata(db, configuredAppUrl), requestId, db));
      }
      if (resource.length === 1 && resource[0] === 'overview') {
        if (method !== 'GET') methodNotAllowed('GET, OPTIONS');
        const params = queryParameters(url, new Set(['sourceDataset', 'country']));
        const filters = parseJobFilters(db, params);
        return sendJson(response, 200, successPayload(queries.getOverview(db, filters), requestId, db));
      }
      if (resource.length === 1 && resource[0] === 'jobs') {
        if (method !== 'GET') methodNotAllowed('GET, OPTIONS');
        const params = queryParameters(url, new Set([
          'q', 'sourceDataset', 'country', 'roleId', 'skillId', 'workModeRaw', 'experienceRaw',
          'page', 'pageSize', 'sort', 'order',
        ]));
        const filters = parseJobFilters(db, params);
        const { page, pageSize } = parsePage(params);
        const { sort, order } = parseSort(params);
        const q = searchParameter(params);
        return sendJson(response, 200, successPayload(queries.getJobs(db, filters, page, pageSize, q, sort, order), requestId, db));
      }
      if (resource.length === 2 && resource[0] === 'jobs') {
        if (method !== 'GET') methodNotAllowed('GET, OPTIONS');
        queryParameters(url, new Set());
        const recordId = resource[1];
        if (!recordId || recordId.length > 200) throw new ApiError(400, 'INVALID_RESOURCE_ID', 'The job record ID is not valid.');
        const job = queries.getJobById(db, recordId);
        if (!job) throw new ApiError(404, 'JOB_NOT_FOUND', 'No job record exists with this recordId.');
        return sendJson(response, 200, successPayload(job, requestId, db));
      }
      if (resource.length === 1 && resource[0] === 'roles') {
        if (method !== 'GET') methodNotAllowed('GET, OPTIONS');
        const params = queryParameters(url, new Set(['q', 'sourceDataset', 'country', 'page', 'pageSize']));
        const filters = parseJobFilters(db, params);
        const { page, pageSize } = parsePage(params);
        const q = searchParameter(params);
        return sendJson(response, 200, successPayload(queries.getRoles(db, filters, page, pageSize, q), requestId, db));
      }
      if (resource.length === 3 && resource[0] === 'roles' && resource[2] === 'analysis') {
        if (method !== 'GET') methodNotAllowed('GET, OPTIONS');
        const params = queryParameters(url, new Set(['sourceDataset', 'country']));
        const filters = parseJobFilters(db, params, { roleId: resource[1] });
        const analysis = queries.getRoleAnalysis(db, resource[1], filters);
        if (!analysis) throw new ApiError(404, 'ROLE_NOT_FOUND', 'No role records match this normalized title and scope.');
        return sendJson(response, 200, successPayload(analysis, requestId, db));
      }
      if (resource.length === 3 && resource[0] === 'roles' && resource[2] === 'ads') {
        if (method !== 'GET') methodNotAllowed('GET, OPTIONS');
        assertRoleExists(db, resource[1]);
        const params = queryParameters(url, new Set([
          'q', 'sourceDataset', 'country', 'skillId', 'workModeRaw', 'experienceRaw',
          'page', 'pageSize', 'sort', 'order',
        ]));
        const filters = parseJobFilters(db, params, { roleId: resource[1] });
        const { page, pageSize } = parsePage(params);
        const { sort, order } = parseSort(params);
        const q = searchParameter(params);
        return sendJson(response, 200, successPayload(queries.getJobs(db, filters, page, pageSize, q, sort, order), requestId, db));
      }
      if (resource.length === 1 && resource[0] === 'skills') {
        if (method !== 'GET') methodNotAllowed('GET, OPTIONS');
        const params = queryParameters(url, new Set(['q', 'sourceDataset', 'country', 'roleId', 'workModeRaw', 'experienceRaw', 'page', 'pageSize']));
        const filters = parseJobFilters(db, params);
        const { page, pageSize } = parsePage(params);
        const q = searchParameter(params);
        return sendJson(response, 200, successPayload(queries.getSkills(db, filters, page, pageSize, q), requestId, db));
      }
      if (resource.length === 2 && resource[0] === 'skills' && resource[1] === 'co-occurrence') {
        if (method !== 'GET') methodNotAllowed('GET, OPTIONS');
        const params = queryParameters(url, new Set(['skillId', 'sourceDataset', 'country', 'roleId', 'workModeRaw', 'experienceRaw', 'limit']));
        const skillId = textParameter(params, 'skillId', { maxLength: 100 });
        if (!skillId) throw new ApiError(400, 'MISSING_QUERY_PARAMETER', 'skillId is required.', { field: 'skillId' });
        const filters = parseJobFilters(db, params);
        const limit = integerParameter(params, 'limit', 10, 1, 50);
        const result = queries.getSkillCooccurrence(db, skillId, filters, limit);
        if (!result) throw new ApiError(404, 'SKILL_NOT_FOUND', 'skillId does not identify an eligible skill.');
        return sendJson(response, 200, successPayload(result, requestId, db));
      }
      if (resource.length === 3 && resource[0] === 'skills' && resource[2] === 'resources') {
        if (method !== 'GET') methodNotAllowed('GET, OPTIONS');
        const params = queryParameters(url, new Set(['language', 'freeOnly', 'page', 'pageSize']));
        const language = textParameter(params, 'language', { maxLength: 80 });
        const freeOnly = booleanParameter(params, 'freeOnly', false);
        const { page, pageSize } = parsePage(params);
        const result = queries.getResourcesForSkill(db, resource[1], { language, freeOnly, page, pageSize });
        if (!result) throw new ApiError(404, 'SKILL_NOT_FOUND', 'skillId does not identify an eligible skill.');
        return sendJson(response, 200, successPayload(result, requestId, db));
      }
      if (resource.length === 1 && resource[0] === 'markets' && method === 'GET') {
        routeNotFound();
      }
      if (resource.length === 2 && resource[0] === 'markets' && resource[1] === 'compare') {
        if (method !== 'GET') methodNotAllowed('GET, OPTIONS');
        const params = queryParameters(url, new Set(['limit']));
        const limit = integerParameter(params, 'limit', 10, 1, 50);
        return sendJson(response, 200, successPayload(queries.getMarketComparison(db, limit), requestId, db));
      }
      if (resource.length === 2 && resource[0] === 'markets' && resource[1] === 'trends') {
        if (method !== 'GET') methodNotAllowed('GET, OPTIONS');
        const params = queryParameters(url, new Set(['metric', 'year', 'period', 'country', 'sourceDataset']));
        const metric = textParameter(params, 'metric', { maxLength: 40 }) || 'jobRecords';
        const period = textParameter(params, 'period', { maxLength: 20 }) || 'month';
        const yearText = textParameter(params, 'year', { maxLength: 4 }) || '2023';
        const sourceDataset = textParameter(params, 'sourceDataset', { maxLength: 80 }) || 'international_jobs';
        const country = textParameter(params, 'country', { maxLength: 120 });
        if (metric !== 'jobRecords' || period !== 'month' || yearText !== '2023' || sourceDataset !== 'international_jobs') {
          throw new ApiError(422, 'UNSUPPORTED_TREND', 'Only monthly job-record counts for international_jobs in 2023 are supported.');
        }
        validateSourceDataset(db, sourceDataset);
        return sendJson(response, 200, successPayload(queries.getHistoricalTrends(db, { country }), requestId, db));
      }
      if (resource.length === 1 && resource[0] === 'matches') {
        if (method !== 'POST') methodNotAllowed('POST, OPTIONS');
        queryParameters(url, new Set());
        const contentType = String(request.headers?.['content-type'] || '').split(';')[0].trim().toLowerCase();
        if (contentType !== 'application/json') {
          throw new ApiError(415, 'UNSUPPORTED_MEDIA_TYPE', 'Content-Type must be application/json.');
        }
        const body = parseMatchRequest(await readJsonBody(request));
        validateSourceDataset(db, body.sourceDataset);
        return sendJson(response, 200, successPayload(queries.matchSkills(db, body), requestId, db));
      }
      routeNotFound();
    } catch (error) {
      const statusCode = Number.isInteger(error?.statusCode) ? error.statusCode : 500;
      const code = error?.code && typeof error.code === 'string' ? error.code : 'INTERNAL_ERROR';
      const publicMessage = statusCode >= 500
        ? (statusCode === 503 ? 'The local application dataset is unavailable.' : 'The request could not be completed.')
        : String(error?.message || 'The request is invalid.');
      if (statusCode >= 500) {
        // Do not log request URLs, bodies, skills, SQL, filesystem paths, or stack traces.
        console.error(JSON.stringify({ requestId, errorCode: code, errorName: error?.name || 'Error' }));
      }
      const errorPayload = {
        error: {
          code,
          message: publicMessage,
          requestId,
          ...(error?.safeDetails ? { details: error.safeDetails } : {}),
        },
      };
      if (error?.allow) response.setHeader('Allow', error.allow);
      if (statusCode === 413) response.setHeader('Connection', 'close');
      return sendJson(response, statusCode, errorPayload);
    }
  };
}

module.exports = { ApiError, createApiHandler, parseMatchRequest, parseObservedTitleModelRequest, readJsonBody };
