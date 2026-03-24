import { NextResponse } from "next/server";

function internalBaseUrl(): string {
  return (
    process.env.API_INTERNAL_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000"
  );
}

type RouteContext = { params: Promise<{ video_id: string }> };

/**
 * Proxies `POST /videos/{video_id}/search` to FastAPI.
 */
export async function POST(request: Request, context: RouteContext) {
  const { video_id } = await context.params;
  const url = `${internalBaseUrl()}/videos/${encodeURIComponent(video_id)}/search`;
  try {
    const body = await request.text();
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      signal: AbortSignal.timeout(120_000),
    });
    const data: unknown = await res.json().catch(() => null);
    if (!res.ok) {
      if (
        typeof data === "object" &&
        data !== null &&
        "error" in data &&
        typeof (data as { error?: unknown }).error === "object" &&
        (data as { error: { code?: string; message?: string } }).error
      ) {
        return NextResponse.json(data, { status: res.status });
      }
      return NextResponse.json(
        {
          error: {
            code: "UPSTREAM_ERROR",
            message: `API a répondu avec le code ${res.status}`,
          },
        },
        { status: 502 },
      );
    }
    return NextResponse.json(data);
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
