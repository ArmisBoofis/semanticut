import { isBackendHealthyPayload } from "./health";

export type BackendHealthResult =
  | { ok: true }
  | { ok: false; statusCode?: number };

function internalBaseUrl(): string {
  return (
    process.env.API_INTERNAL_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000"
  );
}

/**
 * Server-side fetch to FastAPI `/health` (Compose service `api:8000` or local dev).
 * Avoids browser CORS by calling from the Next.js server only.
 */
export async function fetchBackendHealth(): Promise<BackendHealthResult> {
  const url = `${internalBaseUrl()}/health`;
  try {
    const res = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(8_000),
    });
    if (!res.ok) {
      return { ok: false, statusCode: res.status };
    }
    const data: unknown = await res.json();
    if (isBackendHealthyPayload(data)) {
      return { ok: true };
    }
    return { ok: false, statusCode: res.status };
  } catch {
    return { ok: false };
  }
}
