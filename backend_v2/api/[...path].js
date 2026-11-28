import { createHttpHandler } from '../src/http.js';

const handler = createHttpHandler();

export default async function apiHandler(request, response) {
  return handler(request, response);
}
