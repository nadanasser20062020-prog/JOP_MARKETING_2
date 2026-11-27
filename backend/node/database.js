'use strict';

const fs = require('node:fs');
const { DatabaseSync } = require('node:sqlite');
const { resolveDatabasePath } = require('../config/database');

let sharedConnection;

function openReadOnlyDatabase(databasePath = resolveDatabasePath()) {
  const safeDatabasePath = resolveDatabasePath(databasePath);
  if (!fs.existsSync(safeDatabasePath) || !fs.statSync(safeDatabasePath).isFile()) {
    const error = new Error('The configured local SQLite database is unavailable.');
    error.code = 'DATABASE_UNAVAILABLE';
    throw error;
  }

  const connection = new DatabaseSync(safeDatabasePath, {
    readOnly: true,
    enableForeignKeyConstraints: true,
    timeout: 10000,
  });
  connection.exec('PRAGMA query_only = ON; PRAGMA busy_timeout = 10000;');
  return connection;
}

function getDatabase() {
  if (!sharedConnection) sharedConnection = openReadOnlyDatabase();
  return sharedConnection;
}

function closeSharedDatabase() {
  if (sharedConnection) {
    sharedConnection.close();
    sharedConnection = undefined;
  }
}

module.exports = { openReadOnlyDatabase, getDatabase, closeSharedDatabase };
