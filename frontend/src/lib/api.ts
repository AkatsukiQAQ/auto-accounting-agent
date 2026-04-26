// Tiny fetch wrapper — base URL from env, envelope unwrap, typed errors.

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export interface ApiErrorBody {
  code: string;
  message: string;
  meta: Record<string, unknown>;
}

export class ApiError extends Error {
  status: number;
  code: string;
  meta: Record<string, unknown>;
  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = 'ApiError';
    this.status = status;
    this.code = body.code;
    this.meta = body.meta;
  }
}

interface Envelope<T> {
  data: T;
}

async function parseError(res: Response): Promise<ApiError> {
  let body: ApiErrorBody = {
    code: 'unknown',
    message: `HTTP ${res.status}`,
    meta: {},
  };
  try {
    const json = await res.json();
    if (json?.error) body = json.error;
  } catch {
    /* keep default */
  }
  return new ApiError(res.status, body);
}

/** GET / POST / PATCH / DELETE with JSON body. Auto-unwraps `{data: T}`. */
export async function fetchJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...((init.headers as Record<string, string>) ?? {}),
  };
  if (init.body !== undefined && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  if (!res.ok) throw await parseError(res);
  // 200 with empty body would fail .json() — guard.
  const text = await res.text();
  if (!text) return undefined as T;
  const parsed = JSON.parse(text) as Envelope<T> | T;
  // Unwrap only the *single-key* `{data: T}` envelope. List endpoints like
  // `/api/transactions` return `{data: [...], nextCursor: ...}` and the caller
  // wants the whole object — leave those alone.
  if (
    parsed &&
    typeof parsed === 'object' &&
    !Array.isArray(parsed) &&
    Object.keys(parsed as object).length === 1 &&
    'data' in (parsed as object)
  ) {
    return (parsed as Envelope<T>).data;
  }
  return parsed as T;
}

/** Multipart POST — let browser set Content-Type with boundary. */
export async function fetchMultipart<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { method: 'POST', body: form });
  if (!res.ok) throw await parseError(res);
  const text = await res.text();
  const parsed = JSON.parse(text) as Envelope<T>;
  return parsed.data;
}

/** Builds a query string from an object, skipping null/undefined/empty-array. */
export function qs(params: Record<string, string | number | string[] | undefined | null>): string {
  const out: string[] = [];
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '') continue;
    if (Array.isArray(v)) {
      if (v.length === 0) continue;
      out.push(`${encodeURIComponent(k)}=${encodeURIComponent(v.join(','))}`);
    } else {
      out.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
    }
  }
  return out.length ? `?${out.join('&')}` : '';
}
