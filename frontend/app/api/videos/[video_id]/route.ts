import { NextResponse } from "next/server";

function internalBaseUrl(): string {
  return (
    process.env.API_INTERNAL_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000"
  );
}

type RouteContext = { params: Promise<{ video_id: string }> };

/**
 * Proxies `DELETE /videos/{video_id}` to FastAPI (`API_INTERNAL_URL`).
 */
export async function DELETE(_request: Request, context: RouteContext) {
  const { video_id } = await context.params;
  const url = `${internalBaseUrl()}/videos/${encodeURIComponent(video_id)}`;
  try {
    const res = await fetch(url, {
      method: "DELETE",
      signal: AbortSignal.timeout(15_000),
    });
    if (res.status === 204) {
      return new NextResponse(null, { status: 204 });
    }
    let payload: unknown;
    try {
      payload = await res.json();
    } catch {
      payload = {
        error: {
          code: "UPSTREAM_ERROR",
          message: `API a répondu avec le code ${res.status}`,
        },
      };
    }
    return NextResponse.json(payload, { status: res.status });
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
