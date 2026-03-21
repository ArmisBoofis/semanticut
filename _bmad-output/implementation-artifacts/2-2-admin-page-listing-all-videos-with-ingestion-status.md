# Story 2.2: Admin page listing all videos with ingestion status

Status: review

<!-- Ultimate context engine analysis completed — comprehensive developer guide created. -->

## Story

As an admin,
I want an admin page that lists all videos and their ingestion status,
so that I can see what is being processed and what is ready for search.

## Acceptance Criteria

1. **List with status and progress:** Given multiple videos exist with different ingestion states (e.g. `pending`, `running`, `completed`, `failed`), when I open the admin page in the frontend, then I see a table or list of **all** videos (including those still ingesting) with:
   - Video **label** (or identifier),
   - Current **ingestion status**,
   - A **basic progress indicator** — **percentage** and/or **phase name** (whichever is available from the API; both columns if both exist).
2. **Polling:** Given some videos are still ingesting, when I stay on the admin page, then ingestion status (and progress) **updates periodically** via polling **without a full page reload** (epics allow `GET /videos` and/or `GET /videos/{video_id}/status` — implement polling against the list endpoint unless you add the per-status route in this story).
3. **Partial jobs:** Given incomplete ingestion jobs exist, when I view the admin list, then each partially ingested video appears with its **current** ingestion status and **visible** progress (phase and/or percent).

## Tasks / Subtasks

- [x] **Backend: expose progress fields on list** (AC: 1, 3)
  - [x] Extend `VideoListItem` in `backend/app/schemas/video.py` with nullable fields aligned to DB: `ingestion_phase` (`str | null`) and `ingestion_progress_percent` (`int | null` — match `ingestion_jobs.progress_percent`), sourced from `video.ingestion_job` when present.
  - [x] Update `GET /videos` handler in `backend/app/routers/videos.py` to populate these fields (reuse `ingestion_status_for_video` pattern; keep **snake_case** JSON per architecture).
  - [x] Keep **direct** array response (no wrapper). OpenAPI should reflect new fields.
  - [x] Add/adjust API tests (e.g. `backend/tests/test_videos_api.py`) asserting list items include phase/progress when set (mock or DB fixture as per existing test strategy).
- [x] **Frontend: admin route** (AC: 1–3)
  - [x] Add an **App Router** page under **`frontend/app/admin/`** (e.g. `page.tsx`) dedicated to the admin list.
  - [x] **French-only** UI copy for headings, column labels, empty state, loading, and error surfaces — extend `frontend/lib/strings.ts` (or a dedicated `messages` module); **no English chrome** in the browser for these strings [Source: `ux-design-specification.md` — Localization; `architecture.md` — Localization].
  - [x] Render a **responsive** table or list (Tailwind, consistent with existing dark/zinc styling on `app/page.tsx`).
  - [x] **Map** raw API status values (`pending`, `running`, `completed`, `failed`, `unknown`, …) to **French** labels for display (badges or text); keep raw values only for internal logic if needed.
  - [x] **Progress:** show **phase** text when non-null; show **percent** when non-null (e.g. progress bar or numeric); if both null, show `—` or a short French placeholder (e.g. *« — »* / *« non disponible »*) without implying fake progress.
- [x] **Frontend: polling (client)** (AC: 2)
  - [x] Implement a **client component** (or hook) that polls on an interval (e.g. **5–10 s**; document chosen interval) while the admin page is mounted.
  - [x] **No full reload:** use `fetch` + state updates; **no** `location.reload()`.
  - [x] **Accessibility:** use `aria-live="polite"` on the list region so status changes are announced without being noisy.
- [x] **Frontend: same-origin API access** (AC: 1–3)
  - [x] Avoid browser CORS issues: either (A) add a **Next.js Route Handler** (e.g. `frontend/app/api/videos/route.ts`) that **proxies** `GET` to FastAPI using `API_INTERNAL_URL` (same pattern as `fetchBackendHealth`), and have the client poll **`/api/videos`**; **or** (B) enable **FastAPI CORS** for the web origin and use `NEXT_PUBLIC_*` base URL — **pick one approach** and document in `frontend/README.md` if it exists, else root `README` / `frontend` notes. **Recommended:** **proxy route** to reuse `API_INTERNAL_URL` in Docker without exposing `localhost:8000` to the browser.
- [x] **Navigation (minimal)** (AC: 1)
  - [x] Add a small link from the home page to **Admin** (`/admin`) and/or from admin back to home — French labels, unobtrusive (full IA is Story 3+).
- [x] **Tests** (AC: 1–3)
  - [x] Backend: list response includes new fields (see above).
  - [x] Frontend: at least one **Vitest** test for a pure helper (e.g. status → French label mapping) or fetch parsing; optional smoke test for hook timing if practical — follow existing `frontend/lib/health.test.ts` style.
- [x] **Out of scope guardrail:** Do **not** implement **delete** UI (Story **2.3**), **registration** form (unless you add a tiny dev-only curl note in README — optional), or the **async ingestion pipeline** (Story **2.4**). Do **not** implement `GET /videos/{id}/status`** unless needed to satisfy AC — prefer extending list payload + polling `GET /videos`.

## Dev Notes

### Scope guardrails (this story vs neighbors)

- **In scope:** Admin **read-only** list of all videos, **polling**, **French** UI, API list fields for **phase** + **progress** if present in DB.
- **Out of scope:** `DELETE /videos/{id}`, ingestion worker, **primary** search page filtering (Story **3.1**).

### Architecture compliance

- **Stack:** Next.js App Router + TypeScript + Tailwind; FastAPI + Pydantic; JSON **snake_case**; success = **direct** payloads; errors = `{ "error": { "code", "message" } }`. [Source: `architecture.md` — Core decisions, Format Patterns, Naming Patterns]
- **Frontend patterns:** Local state + hooks; explicit loading/error flags; **French** user-facing messages. [Source: `architecture.md` — Communication Patterns, Localization]
- **Feature organization:** Prefer **feature-based** folders under `frontend/` (e.g. `components/admin/` or colocate under `app/admin/`) per architecture. [Source: `architecture.md` — Structure Patterns]

### File structure requirements

- **Backend:** `backend/app/schemas/video.py`, `backend/app/routers/videos.py`, tests under `backend/tests/`.
- **Frontend:** `frontend/app/admin/page.tsx`, client polling component(s), `frontend/lib/strings.ts` (or split admin strings), optional `frontend/app/api/videos/route.ts` for proxy.
- **Do not** rename existing **`GET /videos`** contract keys already used by Story 2.1 (`id`, `label`, `ingestion_status`, `created_at`) — only **add** fields.

### Library / framework requirements

- **Next.js** 15.x, **React** 19.x (already in `frontend/package.json`).
- No new global state library; no `next-intl` required for this story if a single `fr` strings object remains sufficient — **do not** introduce heavy i18n unless you migrate all strings consistently.

### API contract hints (extend existing)

**`GET /videos`** — each item should include at minimum:

```json
{
  "id": "<uuid>",
  "label": "…",
  "ingestion_status": "pending",
  "ingestion_phase": null,
  "ingestion_progress_percent": null,
  "created_at": "<iso8601>"
}
```

When Story 2.4 sets `phase` / `progress_percent`, the admin UI must show them without further schema changes.

### Testing requirements

- **pytest** (async) for API list shape.
- **vitest** for frontend helpers as above.

### Previous story intelligence (2.1)

- **`GET /videos`** already lists videos ordered by `created_at` descending with `ingestion_status` from `ingestion_jobs.status`. [Source: `backend/app/services/video_service.py`, `backend/app/routers/videos.py`]
- **`IngestionJob`** already has **`phase`** and **`progress_percent`** columns — they were nullable for later stories; **this story** exposes them on the list. [Source: `backend/app/models/video.py`]
- **Canonical status** for new jobs: **`pending`**. [Source: `2-1-admin-can-register-videos-for-ingestion.md`]
- **Docker:** `web` service has `API_INTERNAL_URL` for server-side fetch. [Source: `docker-compose.yml`]

### Git intelligence (recent commits)

- Recent: `feat: backend video registration` — models, Alembic, `POST/GET /videos`, structured errors. Build admin UI on this contract; extend list response only as above.

### Latest technical notes

- **Route Handlers** in Next.js App Router: `GET` handler can forward to FastAPI with `fetch` and `cache: 'no-store'` for fresh polling results.
- **React 19** + **Next 15**: client components need `"use client"` where hooks are used.

### Project context reference

- No `project-context.md` in repo; rely on this file + `architecture.md` + `epics.md` + `ux-design-specification.md`.

## References

- `_bmad-output/planning-artifacts/epics.md` — Epic 2, Story 2.2 (acceptance criteria)
- `_bmad-output/planning-artifacts/architecture.md` — API formats, naming, frontend patterns, localization
- `_bmad-output/planning-artifacts/ux-design-specification.md` — French UI, ingestion transparency, progress honesty
- `_bmad-output/implementation-artifacts/2-1-admin-can-register-videos-for-ingestion.md` — prior implementation notes and file list
- `backend/app/models/video.py`, `backend/app/schemas/video.py`, `backend/app/routers/videos.py`
- `frontend/app/page.tsx`, `frontend/lib/fetchBackendHealth.ts`, `frontend/lib/strings.ts`

## Dev Agent Record

### Agent Model Used

Composer (Cursor agent)

### Debug Log References

### Completion Notes List

- Extended `GET /videos` list items with `ingestion_phase` and `ingestion_progress_percent` from `ingestion_jobs`; added service helpers and API tests (including DB update for phase/progress).
- Admin UI at `/admin`: French strings, responsive table, status badges, phase column, progress bar + percent when available, polling every 8 s via `/api/videos` proxy.
- Adjusted `video_client` fixture: `httpx.ASGITransport` no longer accepts `lifespan` in httpx 0.28 (fixes integration tests when `TEST_DATABASE_URL` is set).

### File List

- `backend/app/schemas/video.py`
- `backend/app/services/video_service.py`
- `backend/app/routers/videos.py`
- `backend/tests/test_videos_api.py`
- `backend/tests/conftest.py`
- `frontend/app/page.tsx`
- `frontend/app/admin/page.tsx`
- `frontend/app/api/videos/route.ts`
- `frontend/components/admin/AdminVideoList.tsx`
- `frontend/lib/strings.ts`
- `frontend/lib/ingestionStatus.ts`
- `frontend/lib/ingestionStatus.test.ts`
- `frontend/README.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/2-2-admin-page-listing-all-videos-with-ingestion-status.md`

### Change Log

- 2026-03-21: Story 2.2 — admin video list with ingestion status, polling, French UI, list API phase/progress fields.