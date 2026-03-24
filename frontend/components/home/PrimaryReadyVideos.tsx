"use client";

import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";

import { SemanticVideoPlayer } from "@/components/home/SemanticVideoPlayer";
import {
  filterCompletedVideos,
  isVideoListPayload,
  type VideoListItem,
} from "@/lib/readyVideos";
import {
  buildSearchRequestBody,
  extractApiErrorMessage,
  formatSecondsToClock,
  isNoMatchError,
  parseSearchSuccess,
  splitMacroHighlight,
  type VideoSearchMatch,
} from "@/lib/videoSearch";

function matchQualityLabel(
  q: VideoSearchMatch["match_quality"],
): string {
  switch (q) {
    case "strong":
      return fr.homeSearchMatchQualityStrong;
    case "partial":
      return fr.homeSearchMatchQualityPartial;
    default:
      return fr.homeSearchMatchQualityWeak;
  }
}

function MacroContextWithHighlight({ match }: { match: VideoSearchMatch }) {
  const content = match.macro_context_text ?? match.text;
  const hasHighlightBounds =
    typeof match.match_start_offset === "number" &&
    typeof match.match_end_offset === "number";
  if (!hasHighlightBounds) {
    return (
      <div className="space-y-1">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
          {fr.homeSearchMacroContextTitle}
        </p>
        <p className="whitespace-pre-wrap text-zinc-300">{content}</p>
      </div>
    );
  }
  const { before, mid, after } = splitMacroHighlight(
    content,
    match.match_start_offset,
    match.match_end_offset,
  );
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
        {fr.homeSearchMacroContextTitle}
      </p>
      <p className="whitespace-pre-wrap text-zinc-300">
        {before}
        <mark
          className="rounded-sm bg-amber-500/25 px-0.5 text-zinc-100 ring-1 ring-amber-400/40"
          aria-label={fr.homeSearchPassageHighlightAria}
        >
          {mid}
        </mark>
        {after}
      </p>
    </div>
  );
}
import { fr } from "@/lib/strings";

const POLL_INTERVAL_MS = 8_000;
const DEFAULT_SEARCH_TIMEOUT_MS = 12_000;

declare global {
  interface Window {
    __SEMANTICUT_SEARCH_TIMEOUT_MS__?: number;
  }
}

export function PrimaryReadyVideos() {
  const [items, setItems] = useState<VideoListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchResult, setSearchResult] = useState<VideoSearchMatch | null>(
    null,
  );
  const [searchNoMatch, setSearchNoMatch] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [isTimeoutError, setIsTimeoutError] = useState(false);
  const [seekToSeconds, setSeekToSeconds] = useState<number | null>(null);
  const [seekKey, setSeekKey] = useState(0);
  const [playbackFromLabel, setPlaybackFromLabel] = useState<string | null>(null);
  const [playbackError, setPlaybackError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const latestSeekKeyRef = useRef(0);

  const isValidStartTs = (value: unknown): value is number =>
    typeof value === "number" && Number.isFinite(value) && value >= 0;

  const onPlayerSeeked = useCallback(
    (seconds: number, completedSeekKey: number) => {
      if (completedSeekKey !== latestSeekKeyRef.current) return;
      setPlaybackFromLabel(
        `${fr.homeSearchPlaybackFromPrefix}${formatSecondsToClock(seconds)}`,
      );
    },
    [],
  );

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await fetch("/api/videos", { cache: "no-store" });
      const data: unknown = await res.json();
      if (!res.ok) {
        const msg =
          typeof data === "object" &&
          data !== null &&
          "error" in data &&
          typeof (data as { error?: { message?: string } }).error?.message ===
            "string"
            ? (data as { error: { message: string } }).error.message
            : fr.homeReadyVideosError;
        setError(msg);
        setItems(null);
        return;
      }
      if (!isVideoListPayload(data)) {
        setError(fr.homeReadyVideosError);
        setItems(null);
        return;
      }
      setItems(filterCompletedVideos(data));
    } catch {
      setError(fr.homeReadyVideosError);
      setItems(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const id = window.setInterval(() => {
      void load();
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [load]);

  useEffect(() => {
    if (items === null || items.length === 0) return;
    setSelectedId((prev) => {
      if (prev !== null && items.some((r) => r.id === prev)) return prev;
      return items[0]?.id ?? null;
    });
  }, [items]);

  useEffect(() => {
    setSearchResult(null);
    setSearchNoMatch(false);
    setSearchError(null);
    setIsTimeoutError(false);
    setSeekToSeconds(null);
    setPlaybackFromLabel(null);
    setPlaybackError(null);
  }, [selectedId]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const hasReadyVideos = Boolean(items && items.length > 0);
  const canSubmitSearch =
    hasReadyVideos &&
    selectedId !== null &&
    query.trim().length > 0 &&
    !searchLoading;
  const searchTimeoutMs =
    typeof window !== "undefined" &&
    Number.isFinite(window.__SEMANTICUT_SEARCH_TIMEOUT_MS__)
      ? Number(window.__SEMANTICUT_SEARCH_TIMEOUT_MS__)
      : DEFAULT_SEARCH_TIMEOUT_MS;

  const startSearch = useCallback(async () => {
    if (!selectedId || !query.trim() || searchLoading) return;

    abortRef.current?.abort();
    const ac = new AbortController();
    const timeoutId = window.setTimeout(() => {
      ac.abort("timeout");
    }, searchTimeoutMs);
    abortRef.current = ac;

    setSearchLoading(true);
    setSearchNoMatch(false);
    setSearchError(null);
    setIsTimeoutError(false);
    setSearchResult(null);
    setSeekToSeconds(null);
    setPlaybackFromLabel(null);
    setPlaybackError(null);

    try {
      const res = await fetch(
        `/api/videos/${encodeURIComponent(selectedId)}/search`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(buildSearchRequestBody(query)),
          signal: ac.signal,
          cache: "no-store",
        },
      );
      const data: unknown = await res.json().catch(() => null);

      if (ac.signal.aborted) return;

      if (!res.ok) {
        if (isNoMatchError(data)) {
          setSearchNoMatch(true);
          return;
        }
        setSearchError(
          extractApiErrorMessage(data, fr.homeSearchGenericError),
        );
        return;
      }

      const parsed = parseSearchSuccess(data);
      if (parsed === null) {
        setSearchError(fr.homeSearchMalformedResponse);
        return;
      }
      setSearchResult(parsed);
      if (!isValidStartTs(parsed.start_ts)) {
        setSeekToSeconds(null);
        setPlaybackError(fr.homeSearchUnplayableResult);
        return;
      }
      setPlaybackError(null);
      setSeekToSeconds(parsed.start_ts);
      setSeekKey((k) => {
        const next = k + 1;
        latestSeekKeyRef.current = next;
        return next;
      });
    } catch (err) {
      const timeoutAbort =
        err instanceof DOMException &&
        err.name === "AbortError" &&
        ac.signal.reason === "timeout";
      if (timeoutAbort) {
        setIsTimeoutError(true);
        setSearchError(fr.homeSearchTimeoutError);
        return;
      }
      if (err instanceof DOMException && err.name === "AbortError") return;
      setSearchError(fr.homeSearchGenericError);
    } finally {
      window.clearTimeout(timeoutId);
      if (abortRef.current === ac) setSearchLoading(false);
    }
  }, [query, searchLoading, searchTimeoutMs, selectedId]);

  const onSubmitSearch = async (e: FormEvent) => {
    e.preventDefault();
    await startSearch();
  };

  if (loading) {
    return (
      <p className="text-sm text-zinc-400" role="status">
        {fr.homeReadyVideosLoading}
      </p>
    );
  }

  if (error) {
    return (
      <p className="text-sm text-red-400" role="alert">
        {error}
      </p>
    );
  }

  return (
    <section className="space-y-4" aria-live="polite" aria-relevant="text">
      <div className="space-y-1">
        <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-400">
          {fr.homeReadyVideosHeading}
        </h2>
        <p className="text-sm text-zinc-400">{fr.homeReadyVideosHelper}</p>
      </div>

      {!hasReadyVideos ? (
        <p className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 text-sm text-zinc-300">
          {fr.homeReadyVideosEmpty}
        </p>
      ) : (
        <ul className="space-y-2">
          {items?.map((row) => (
            <li
              key={row.id}
              className="rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-3 text-sm text-zinc-100"
            >
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="radio"
                  name="ready-video"
                  className="accent-zinc-100"
                  checked={selectedId === row.id}
                  onChange={() => setSelectedId(row.id)}
                />
                <span>{row.label}</span>
              </label>
            </li>
          ))}
        </ul>
      )}

      {hasReadyVideos && selectedId !== null ? (
        <SemanticVideoPlayer
          videoId={selectedId}
          seekToSeconds={seekToSeconds}
          seekKey={seekKey}
          onSeeked={onPlayerSeeked}
        />
      ) : null}

      <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
        <h3 className="text-sm font-medium text-zinc-200">
          {fr.homeSearchHeading}
        </h3>

        {!hasReadyVideos ? (
          <p className="mt-2 text-sm text-zinc-400">{fr.homeSearchNoVideoSelected}</p>
        ) : selectedId === null ? (
          <p className="mt-2 text-sm text-zinc-400">{fr.homeSearchNoVideoSelected}</p>
        ) : (
          <form onSubmit={onSubmitSearch} className="mt-3 space-y-3">
            <div>
              <label
                htmlFor="home-search-query"
                className="block text-xs font-medium uppercase tracking-wide text-zinc-500"
              >
                {fr.homeSearchQueryLabel}
              </label>
              <input
                id="home-search-query"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={fr.homeSearchQueryPlaceholder}
                className="mt-1 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600"
                disabled={searchLoading}
                autoComplete="off"
              />
            </div>
            <button
              type="submit"
              disabled={!canSubmitSearch}
              className="rounded-md bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-900 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {searchLoading ? fr.homeSearchSubmitting : fr.homeSearchSubmit}
            </button>
            {searchLoading ? (
              <p className="text-sm text-zinc-400" role="status">
                {fr.homeSearchSubmitting}
              </p>
            ) : null}
          </form>
        )}

        {searchNoMatch ? (
          <p className="mt-3 text-sm text-amber-200/90" role="status">
            {fr.homeSearchNoMatch}
          </p>
        ) : null}

        {searchError ? (
          <div className="mt-3 space-y-2">
            <p className="text-sm text-red-400" role="alert">
              {searchError}
            </p>
            {isTimeoutError ? (
              <button
                type="button"
                onClick={() => {
                  void startSearch();
                }}
                disabled={searchLoading || !canSubmitSearch}
                className="rounded-md border border-zinc-600 px-3 py-1.5 text-sm text-zinc-200 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {fr.homeSearchRetry}
              </button>
            ) : null}
          </div>
        ) : null}

        {playbackError ? (
          <p className="mt-3 text-sm text-red-400" role="alert">
            {playbackError}
          </p>
        ) : null}

        {searchResult !== null && !searchNoMatch && !searchError ? (
          <div className="mt-3 space-y-2 rounded-md border border-zinc-700 bg-zinc-950/50 p-3 text-sm text-zinc-200">
            <p className="font-medium text-zinc-100">{fr.homeSearchSnippetTitle}</p>
            <MacroContextWithHighlight match={searchResult} />
            <p className="text-xs text-zinc-500">{matchQualityLabel(searchResult.match_quality)}</p>
            {playbackFromLabel ? (
              <p className="text-sm text-emerald-400/90">{playbackFromLabel}</p>
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}
