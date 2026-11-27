'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const REAL_PROJECT_ROOT = fs.realpathSync(PROJECT_ROOT);
const DEFAULT_DATABASE_PATH = path.join(PROJECT_ROOT, 'data', 'processed', 'job_market.sqlite3');

function isInsideProjectRoot(candidatePath) {
  const relativePath = path.relative(REAL_PROJECT_ROOT, candidatePath);
  return relativePath === ''
    || (relativePath !== '..' && !relativePath.startsWith(`..${path.sep}`) && !path.isAbsolute(relativePath));
}

function assertInsideProjectRoot(candidatePath) {
  let existingAncestor = candidatePath;
  while (true) {
    try {
      fs.lstatSync(existingAncestor);
      break;
    } catch (error) {
      if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') throw error;
      const parent = path.dirname(existingAncestor);
      if (parent === existingAncestor) throw error;
      existingAncestor = parent;
    }
  }
  const realAncestor = fs.realpathSync(existingAncestor);
  const suffix = path.relative(existingAncestor, candidatePath);
  const physicalCandidate = path.resolve(realAncestor, suffix);
  if (!isInsideProjectRoot(physicalCandidate)) {
    throw new Error('JOP_DATABASE_PATH must stay inside the project root.');
  }
}

function resolveDatabasePath(configuredPath = process.env.JOP_DATABASE_PATH) {
  const candidate = String(configuredPath || DEFAULT_DATABASE_PATH).trim();
  if (!candidate || candidate === ':memory:' || candidate.startsWith('file:') || candidate.includes('://')) {
    throw new Error('JOP_DATABASE_PATH must be a local SQLite filesystem path.');
  }
  const resolvedPath = path.resolve(REAL_PROJECT_ROOT, candidate);
  if (!isInsideProjectRoot(resolvedPath)) {
    throw new Error('JOP_DATABASE_PATH must stay inside the project root.');
  }
  assertInsideProjectRoot(resolvedPath);
  return resolvedPath;
}

module.exports = Object.freeze({ PROJECT_ROOT, DEFAULT_DATABASE_PATH, resolveDatabasePath });
