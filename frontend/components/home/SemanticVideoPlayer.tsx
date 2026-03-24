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
      onSeeked?.(t, seekKey);
    };
    const handleLoadedMetadata = () => {
      try {
        el.currentTime = t;
        tryPlay();
      } catch {
        /* invalid state */
      }
    };
    const handleCanPlay = () => {
      tryPlay();
    };
    const applySeekNow = (): boolean => {
      try {
        el.currentTime = t;
        tryPlay();
        return true;
      } catch {
        return false;
      }
    };

    try {
      el.addEventListener("seeked", handleSeeked, { once: true });
      el.addEventListener("canplay", handleCanPlay, { once: true });
      if (el.readyState >= HTMLMediaElement.HAVE_METADATA) {
        applySeekNow();
      } else {
        el.addEventListener("loadedmetadata", handleLoadedMetadata, { once: true });
        // Force metadata loading before attempting seek/play.
        el.load();
      }
    } catch {
      /* invalid state */
    }
    return () => {
      el.removeEventListener("seeked", handleSeeked);
      el.removeEventListener("loadedmetadata", handleLoadedMetadata);
      el.removeEventListener("canplay", handleCanPlay);
    };
  }, [seekToSeconds, seekKey, onSeeked]);

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
