"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { fr } from "@/lib/strings";

const VIDEO_ACCEPT =
  ".mp4,.webm,.mov,.mkv,.avi,.m4v,.mpeg,.mpg,video/mp4,video/webm,video/quicktime";

type Props = {
  onRegistered: () => void;
};

export function RegisterVideoForm({ onRegistered }: Props) {
  const [label, setLabel] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!success) return;
    const t = window.setTimeout(() => setSuccess(null), 4000);
    return () => window.clearTimeout(t);
  }, [success]);

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setError(null);
      setSuccess(null);
      const trimmed = label.trim();
      if (!trimmed) {
        setError(fr.adminRegisterLabelRequired);
        return;
      }
      if (!file) {
        setError(fr.adminRegisterFileRequired);
        return;
      }
      setSubmitting(true);
      try {
        const fd = new FormData();
        fd.set("label", trimmed);
        fd.set("file", file);
        const res = await fetch("/api/videos", {
          method: "POST",
          body: fd,
          signal: AbortSignal.timeout(120_000),
        });
        const data: unknown = await res.json().catch(() => null);
        if (!res.ok) {
          let message = fr.adminRegisterError;
          if (
            typeof data === "object" &&
            data !== null &&
            "error" in data &&
            typeof (data as { error?: { message?: string } }).error?.message ===
              "string"
          ) {
            message = (data as { error: { message: string } }).error.message;
          }
          setError(message);
          return;
        }
        setLabel("");
        setFile(null);
        setSuccess(fr.adminRegisterSuccess);
        onRegistered();
      } catch {
        setError(fr.adminRegisterError);
      } finally {
        setSubmitting(false);
      }
    },
    [file, label, onRegistered],
  );

  return (
    <section
      className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4"
      aria-labelledby="admin-register-heading"
    >
      <h2
        id="admin-register-heading"
        className="text-sm font-medium text-zinc-200"
      >
        {fr.adminRegisterTitle}
      </h2>
      <p className="mt-1 text-xs text-zinc-500">{fr.adminRegisterHint}</p>
      <form className="mt-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end" onSubmit={handleSubmit}>
        <div className="min-w-[12rem] flex-1">
          <label htmlFor="admin-video-label" className="sr-only">
            {fr.adminRegisterLabel}
          </label>
          <input
            id="admin-video-label"
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder={fr.adminRegisterLabelPlaceholder}
            disabled={submitting}
            className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500 disabled:opacity-50"
            autoComplete="off"
          />
        </div>
        <div>
          <label htmlFor="admin-video-file" className="sr-only">
            {fr.adminRegisterFile}
          </label>
          <input
            id="admin-video-file"
            type="file"
            accept={VIDEO_ACCEPT}
            disabled={submitting}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="w-full max-w-xs text-sm text-zinc-300 file:mr-3 file:rounded-md file:border-0 file:bg-zinc-800 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-zinc-200 hover:file:bg-zinc-700 disabled:opacity-50"
          />
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? fr.adminRegisterSubmitting : fr.adminRegisterSubmit}
        </button>
      </form>
      {error && (
        <p className="mt-3 text-sm text-red-400" role="alert">
          {error}
        </p>
      )}
      {success && (
        <p className="mt-3 text-sm text-emerald-400" role="status">
          {success}
        </p>
      )}
    </section>
  );
}
