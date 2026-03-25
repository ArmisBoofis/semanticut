"use client";

import React, { useEffect, useRef } from "react";

type Props = {
  videoId: string;
  /** When set, seek playback to this offset (seconds). */
  seekToSeconds: number | null;
  /** Bump on each successful search so repeated seeks to the same timestamp still run. */
  seekKey: number;
  /** Called after media seek completion for the active seek key. */
  onSeeked?: (seconds: number, seekKey: number) => void;
};

export function SemanticVideoPlayer({
  videoId,
  seekToSeconds,
  seekKey,
  onSeeked,
}: Props) {
  const ref = useRef<HTMLVideoElement | null>(null);
  /** Parent often passes an inline handler; keep it out of effect deps so list re-renders / polling do not re-seek. */
  const onSeekedRef = useRef(onSeeked);
  onSeekedRef.current = onSeeked;

  const src = `/api/videos/${encodeURIComponent(videoId)}/media`;

  useEffect(() => {
    const el = ref.current;
    if (el === null || seekToSeconds === null) return;
    const t = Math.max(0, seekToSeconds);

    const tryPlay = () => {
      void el.play().catch(async () => {
        // Some browsers block unmuted autoplay after async search callbacks.
        if (el.muted) return;
        el.muted = true;
        await el.play().catch(() => {
          /* user can still press play manually */
        });
      });
    };

    const handleSeeked = () => {
      onSeekedRef.current?.(t, seekKey);
    };

    const handleLoadedMetadata = () => {
      try {
        el.currentTime = t;
        tryPlay();
      } catch {
        /* invalid state */
      }
    };

    const applySeekNow = () => {
      try {
        el.currentTime = t;
        tryPlay();
      } catch {
        /* invalid state */
      }
    };

    try {
      el.addEventListener("seeked", handleSeeked, { once: true });
      if (el.readyState >= HTMLMediaElement.HAVE_METADATA) {
        applySeekNow();
      } else {
        el.addEventListener("loadedmetadata", handleLoadedMetadata, { once: true });
        // Do not call `load()` here: it resets the media pipeline and, combined with
        // frequent re-renders, can leave the decoder stuck on one frame while time advances.
      }
    } catch {
      /* invalid state */
    }
    return () => {
      el.removeEventListener("seeked", handleSeeked);
      el.removeEventListener("loadedmetadata", handleLoadedMetadata);
    };
  }, [seekToSeconds, seekKey, videoId]);

  return (
    <video
      ref={ref}
      className="mt-3 w-full max-w-xl rounded-md border border-zinc-800 bg-black"
      controls
      playsInline
      preload="metadata"
      src={src}
    />
  );
}
