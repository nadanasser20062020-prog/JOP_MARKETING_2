'use strict';

const DEFAULT_APP_URL = 'http://localhost:3000';

function resolveAppUrl() {
  const configured = String(process.env.APP_URL || '').trim();
  const vercelHost = String(process.env.VERCEL_URL || '').trim();
  const candidate = configured || (vercelHost ? `https://${vercelHost}` : DEFAULT_APP_URL);

  let parsed;
  try {
    parsed = new URL(candidate);
  } catch {
    throw new Error('APP_URL must be an absolute http:// or https:// URL.');
  }

  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) {
    throw new Error('APP_URL must be an absolute http:// or https:// URL without credentials.');
  }
  if (parsed.pathname !== '/' || parsed.search || parsed.hash) {
    throw new Error('APP_URL must contain only the application origin, without a path, query, or fragment.');
  }

  return parsed.origin;
}

const app_url = resolveAppUrl();

module.exports = Object.freeze({ app_url, app_origin: new URL(app_url).origin });
