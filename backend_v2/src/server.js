import http from 'node:http';
import { createHttpHandler } from './http.js';
import { config } from './config.js';

const handler = createHttpHandler();
const server = http.createServer((req, res) => {
  void handler(req, res);
});

server.listen(config.port, config.host, () => {
  console.log(`JOP backend v2 listening on http://${config.host}:${config.port}`);
  console.log('Dashboard: /dashboard | API: /api/v2');
});

function shutdown(signal) {
  console.log(`${signal} received; closing the HTTP server.`);
  server.close(() => {
    handler.close();
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 10_000).unref();
}

process.once('SIGINT', () => shutdown('SIGINT'));
process.once('SIGTERM', () => shutdown('SIGTERM'));
