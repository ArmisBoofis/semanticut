"use client";

import { useCallback, useEffect, useState } from "react";

import { frenchIngestionStatusLabel } from "@/lib/ingestionStatus";
import { fr } from "@/lib/strings";

/** Polling interval while this page is mounted (8 s — within 5–10 s story range). */
const POLL_INTERVAL_MS = 8_000;

export type VideoListItem = {
  id: string;
  label: string;
  ingestion_status: string;
  ingestion_phase: string | null;
  ingestion_progress_percent: number | null;
  created_at: string;
};

function isVideoListPayload(data: unknown): data is VideoListItem[] {
  if (!Array.isArray(data)) return false;
  return data.every(
    (row) =>
      row !== null &&
      typeof row === "object" &&
      "id" in row &&
      "label" in row &&
      "ingestion_status" in row &&
      "created_at" in row,
  );
}

export function AdminVideoList() {
  const [items, setItems] = useState<VideoListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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
            : fr.adminLoadError;
        setError(msg);
        setItems(null);
        return;
      }
      if (!isVideoListPayload(data)) {
        setError(fr.adminInvalidPayload);
        setItems(null);
        return;
      }
      setItems(data);
    } catch {
      setError(fr.adminLoadError);
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

  if (loading) {
    return (
      <p className="text-sm text-zinc-400" role="status">
        {fr.adminLoading}
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

  if (!items || items.length === 0) {
    return <p className="text-sm text-zinc-400">{fr.adminEmpty}</p>;
  }

  return (
    <div
      className="overflow-x-auto rounded-lg border border-zinc-800 bg-zinc-900/50"
      aria-live="polite"
      aria-relevant="text"
    >
      <table className="min-w-full border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-zinc-800 text-zinc-400">
            <th scope="col" className="px-4 py-3 font-medium">
              {fr.adminColLabel}
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              {fr.adminColStatus}
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              {fr.adminColPhase}
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              {fr.adminColProgress}
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => (
            <tr
              key={row.id}
              className="border-b border-zinc-800/80 last:border-0"
            >
              <td className="px-4 py-3 font-medium text-zinc-100">
                {row.label}
              </td>
              <td className="px-4 py-3">
                <span className="inline-flex rounded-full border border-zinc-700 bg-zinc-800/80 px-2.5 py-0.5 text-xs text-zinc-200">
                  {frenchIngestionStatusLabel(row.ingestion_status)}
                </span>
              </td>
              <td className="px-4 py-3 text-zinc-300">
                {row.ingestion_phase ?? fr.adminDash}
              </td>
              <td className="px-4 py-3">
                {row.ingestion_progress_percent != null ? (
                  <div className="flex max-w-xs items-center gap-2">
                    <div className="h-2 flex-1 overflow-hidden rounded bg-zinc-800">
                      <div
                        className="h-full rounded bg-emerald-600/90"
                        style={{
                          width: `${Math.min(100, Math.max(0, row.ingestion_progress_percent))}%`,
                        }}
                      />
                    </div>
                    <span className="tabular-nums text-zinc-400">
                      {row.ingestion_progress_percent}%
                    </span>
                  </div>
                ) : (
                  <span className="text-zinc-500">{fr.adminNoProgress}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
