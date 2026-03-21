# semanticut — frontend

Next.js (App Router) + TypeScript + TailwindCSS. Product UI copy is **French** (`fr-FR`).

- **Local dev (host):** `npm ci && export API_INTERNAL_URL=http://127.0.0.1:8000 && npm run dev`
- **Docker:** see repository root `README.md` — `web` service uses `API_INTERNAL_URL=http://api:8000` for server-side fetches to FastAPI.

The home page calls **`GET /health`** on the API from the **Next.js server** (no browser CORS).

The **admin** list (`/admin`) polls **`/api/videos`**, a Route Handler that proxies **`GET /videos`** on FastAPI using `API_INTERNAL_URL` (same pattern as health — avoids browser CORS and keeps the API URL server-side only).
