# semanticut — frontend

Next.js (App Router) + TypeScript + TailwindCSS. Product UI copy is **French** (`fr-FR`).

- **Local dev (host):** `npm ci && export API_INTERNAL_URL=http://127.0.0.1:8000 && npm run dev`
- **Docker (demo / prod-like):** the root `docker-compose.yml` **`web`** image runs **`next build`** and **`node server.js`** (standalone). Rebuild after UI changes: `docker compose build web && docker compose up -d web`.

The home page calls **`GET /health`** on the API from the **Next.js server** (no browser CORS).

The **admin** list (`/admin`) polls **`/api/videos`**, a Route Handler that proxies **`GET /videos`** on FastAPI using `API_INTERNAL_URL` (same pattern as health — avoids browser CORS and keeps the API URL server-side only).
