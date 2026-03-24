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
  try {
    const res = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(120_000),
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
    return new NextResponse(res.body, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "no-store",
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
