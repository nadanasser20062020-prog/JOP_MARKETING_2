import { badRequest } from './errors.js';

export function normalizeKey(value) {
  return String(value ?? '')
    .normalize('NFKC')
    .toLocaleLowerCase('en-US')
    .trim()
    .replace(/\s+/gu, ' ');
}

export function parseBoundedInteger(value, { name, fallback, min = 1, max = 100 } = {}) {
  if (value === undefined || value === null || value === '') return fallback;
  const number = Number(value);
  if (!Number.isInteger(number) || number < min || number > max) {
    throw badRequest(`${name || 'value'} must be an integer between ${min} and ${max}.`);
  }
  return number;
}

export function escapeLikePrefix(value) {
  return String(value ?? '').replace(/[\\%_]/gu, '\\$&');
}

export function safePercentage(numerator, denominator) {
  if (!denominator) return 0;
  return Number(((Number(numerator) / Number(denominator)) * 100).toFixed(4));
}

export function positiveNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : null;
}

export function getRoleDisplay(value) {
  return String(value ?? '').replace(/\s+/gu, ' ').trim();
}
