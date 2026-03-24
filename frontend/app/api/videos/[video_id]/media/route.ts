import { NextResponse } from "next/server";

function internalBaseUrl(): string {
  return (
    process.env.API_INTERNAL_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000"
  );
}

type RouteContext = { params: Promise<{ video_id: string }> };

/**
 * Proxies `GET /videos/{video_id}/file` for HTML5 video playback.
 */
export async function GET(_request: Request, context: RouteContext) {
  const { video_id } = await context.params;
  const url = `${internalBaseUrl()}/videos/${encodeURIComponent(video_id)}/file`;
  const incomingRange = _request.headers.get("range");
  try {
    const upstreamHeaders = new Headers();
    if (incomingRange !== null) {
      upstreamHeaders.set("Range", incomingRange);
    }
    const res = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(120_000),
      headers: upstreamHeaders,
    });
    if (!res.ok) {
      const errPayload = await res.json().catch(() => ({
        error: {
          code: "UPSTREAM_ERROR",
          message: `API a répondu avec le code ${res.status}`,
        },
      }));
      return NextResponse.json(errPayload, { status: res.status });
    }
    const contentType = res.headers.get("content-type") ?? "video/mp4";
    const contentRange = res.headers.get("content-range");
    const acceptRanges = res.headers.get("accept-ranges");
    const contentLength = res.headers.get("content-length");
    return new NextResponse(res.body, {
      status: res.status,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "no-store",
        ...(contentRange ? { "Content-Range": contentRange } : {}),
        ...(acceptRanges ? { "Accept-Ranges": acceptRanges } : {}),
        ...(contentLength ? { "Content-Length": contentLength } : {}),
      },
    });
  } catch {
    return NextResponse.json(
      {
        error: {
          code: "UPSTREAM_ERROR",
          message: "Impossible de joindre l’API.",
        },
      },
      { status: 502 },
    );
  }
}
