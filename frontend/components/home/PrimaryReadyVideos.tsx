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
  const { before, mid, after } = splitMacroHighlight(
    match.macro_context_text,
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
  const [seekToSeconds, setSeekToSeconds] = useState<number | null>(null);
  const [seekKey, setSeekKey] = useState(0);

  const abortRef = useRef<AbortController | null>(null);

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
    setSeekToSeconds(null);
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

  const onSubmitSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedId || !query.trim() || searchLoading) return;

    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    setSearchLoading(true);
    setSearchNoMatch(false);
    setSearchError(null);
    setSearchResult(null);
    setSeekToSeconds(null);

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
      setSeekToSeconds(parsed.start_ts);
      setSeekKey((k) => k + 1);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setSearchError(fr.homeSearchGenericError);
    } finally {
      if (!ac.signal.aborted) setSearchLoading(false);
    }
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
          <p className="mt-3 text-sm text-red-400" role="alert">
            {searchError}
          </p>
        ) : null}

        {searchResult !== null && !searchNoMatch && !searchError ? (
          <div className="mt-3 space-y-2 rounded-md border border-zinc-700 bg-zinc-950/50 p-3 text-sm text-zinc-200">
            <p className="font-medium text-zinc-100">{fr.homeSearchSnippetTitle}</p>
            <MacroContextWithHighlight match={searchResult} />
            <p className="text-xs text-zinc-500">{matchQualityLabel(searchResult.match_quality)}</p>
            <p className="text-sm text-emerald-400/90">
              {fr.homeSearchPlaybackFromPrefix}
              {formatSecondsToClock(searchResult.start_ts)}
            </p>
          </div>
        ) : null}
      </div>
    </section>
  );
}
