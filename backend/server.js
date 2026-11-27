'use strict';

const { createServer } = require('node:http');
const { createApiHandler } = require('./node/api');

const host = process.env.HOST || '0.0.0.0';
const port = Number(process.env.PORT || 3000);
if (!Number.isInteger(port) || port < 0 || port > 65535) {
  throw new Error('PORT must be an integer between 0 and 65535.');
}

const server = createServer(createApiHandler());
server.requestTimeout = 15000;
server.headersTimeout = 10000;
server.keepAliveTimeout = 5000;

server.listen(port, host, () => {
  const address = server.address();
  const shownPort = typeof address === 'object' && address ? address.port : port;
  console.log(`JOP API listening at http://${host}:${shownPort}`);
});

function shutdown() {
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(1), 5000).unref();
}
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
