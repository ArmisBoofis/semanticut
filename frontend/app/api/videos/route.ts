import { NextResponse } from "next/server";

function internalBaseUrl(): string {
  return (
    process.env.API_INTERNAL_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000"
  );
}

/**
 * Proxies `GET /videos` from FastAPI using `API_INTERNAL_URL` (Docker: `http://api:8000`).
 * `cache: "no-store"` keeps polling responses fresh.
 */
export async function GET() {
  const url = `${internalBaseUrl()}/videos`;
  try {
    const res = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
    if (!res.ok) {
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
    const data: unknown = await res.json();
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
