export class HttpError extends Error {
  constructor(status, code, message, details = undefined) {
    super(message);
    this.name = 'HttpError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function notFound(message = 'The requested resource was not found.') {
  return new HttpError(404, 'NOT_FOUND', message);
}

export function badRequest(message, details = undefined) {
  return new HttpError(400, 'BAD_REQUEST', message, details);
}

export function serviceUnavailable(message, details = undefined) {
  return new HttpError(503, 'SERVICE_UNAVAILABLE', message, details);
}
