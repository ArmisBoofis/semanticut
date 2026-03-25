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

function MacroContextWithHighlight({ match }: { match: VideoSearchMatch }) {
  const content = match.macro_context_text ?? match.text;
  const { match_start_offset, match_end_offset } = match;
  if (
    typeof match_start_offset !== "number" ||
    typeof match_end_offset !== "number"
  ) {
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
    match_start_offset,
    match_end_offset,
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
const DEFAULT_SEEK_TIMEOUT_MS = 9_000;

declare global {
  interface Window {
    __SEMANTICUT_SEARCH_TIMEOUT_MS__?: number;
  }
}

type PerVideoState = {
  query: string;
  searchLoading: boolean;
  searchResult: VideoSearchMatch | null;
  searchNoMatch: boolean;
  searchError: string | null;
  isTimeoutError: boolean;
  seekToSeconds: number | null;
  seekKey: number;
  playbackFromLabel: string | null;
  playbackError: string | null;
  isSeeking: boolean;
  seekTimeoutError: string | null;
};

function makeInitialPerVideoState(): PerVideoState {
  return {
    query: "",
    searchLoading: false,
    searchResult: null,
    searchNoMatch: false,
    searchError: null,
    isTimeoutError: false,
    seekToSeconds: null,
    seekKey: 0,
    playbackFromLabel: null,
    playbackError: null,
    isSeeking: false,
    seekTimeoutError: null,
  };
}

export function PrimaryReadyVideos() {
  const [items, setItems] = useState<VideoListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [panelStateByVideoId, setPanelStateByVideoId] = useState<
    Record<string, PerVideoState>
  >({});
  const prevSelectedIdRef = useRef<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const latestSeekKeyRef = useRef(0);
  const seekTimeoutIdRef = useRef<number | null>(null);

  const clearSeekTimeout = useCallback(() => {
    if (seekTimeoutIdRef.current === null) return;
    window.clearTimeout(seekTimeoutIdRef.current);
    seekTimeoutIdRef.current = null;
  }, []);

  const scheduleSeekTimeout = useCallback(
    (videoId: string, activeSeekKey: number) => {
      clearSeekTimeout();
      seekTimeoutIdRef.current = window.setTimeout(() => {
        // Only the latest seek key is allowed to update the UI.
        if (latestSeekKeyRef.current !== activeSeekKey) return;
        setPanelStateByVideoId((prev) => {
          const cur = prev[videoId];
          if (!cur) return prev;
          return {
            ...prev,
            [videoId]: {
              ...cur,
              isSeeking: false,
              seekTimeoutError: fr.homeSearchSeekTimeoutError,
            },
          };
        });
      }, DEFAULT_SEEK_TIMEOUT_MS);
    },
    [clearSeekTimeout],
  );

  const isValidStartTs = (value: unknown): value is number =>
    typeof value === "number" && Number.isFinite(value) && value >= 0;

  const onPlayerSeeked = useCallback(
    (videoId: string, seconds: number, completedSeekKey: number) => {
      if (completedSeekKey !== latestSeekKeyRef.current) return;
      clearSeekTimeout();
      setPanelStateByVideoId((prev) => {
        const cur = prev[videoId];
        if (!cur) return prev;
        return {
          ...prev,
          [videoId]: {
            ...cur,
            isSeeking: false,
            seekTimeoutError: null,
            playbackFromLabel: `${fr.homeSearchPlaybackFromPrefix}${formatSecondsToClock(seconds)}`,
          },
        };
      });
    },
    [clearSeekTimeout],
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
      if (prev === null) return null;
      return items.some((r) => r.id === prev) ? prev : null;
    });
  }, [items]);

  useEffect(() => {
    if (items === null) return;
    setPanelStateByVideoId((prev) => {
      let changed = false;
      const next = { ...prev };
      for (const it of items) {
        if (!next[it.id]) {
          next[it.id] = makeInitialPerVideoState();
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [items]);

  useEffect(() => {
    const prevId = prevSelectedIdRef.current;
    prevSelectedIdRef.current = selectedId;

    // stop in-flight work and pending seek-timeout when switching videos.
    abortRef.current?.abort();
    clearSeekTimeout();
    latestSeekKeyRef.current = 0;

    // Avoid showing transient "seeking..." feedback for a previous video.
    if (prevId && prevId !== selectedId) {
      setPanelStateByVideoId((prev) => {
        const cur = prev[prevId];
        if (!cur) return prev;
        return {
          ...prev,
          [prevId]: { ...cur, isSeeking: false, seekTimeoutError: null },
        };
      });
    }
  }, [selectedId, clearSeekTimeout]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      clearSeekTimeout();
    };
  }, [clearSeekTimeout]);

  const hasReadyVideos = Boolean(items && items.length > 0);
  const searchTimeoutMs =
    typeof window !== "undefined" &&
    Number.isFinite(window.__SEMANTICUT_SEARCH_TIMEOUT_MS__)
      ? Number(window.__SEMANTICUT_SEARCH_TIMEOUT_MS__)
      : DEFAULT_SEARCH_TIMEOUT_MS;

  const startSearch = useCallback(async () => {
    if (!selectedId) return;
    const panel = panelStateByVideoId[selectedId];
    if (!panel) return;
    if (!panel.query.trim() || panel.searchLoading) return;

    abortRef.current?.abort();
    const ac = new AbortController();
    const timeoutId = window.setTimeout(() => {
      ac.abort("timeout");
    }, searchTimeoutMs);
    abortRef.current = ac;

    const videoId = selectedId;
    const currentQuery = panel.query;

    // Reset transient feedback, but keep per-video history in the map.
    setPanelStateByVideoId((prev) => {
      const cur = prev[videoId];
      if (!cur) return prev;
      return {
        ...prev,
        [videoId]: {
          ...cur,
          searchLoading: true,
          searchNoMatch: false,
          searchError: null,
          isTimeoutError: false,
          searchResult: null,
          seekToSeconds: null,
          playbackFromLabel: null,
          playbackError: null,
          isSeeking: false,
          seekTimeoutError: null,
        },
      };
    });
    clearSeekTimeout();

    try {
      const res = await fetch(
        `/api/videos/${encodeURIComponent(videoId)}/search`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(buildSearchRequestBody(currentQuery)),
          signal: ac.signal,
          cache: "no-store",
        },
      );
      const data: unknown = await res.json().catch(() => null);

      if (ac.signal.aborted) return;

      if (!res.ok) {
        if (isNoMatchError(data)) {
          setPanelStateByVideoId((prev) => {
            const cur = prev[videoId];
            if (!cur) return prev;
            return { ...prev, [videoId]: { ...cur, searchNoMatch: true } };
          });
          return;
        }
        setPanelStateByVideoId((prev) => {
          const cur = prev[videoId];
          if (!cur) return prev;
          return {
            ...prev,
            [videoId]: {
              ...cur,
              searchError: extractApiErrorMessage(data, fr.homeSearchGenericError),
            },
          };
        });
        return;
      }

      const parsed = parseSearchSuccess(data);
      if (parsed === null) {
        setPanelStateByVideoId((prev) => {
          const cur = prev[videoId];
          if (!cur) return prev;
          return { ...prev, [videoId]: { ...cur, searchError: fr.homeSearchMalformedResponse } };
        });
        return;
      }

      if (!isValidStartTs(parsed.start_ts)) {
        clearSeekTimeout();
        setPanelStateByVideoId((prev) => {
          const cur = prev[videoId];
          if (!cur) return prev;
          return {
            ...prev,
            [videoId]: {
              ...cur,
              searchResult: parsed,
              isSeeking: false,
              seekTimeoutError: null,
              seekToSeconds: null,
              playbackError: fr.homeSearchUnplayableResult,
            },
          };
        });
        return;
      }

      // Next seekKey enables repeated seeks even to the same timestamp.
      const nextSeekKey = panel.seekKey + 1;
      latestSeekKeyRef.current = nextSeekKey;
      scheduleSeekTimeout(videoId, nextSeekKey);

      setPanelStateByVideoId((prev) => {
        const cur = prev[videoId];
        if (!cur) return prev;
        return {
          ...prev,
          [videoId]: {
            ...cur,
            searchResult: parsed,
            playbackError: null,
            isSeeking: true,
            seekTimeoutError: null,
            seekToSeconds: parsed.start_ts,
            seekKey: nextSeekKey,
          },
        };
      });
    } catch (err) {
      const timeoutAbort =
        err instanceof DOMException &&
        err.name === "AbortError" &&
        ac.signal.reason === "timeout";
      if (timeoutAbort) {
        setPanelStateByVideoId((prev) => {
          const cur = prev[videoId];
          if (!cur) return prev;
          return {
            ...prev,
            [videoId]: {
              ...cur,
              isTimeoutError: true,
              searchError: fr.homeSearchTimeoutError,
            },
          };
        });
        return;
      }
      if (err instanceof DOMException && err.name === "AbortError") return;
      setPanelStateByVideoId((prev) => {
        const cur = prev[videoId];
        if (!cur) return prev;
        return { ...prev, [videoId]: { ...cur, searchError: fr.homeSearchGenericError } };
      });
    } finally {
      window.clearTimeout(timeoutId);
      if (abortRef.current === ac) {
        setPanelStateByVideoId((prev) => {
          const cur = prev[videoId];
          if (!cur) return prev;
          return { ...prev, [videoId]: { ...cur, searchLoading: false } };
        });
      }
    }
  }, [
    selectedId,
    panelStateByVideoId,
    searchTimeoutMs,
    clearSeekTimeout,
    scheduleSeekTimeout,
  ]);

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
        <div className="space-y-2">
          <p className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 text-sm text-zinc-300">
            {fr.homeReadyVideosEmpty}
          </p>
          <p className="text-sm text-zinc-400">{fr.homeSearchNoVideoSelected}</p>
        </div>
      ) : (
        <ul className="space-y-2">
          {items?.map((row) => {
            const isOpen = selectedId === row.id;
            const panel = panelStateByVideoId[row.id];
            return (
              <li
                key={row.id}
                className="rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-3 text-sm text-zinc-100"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium">{row.label}</span>
                  <button
                    type="button"
                    aria-expanded={isOpen}
                    aria-controls={`video-panel-${row.id}`}
                    aria-label={`Afficher le lecteur pour "${row.label}"`}
                    onClick={() => {
                      setSelectedId((prev) => (prev === row.id ? null : row.id));
                    }}
                    className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-zinc-700 bg-zinc-950/50 text-zinc-200 hover:bg-zinc-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500"
                  >
                    <span
                      aria-hidden
                      className={
                        isOpen
                          ? "rotate-180 transition-transform duration-200"
                          : "transition-transform duration-200"
                      }
                    >
                      ▾
                    </span>
                  </button>
                </div>

                <div
                  className="grid transition-[grid-template-rows] duration-300 ease-out motion-reduce:transition-none"
                  style={{ gridTemplateRows: isOpen ? "1fr" : "0fr" }}
                >
                  <div className="min-h-0 overflow-hidden">
                    {isOpen && panel ? (
                      <div
                        id={`video-panel-${row.id}`}
                        className="animate-semanticut-video-panel-open space-y-4 border-t border-zinc-800/80 pt-4"
                      >
                        <SemanticVideoPlayer
                          videoId={row.id}
                          seekToSeconds={panel.seekToSeconds}
                          seekKey={panel.seekKey}
                          onSeeked={(seconds, completedSeekKey) =>
                            onPlayerSeeked(row.id, seconds, completedSeekKey)
                          }
                        />

                        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
                          <h3 className="text-sm font-medium text-zinc-200">
                            {fr.homeSearchHeading}
                          </h3>

                          <form
                            onSubmit={onSubmitSearch}
                            className="mt-3 space-y-3"
                          >
                            <div>
                              <label
                                htmlFor={`home-search-query-${row.id}`}
                                className="block text-xs font-medium uppercase tracking-wide text-zinc-500"
                              >
                                {fr.homeSearchQueryLabel}
                              </label>
                              <input
                                id={`home-search-query-${row.id}`}
                                type="text"
                                value={panel.query}
                                onChange={(e) =>
                                  setPanelStateByVideoId((prev) => {
                                    const cur = prev[row.id];
                                    if (!cur) return prev;
                                    return {
                                      ...prev,
                                      [row.id]: {
                                        ...cur,
                                        query: e.target.value,
                                      },
                                    };
                                  })
                                }
                                placeholder={fr.homeSearchQueryPlaceholder}
                                className="mt-1 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600"
                                disabled={panel.searchLoading}
                                autoComplete="off"
                              />
                            </div>
                            <button
                              type="submit"
                              disabled={
                                selectedId !== row.id ||
                                !panel.query.trim() ||
                                panel.searchLoading
                              }
                              className="rounded-md bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-900 disabled:cursor-not-allowed disabled:opacity-40"
                            >
                              {panel.searchLoading
                                ? fr.homeSearchSubmitting
                                : fr.homeSearchSubmit}
                            </button>
                            {panel.searchLoading ? (
                              <p className="text-sm text-zinc-400" role="status">
                                {fr.homeSearchSubmitting}
                              </p>
                            ) : null}
                          </form>

                          {panel.searchNoMatch ? (
                            <p
                              className="mt-3 text-sm text-amber-200/90"
                              role="status"
                            >
                              {fr.homeSearchNoMatch}
                            </p>
                          ) : null}

                          {panel.searchError ? (
                            <div className="mt-3 space-y-2">
                              <p className="text-sm text-red-400" role="alert">
                                {panel.searchError}
                              </p>
                              {panel.isTimeoutError ? (
                                <button
                                  type="button"
                                  onClick={() => {
                                    void startSearch();
                                  }}
                                  disabled={
                                    panel.searchLoading ||
                                    selectedId !== row.id ||
                                    !panel.query.trim()
                                  }
                                  className="rounded-md border border-zinc-600 px-3 py-1.5 text-sm text-zinc-200 disabled:cursor-not-allowed disabled:opacity-40"
                                >
                                  {fr.homeSearchRetry}
                                </button>
                              ) : null}
                            </div>
                          ) : null}

                          {panel.playbackError ? (
                            <p
                              className="mt-3 text-sm text-red-400"
                              role="alert"
                            >
                              {panel.playbackError}
                            </p>
                          ) : null}

                          {panel.searchResult !== null &&
                          !panel.searchNoMatch &&
                          !panel.searchError ? (
                            <div className="mt-3 space-y-2 rounded-md border border-zinc-700 bg-zinc-950/50 p-3 text-sm text-zinc-200">
                              <p className="font-medium text-zinc-100">
                                {fr.homeSearchSnippetTitle}
                              </p>
                              <MacroContextWithHighlight
                                match={panel.searchResult}
                              />
                              {panel.seekTimeoutError ? (
                                <p
                                  className="text-sm text-red-400"
                                  role="alert"
                                >
                                  {panel.seekTimeoutError}
                                </p>
                              ) : null}
                              {panel.isSeeking ? (
                                <p
                                  className="text-sm text-zinc-400"
                                  role="status"
                                >
                                  {fr.homeSearchSeeking}
                                </p>
                              ) : null}
                              {panel.playbackFromLabel ? (
                                <p className="text-sm text-emerald-400/90">
                                  {panel.playbackFromLabel}
                                </p>
                              ) : null}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {hasReadyVideos && selectedId === null ? (
        <p className="text-sm text-zinc-400">{fr.homeSearchNoVideoSelected}</p>
      ) : null}
    </section>
  );
}
