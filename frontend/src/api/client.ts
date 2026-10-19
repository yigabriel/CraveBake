import type { ApiErrorBody } from "./types";

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000/v1";
const TOKEN_KEY = "cravebake.token";

/** Every API error has the same shape (see docs/FRONTEND_FEATURES.md §1). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly fieldErrors: Record<string, string> = {},
    readonly retryAfterSeconds: number | null = null,
  ) {
    super(message);
  }
}

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string | null) {
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token);
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      // Private mode: the session simply won't survive a reload.
    }
  },
};

let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

type QueryValue = string | number | boolean | null | undefined | string[];

export function buildQuery(params: Record<string, QueryValue>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    // Repeated keys for lists: ?tag_ids=a&tag_ids=b
    if (Array.isArray(value)) value.forEach((item) => search.append(key, item));
    else search.append(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

interface RequestOptions {
  method?: string;
  query?: Record<string, QueryValue>;
  json?: unknown;
  form?: Record<string, string>;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return (await apiWithStatus<T>(path, options)).data;
}

export async function apiWithStatus<T>(path: string, options: RequestOptions = {}): Promise<{ data: T; status: number }> {
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (options.form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = new URLSearchParams(options.form);
  } else if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}${buildQuery(options.query ?? {})}`, {
      method: options.method ?? "GET",
      headers,
      body,
    });
  } catch {
    throw new ApiError(0, "network_error", "Network error");
  }

  if (response.status === 204) return { data: undefined as T, status: 204 };
  const data = await response.json().catch(() => null);
  if (response.ok) return { data: data as T, status: response.status };

  const error = (data ?? {}) as Partial<ApiErrorBody>;
  const fieldErrors: Record<string, string> = {};
  for (const item of error.errors ?? []) {
    // "body.password" / "query.limit" -> "password" / "limit"
    fieldErrors[item.field.split(".").slice(1).join(".") || item.field] = item.message;
  }
  const retryAfter = response.headers.get("Retry-After");
  const apiError = new ApiError(
    response.status,
    error.code ?? "internal_error",
    error.detail ?? response.statusText,
    fieldErrors,
    retryAfter ? Number(retryAfter) : null,
  );
  // A bad credentials login is also 401, but there is no session to drop yet.
  if (response.status === 401 && token) onUnauthorized();
  throw apiError;
}
