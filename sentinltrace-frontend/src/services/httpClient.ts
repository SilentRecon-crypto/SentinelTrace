// ============================================================
// SENTINELTRACE HTTP CLIENT
//
// The single place that knows how to talk to the real FastAPI backend.
// Every real-backend service module (health.ts, complaints.ts, ...) goes
// through this file — never calls fetch() directly — so retry/error/base-
// URL handling only ever needs to change in one place.
//
// This is intentionally separate from src/services/api.ts and
// src/services/userApi.ts, which remain the existing mock/demo data layer
// for pages not yet wired to the real backend.
// ============================================================

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined;

export class ApiError extends Error {
  /** HTTP status code, or 0 for a network-level failure (backend unreachable, misconfigured base URL, etc). */
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (!API_BASE_URL) {
    throw new ApiError(
      0,
      "VITE_API_BASE_URL is not set. Add it to .env.local (see .env.example) — e.g. VITE_API_BASE_URL=http://127.0.0.1:8000 — and restart the dev server."
    );
  }

  const url = `${API_BASE_URL}${path}`;
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    // fetch() throws (not a rejected HTTP response) for network-level failures:
    // backend not running, wrong host/port, CORS misconfiguration, etc.
    throw new ApiError(0, `Could not reach the SentinelTrace backend at ${API_BASE_URL}. Is it running?`);
  }

  if (!res.ok) {
    let detail = res.statusText || `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body && typeof body.detail === "string") detail = body.detail;
      else if (body && body.detail) detail = JSON.stringify(body.detail);
    } catch {
      // Response body wasn't JSON (or was empty) — fall back to statusText above.
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const http = {
  get: <T>(path: string): Promise<T> => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>(path, { method: "PATCH", body: body === undefined ? undefined : JSON.stringify(body) }),
};
