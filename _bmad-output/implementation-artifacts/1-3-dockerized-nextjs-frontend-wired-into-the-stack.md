# Story 1.3: Dockerized Next.js frontend wired into the stack

Status: review

<!-- Ultimate context engine analysis completed — comprehensive developer guide created. -->

## Story

As a reviewer,
I want a Dockerized Next.js frontend that I can open in the browser and that reaches the FastAPI backend,
so that I can verify full-stack wiring before real features are implemented.

## Acceptance Criteria

1. **Web service up:** Given I run `docker compose up` from the repo root, when the stack is healthy, then a **`web`** service is running **Next.js** (App Router), exposed on a **documented host port** (e.g. **3000**), and I can load a **basic page** in the browser.
2. **Frontend ↔ API wiring:** Given **`web`** and **`api`** are running, when I open the **main page** (root route), then the UI **successfully calls** a **basic backend endpoint** (e.g. `GET /health`) and renders a **simple status** indicating the backend is reachable (e.g. a line showing API health / “Backend OK”) **without** CORS or network errors in normal Docker Compose use.
3. **Reviewer path:** Given I am a new reviewer, when I read the README **Getting Started / Running with Docker** section, then I see a **single copy-paste command** (or a very small set of commands) from **clone → running stack → URL to visit**, with notes on **expected ports** (`web`, `api`, `db`).

## Tasks / Subtasks

- [x] **Scaffold / wire `frontend/`** (AC: 1)
  - [x] Ensure **`frontend/`** exists with **Next.js (App Router)**, **TypeScript**, and **TailwindCSS** (per architecture and epics).
  - [x] Add a minimal **root page** that is enough to prove the app runs (no full product UI yet).
- [x] **Dockerfile + Compose** (AC: 1, 2)
  - [x] Add **`frontend/Dockerfile`** (dev-friendly: bind-mount + `next dev`, or production `next build` + `next start` — **document** the choice; hot reload in dev is a goal per epics).
  - [x] Extend root **`docker-compose.yml`** with a **`web`** service: `build` context **`frontend/`**, **`depends_on`** **`api`** (and transitively **`db`**), publish **`WEB_PORT`** (default **3000**).
  - [x] Pass **API base URL** into the frontend via env (e.g. **`NEXT_PUBLIC_API_URL`** for browser-side calls, and/or server-only **`API_INTERNAL_URL=http://api:8000`** for server-side fetches from inside Compose — see Dev Notes).
- [x] **Call `GET /health` from the UI** (AC: 2)
  - [x] Implement the health display using **one** clear strategy (see **CORS vs proxy** below) so the reviewer sees no console CORS failures.
  - [x] Handle failure states without crashing (e.g. show a short French error line if the API is down).
- [x] **CORS or proxy (required for browser → API)** (AC: 2)
  - [x] If the browser calls **`http://localhost:8000`** (or host:port) **directly**, add **`CORSMiddleware`** on FastAPI for the **`web`** origin(s), driven by env (e.g. **`CORS_ORIGINS`**).
  - [x] **Alternatively**, use a **Next.js Route Handler** or **server component** fetch to **`http://api:8000/health`** inside the Docker network (no CORS for the browser). If you choose this, document that the **browser** never talks to `:8000` directly in this setup.
- [x] **French UI copy (minimal)** (AC: 1–2)
  - [x] All **user-visible** strings on this page in **French** (`fr-FR`), centralized or in a small messages module (per architecture / UX spec — even a placeholder page should not ship English chrome).
- [x] **Documentation** (AC: 3)
  - [x] Update root **`README.md`**: **`docker compose up`** brings up **`db` + `api` + `web`**, ports, and example URLs; align with **`.env.example`** (`WEB_PORT`, any `NEXT_PUBLIC_*` / CORS vars).
- [x] **Verification** (AC: 1–3)
  - [x] Extend **`scripts/verify-compose.sh`** (and **`npm test`**) so CI/static checks know about **`web`** (e.g. `docker compose config` includes `web`, expected env keys documented).

## Dev Notes

### Scope guardrails (this story vs neighbors)

- **In scope:** `web` Docker image, Next.js app shell, Compose wiring, **one** visible proof of **API reachability** (`/health`), README + env docs, Tailwind + TS baseline, **French** UI strings for what ships.
- **Out of scope:** `/videos` flows, admin/primary product pages, video player, Alembic schema work, i18n routing for multiple locales (French-only single locale is enough if strings are centralized).

### Architecture compliance

- **Stack:** Next.js (App Router) + TypeScript + TailwindCSS; REST JSON to FastAPI; Compose is the orchestration for reviewers. [Source: `_bmad-output/planning-artifacts/architecture.md` — Frontend Architecture, Infrastructure & Deployment]
- **Services:** **`api`**, **`db`**, **`web`** on Docker Compose; env via `.env` / `.env.example`. [Source: `architecture.md` — Infrastructure & Deployment]
- **API:** Success payloads are **unwrapped**; `GET /health` today returns **`{"status":"ok","database":"ok"}`** (200) or **503** with error shape when DB is down — **do not** treat 503 as “OK” in the UI. [Source: `backend/app/main.py`, `architecture.md` — Format Patterns]
- **Naming:** React components **`PascalCase`**, hooks **`useX`**, utilities **`camelCase`** exports in **`camelCase`** files where applicable. [Source: `architecture.md` — Naming Patterns]
- **Localization:** Product UI **French only**; README/API may stay English. [Source: `architecture.md` — Localization & UI language; `ux-design-specification.md` — Localization]

### File structure requirements

- **Monorepo:** Root owns **`docker-compose.yml`**; **`frontend/`** owns the Next.js app (matches README today).
- Suggested layout (adjust if you standardize differently, **document** in README):
  - `frontend/Dockerfile`, `frontend/package.json`, `frontend/next.config.ts` (or `.mjs`)
  - `frontend/app/` — App Router routes (`app/page.tsx` for home)
  - `frontend/components/` — shared UI as needed (minimal for 1.3)
  - Optional: `frontend/messages/fr.json` or `lib/strings.ts` for French copy centralization

### Library / framework requirements

- **Next.js:** Current stable **15.x** or **14.x** App Router line; **React 18+**; **TypeScript** strict or sensible default.
- **TailwindCSS:** v3/v4 per Next.js template; keep **`postcss.config`** / **`tailwind.config`** consistent with the scaffold you choose.
- **Lint/format:** ESLint + Prettier (or Biome) — align with “hot reload and basic linting/formatting” from epics.

### CORS vs server-side fetch (decision guide)

| Approach | Pros | Cons |
|----------|------|------|
| **A. CORS on FastAPI** | Matches future client-side calls to API from the browser | Must list exact origins (e.g. `http://localhost:3000`) and keep env in sync |
| **B. Next.js server fetch to `http://api:8000`** | No CORS for MVP wiring | Browser network tab shows calls to Next, not raw API; still valid for AC if “no CORS errors” |

Pick **one** for the demo path and document it. Many teams use **B** for the home page SSR + **document** `NEXT_PUBLIC_API_URL` for later client hooks.

### Testing requirements

- **Manual (required):**
  - `cp .env.example .env` → `docker compose up --build` → open **`http://localhost:${WEB_PORT:-3000}`** → page shows backend status from **`/health`** without browser console CORS errors.
  - With **`api` stopped** or unhealthy, UI shows a **clear French** error, not a white screen.
- **Automated:** Extend existing **`scripts/verify-compose.sh`** smoke checks; optional Playwright later — not required for 1.3 if scope stays tight.

### Previous story intelligence (Story 1.2)

- **`GET /health`** is implemented at **`/health`** with body **`{"status":"ok","database":"ok"}`** when DB is up; **503** when DB check fails. [Source: `backend/app/main.py`]
- **Compose:** **`api`** uses **`depends_on: db: condition: service_healthy`**; **`DATABASE_URL`** built from **`POSTGRES_*`**. **`web`** should **`depends_on`** **`api`** so the API is up before the reviewer hits the UI (ordering — health still handles transient failures).
- **Env contract:** Reuse **`.env.example`** pattern; add **`WEB_PORT`**, **`NEXT_PUBLIC_API_URL`** (if used), **`CORS_ORIGINS`** (if used). Do not fork a second conflicting source of truth for DB vars.
- **Verification:** **`npm test`** runs **`scripts/verify-compose.sh`** — extend rather than replace.

### Git / codebase intelligence

- Latest work: **FastAPI + DB health** (`feat: Fast API base template with db healthcheck`), Docker PostgreSQL setup. **`frontend/`** is expected by README but **not yet** wired in **`docker-compose.yml`** — this story **adds** the **`web`** service and real Next.js app if the folder is empty or stub.

### Latest technical specifics

- **Docker networking:** From **`web`** container, API hostname is **`api`**, port **8000** (internal). From **host browser**, API is **`localhost:${API_PORT:-8000}`** if calling API directly.
- **Next.js in Docker:** For **dev**, mount source and run **`next dev -H 0.0.0.0`**; for **prod-like**, multi-stage build and **`next start`**. Document which mode **`docker compose up`** uses by default.
- **Node:** Pin **Node 20 LTS** or **22** in Dockerfile to match Next.js support matrix.

### Project context reference

- No **`project-context.md`** found in repo; authoritative planning sources remain **`epics.md`**, **`architecture.md`**, **`ux-design-specification.md`**.

### References

- Epic & AC: `_bmad-output/planning-artifacts/epics.md` — Epic 1, Story 1.3.
- PRD / FR5: `_bmad-output/planning-artifacts/prd.md` — Docker Compose full stack.
- Architecture: `_bmad-output/planning-artifacts/architecture.md` — frontend stack, Compose services, naming, errors, French UI.
- UX: `_bmad-output/planning-artifacts/ux-design-specification.md` — French-only product UI, reviewer-first clarity.

## Dev Agent Record

### Agent Model Used

Cursor agent

### Debug Log References

### Completion Notes List

- Implemented Next.js **15.5.14** (App Router) + TypeScript + TailwindCSS under `frontend/` with French copy in `lib/strings.ts`.
- Server-side fetch to FastAPI **`GET /health`** via **`API_INTERNAL_URL`** (Compose: `http://api:8000`; local host dev: `http://127.0.0.1:8000`) — **approach B**, no CORS in the browser.
- Added **`web`** service + named volumes for `node_modules` + `.next`, bind-mount for source, **`docker-entrypoint.sh`** runs **`npm ci`** when `node_modules` volume is empty.
- Extended **`.env.example`**, **`docker-compose.yml`**, **`README.md`**, **`scripts/verify-compose.sh`**; Vitest unit tests for `isBackendHealthyPayload`.
- Verified: `npm test` (root), `cd frontend && npm test`, `npm run lint`, `npm run build`, `docker compose build web`.

### File List

- `docker-compose.yml`
- `.env.example`
- `README.md`
- `scripts/verify-compose.sh`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/tsconfig.json`
- `frontend/next.config.ts`
- `frontend/next-env.d.ts`
- `frontend/postcss.config.mjs`
- `frontend/tailwind.config.ts`
- `frontend/eslint.config.mjs`
- `frontend/vitest.config.ts`
- `frontend/Dockerfile`
- `frontend/docker-entrypoint.sh`
- `frontend/.dockerignore`
- `frontend/.gitignore`
- `frontend/README.md`
- `frontend/app/globals.css`
- `frontend/app/layout.tsx`
- `frontend/app/page.tsx`
- `frontend/lib/strings.ts`
- `frontend/lib/health.ts`
- `frontend/lib/health.test.ts`
- `frontend/lib/fetchBackendHealth.ts`
- `_bmad-output/implementation-artifacts/1-3-dockerized-nextjs-frontend-wired-into-the-stack.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- **2026-03-21:** Story context created (create-story workflow); status `ready-for-dev`.
- **2026-03-21:** Implemented Story 1.3 — Next.js `web` service, server-side `/health` wiring, French UI, Docker Compose, docs, Vitest; status `review`.
