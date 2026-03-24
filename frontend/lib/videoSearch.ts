/**
 * Search API payload guards (POST /videos/{id}/search).
 */

export type MatchQuality = "strong" | "partial" | "weak";

export type VideoSearchMatch = {
  start_ts: number;
  end_ts: number;
  text: string;
  confidence: number;
  macro_context_text: string | null;
  match_start_offset: number | null;
  match_end_offset: number | null;
  match_quality: MatchQuality;
};

export function buildSearchRequestBody(query: string): { query: string } {
  return { query: query.trim() };
}

function isMatchQuality(v: unknown): v is MatchQuality {
  return v === "strong" || v === "partial" || v === "weak";
}

export function parseSearchSuccess(data: unknown): VideoSearchMatch | null {
  if (typeof data !== "object" || data === null) return null;
  const o = data as Record<string, unknown>;
  const start_ts = Number(o.start_ts);
  const end_ts = Number(o.end_ts);
  const text = typeof o.text === "string" ? o.text : null;
  const confidence = Number(o.confidence);
  const macro_context_text =
    typeof o.macro_context_text === "string" ? o.macro_context_text : null;
  const rawStartOffset = o.match_start_offset;
  const rawEndOffset = o.match_end_offset;
  const hasOffsets =
    rawStartOffset !== undefined &&
    rawStartOffset !== null &&
    rawEndOffset !== undefined &&
    rawEndOffset !== null;
  const match_start_offset = hasOffsets ? Number(rawStartOffset) : null;
  const match_end_offset = hasOffsets ? Number(rawEndOffset) : null;
  const mq = o.match_quality;
  if (
    !Number.isFinite(start_ts) ||
    !Number.isFinite(end_ts) ||
    text === null ||
    !Number.isFinite(confidence) ||
    (hasOffsets &&
      (!Number.isFinite(match_start_offset) || !Number.isFinite(match_end_offset))) ||
    !isMatchQuality(mq)
  ) {
    return null;
  }
  return {
    start_ts,
    end_ts,
    text,
    confidence,
    macro_context_text,
    match_start_offset:
      match_start_offset === null ? null : Math.trunc(match_start_offset),
    match_end_offset: match_end_offset === null ? null : Math.trunc(match_end_offset),
    match_quality: mq,
  };
}

export function extractApiErrorMessage(
  data: unknown,
  fallback: string,
): string {
  const isLikelyInternalCode = (value: string): boolean =>
    /^[A-Z0-9_]+$/.test(value);
  if (
    typeof data === "object" &&
    data !== null &&
    "error" in data &&
    typeof (data as { error?: { message?: string } }).error?.message === "string"
  ) {
    const message = (data as { error: { message: string } }).error.message.trim();
    if (!message || isLikelyInternalCode(message)) return fallback;
    return message;
  }
  return fallback;
}

export function isNoMatchError(data: unknown): boolean {
  if (typeof data !== "object" || data === null || !("error" in data)) {
    return false;
  }
  const err = (data as { error?: { code?: string } }).error;
  return err?.code === "NO_MATCH";
}

/**
 * Split macro context using server-provided Python-str offsets (clamped to macro length).
 * Used for highlight rendering and tests.
 */
export function splitMacroHighlight(
  macro_context_text: string,
  match_start_offset: number,
  match_end_offset: number,
): { before: string; mid: string; after: string } {
  const s = macro_context_text;
  const lo = Math.max(0, Math.min(match_start_offset, s.length));
  const hi = Math.max(lo, Math.min(match_end_offset, s.length));
  return {
    before: s.slice(0, lo),
    mid: s.slice(lo, hi),
    after: s.slice(hi),
  };
}

/** Seconds from start → MM:SS for display (floor seconds). */
export function formatSecondsToClock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}
