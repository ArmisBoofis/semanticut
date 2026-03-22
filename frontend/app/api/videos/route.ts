import { NextResponse } from "next/server";

function internalBaseUrl(): string {
  return (
    process.env.API_INTERNAL_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000"
  );
}

/**
 * Proxies multipart registration to `POST /videos/upload` on the API (shared volume + DB row).
 */
export async function POST(request: Request) {
  const url = `${internalBaseUrl()}/videos/upload`;
  try {
    const formData = await request.formData();
    const res = await fetch(url, {
      method: "POST",
      body: formData,
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
    return NextResponse.json(data, { status: 201 });
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
