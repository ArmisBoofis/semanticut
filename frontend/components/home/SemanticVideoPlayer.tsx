"use client";

import React, { useEffect, useRef } from "react";

type Props = {
  videoId: string;
  /** When set, seek playback to this offset (seconds). */
  seekToSeconds: number | null;
  /** Bump on each successful search so repeated seeks to the same timestamp still run. */
  seekKey: number;
};

export function SemanticVideoPlayer({ videoId, seekToSeconds, seekKey }: Props) {
  const ref = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (el === null || seekToSeconds === null) return;
    const t = Math.max(0, seekToSeconds);
    try {
      el.currentTime = t;
      void el.play().catch(() => {
        /* autoplay may be blocked; user can press play */
      });
    } catch {
      /* invalid state */
    }
  }, [seekToSeconds, seekKey, videoId]);

  const src = `/api/videos/${encodeURIComponent(videoId)}/media`;

  return (
    <video
      ref={ref}
      className="mt-3 w-full max-w-xl rounded-md border border-zinc-800 bg-black"
      controls
      preload="metadata"
      src={src}
    />
  );
}
