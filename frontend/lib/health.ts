/**
 * Interprets JSON from GET /health (FastAPI). Success body example:
 * `{ "status": "ok", "database": "ok" }`
 */
export function isBackendHealthyPayload(data: unknown): boolean {
  if (!data || typeof data !== "object") {
    return false;
  }
  const o = data as Record<string, unknown>;
  return o.status === "ok" && o.database === "ok";
}
