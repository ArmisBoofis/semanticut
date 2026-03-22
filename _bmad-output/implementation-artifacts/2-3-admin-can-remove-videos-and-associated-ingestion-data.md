# Story 2.3: Admin can remove videos and associated ingestion data

Status: review

<!-- Ultimate context engine analysis completed — comprehensive developer guide created. -->

## Story

As an admin,
I want to remove a video and its associated ingestion data,
so that I can keep the system clean and avoid cluttering the demo environment.

## Acceptance Criteria

1. **API contract:** Given at least one video exists, when the admin UI triggers removal for that video, then the frontend calls **`DELETE /videos/{video_id}`** (path parameter name **`video_id`**, **UUID**), matching `_bmad-output/planning-artifacts/epics.md` Story 2.3 and `architecture.md` REST naming.
2. **Data removal:** Given the delete request succeeds, when the admin list is refreshed or the next poll runs, then the video **no longer appears** in `GET /videos`, and the **`ingestion_jobs`** row for that video is **gone** (CASCADE / explicit delete). **Transcript / embedding tables do not exist yet** in the codebase; when they are added (later epics), their `video_id` foreign keys **must** use **`ON DELETE CASCADE`** (or equivalent) so this story’s guarantee (“no longer present or referenced”) remains true — document any new migration that adds those tables accordingly.
3. **In-flight ingestion:** Given the video was still ingesting (`pending` / `running` / etc.) when deletion was requested, when deletion completes, then the API responds with **success** (see HTTP semantics below) and the admin sees a **clear French** success or error message. **There is no background ingestion worker yet** (Story 2.4); today “cleanup” means **DB + optional file** removal. Add a **short code comment** where a future worker would cancel in-process tasks, so Story 2.4+ can hook cancellation without redesigning the endpoint.
4. **Errors:** Invalid `video_id` format → **400** with standard error shape. Unknown id → **404** with `{ "error": { "code", "message" } }`. All errors remain **French-friendly messages** where user-visible (server `message` may stay concise; frontend maps to `fr` strings when displaying).

## Tasks / Subtasks

- [x] **Backend: `DELETE /videos/{video_id}`** (AC: 1–4)
  - [x] Add **`delete_video`** (or equivalent) in `backend/app/services/video_service.py`: load **`Video`** by id (with `selectinload(Video.ingestion_job)` if needed), raise **`AppError("NOT_FOUND", …, 404)`** if missing.
  - [x] **`session.delete(video)`** (or delete by id) so ORM cascade removes **`IngestionJob`** — relationship on `Video.ingestion_job` already has **`cascade="all, delete-orphan"`**; DB FK **`ingestion_jobs.video_id` → `videos.id`** is **`ON DELETE CASCADE`** [Source: `backend/app/models/video.py`, Alembic initial migration].
  - [x] Return **`204 No Content`** on success (no body), **or** **`200`** with a minimal direct JSON payload — **pick one**, document in OpenAPI; prefer **204** for simple deletes unless the product needs an echo of `id`.
  - [x] Register route on **`videos.router`** with correct **`video_id: UUID`** typing so OpenAPI shows UUID format.
  - [x] **pytest:** happy path delete → subsequent `GET /videos` omits video; `GET` after delete on nested resources if any; **404** for unknown UUID; **400** for malformed path UUID (FastAPI may handle path UUID validation — assert behavior).
- [x] **Optional: storage file** (AC: 2, scope tightly)
  - [x] If product wants demo disk cleanup: only delete files under a **known, documented** root (e.g. same rules as future upload directory), **never** arbitrary absolute paths from `storage_path`; if skipped, note in Dev Notes **“DB-only delete in 2.3”**.
- [x] **Frontend: remove control + proxy** (AC: 1, 3, 4)
  - [x] Extend **`frontend/app/api/videos/`** with a **Route Handler** for **`DELETE`** — e.g. **`frontend/app/api/videos/[video_id]/route.ts`** forwarding to **`DELETE ${API_INTERNAL_URL}/videos/${video_id}`** (mirror **`GET` proxy** pattern in `frontend/app/api/videos/route.ts`).
  - [x] **`AdminVideoList`** (or small child component): per-row **“Supprimer”** (or equivalent) control, **French** labels from **`frontend/lib/strings.ts`**.
  - [x] **Confirmation:** **`Dialog`** (modal) before delete per **`ux-design-specification.md`** — destructive actions require confirm; focus trap / Esc per existing UX spec.
  - [x] On success: **optimistic or refetch** — call existing **`load()`** after delete so list updates; respect **polling** (row should disappear on next tick).
  - [x] On error: show **`fr`** user message; do not expose raw stack traces.
- [x] **Accessibility:** button has clear **accessible name**; dialog **title** describes irreversible action.
- [x] **Out of scope:** Do **not** implement Story **2.4** worker; do **not** add registration upload form (**2.5**).

## Dev Notes

### Scope guardrails (this story vs neighbors)

- **In scope:** **`DELETE /videos/{video_id}`**, DB cleanup of **video + ingestion job**, admin UI **remove** with **confirm**, **French** copy, **Next.js proxy** for DELETE.
- **Out of scope:** Async pipeline implementation (**2.4**), multipart upload UI (**2.5**), **auth**.

### Architecture compliance

- **REST:** `DELETE /videos/{video_id}` [Source: `architecture.md` — API Naming; epics Story 2.3].
- **JSON:** Success = **direct payload or empty** per chosen status; errors = **`{ "error": { "code", "message" } }`** [Source: `architecture.md` — Format Patterns].
- **Naming:** Path param **`video_id`**, JSON **snake_case** if any response body.
- **Frontend:** Next.js App Router, Tailwind, **French-only** user-visible strings [Source: `architecture.md` — Localization].
- **State:** Local state + existing fetch pattern in **`AdminVideoList`** [Source: `2-2` story].

### File structure requirements

- **Backend:** `backend/app/routers/videos.py`, `backend/app/services/video_service.py`, optionally `backend/app/schemas/video.py` only if a small response model is needed.
- **Frontend:** `frontend/components/admin/AdminVideoList.tsx`, `frontend/lib/strings.ts`, new **`frontend/app/api/videos/[video_id]/route.ts`** (or equivalent dynamic segment).
- **Tests:** `backend/tests/test_videos_api.py`.

### Library / framework requirements

- **FastAPI** + **SQLAlchemy 2 async** (existing).
- **Next.js 15** / **React 19** (existing). Use **`Dialog`** from the same UI approach as the rest of the app — if no Radix/shadcn yet, implement a minimal accessible modal (focus trap, Esc) consistent with **`ux-design-specification.md`** modals section.

### UX compliance

- **Destructive action:** Confirm in **Dialog** before delete; use **semantic destructive** styling where applicable [Source: `ux-design-specification.md` — Admin / destructive / Modals].

### Data model notes

- **`videos`** + **`ingestion_jobs`** only today; no **`transcript_segments`** / **`embeddings`** tables in repo yet. **Acceptance criterion 2** requires forward-looking **CASCADE** when those tables appear.
- **`IngestionJob.video_id`** → **`videos.id`** **`ON DELETE CASCADE`** at DB level [Source: Alembic `20260321_0001_initial_videos_and_ingestion_jobs.py`].

### API sketch

**`DELETE /videos/{video_id}`**

- **204:** No body (recommended).
- **404:** `{ "error": { "code": "NOT_FOUND", "message": "…" } }` (message can be English for logs/API consistency or French if you standardize all API messages — **prefer one convention**; frontend **`fr`** strings are authoritative for UI.)

### Testing requirements

- **pytest:** Delete existing video → list count decreases; job row gone (query `ingestion_jobs` or infer from list); unknown UUID → 404.
- **vitest (optional):** Thin test for “delete button triggers fetch with DELETE” or URL builder — follow **`frontend/lib/ingestionStatus.test.ts`** style.

### Previous story intelligence (2.2)

- Admin list lives at **`/admin`**, **`AdminVideoList`** polls **`/api/videos`** every **8 s** [Source: `2-2-admin-page-listing-all-videos-with-ingestion-status.md`].
- **Proxy:** `API_INTERNAL_URL` in Route Handler — **reuse** for **`DELETE`** [Source: `frontend/app/api/videos/route.ts`].
- **Do not** break **`GET /videos`** list shape or **`VideoListItem`** fields.

### Git intelligence (recent commits)

- **`b6385a2`** — Admin listing, **`GET /videos`** extended with phase/progress, **`/api/videos`** proxy, French strings.
- **`15575b4`** — Video registration, models, **`POST/GET /videos`**.

### Latest technical notes

- **FastAPI:** `UUID` path parameters validate format automatically; wrong format → **422** unless customized — align tests with actual behavior or add a custom validator if you need **400** with **`AppError`** shape.
- **SQLAlchemy:** `await session.delete(video); await session.commit()` in the router or service — keep **transaction** boundaries consistent with **`POST /videos`**.

### Project context reference

- No `project-context.md` in repo; rely on this file + **`architecture.md`** + **`epics.md`** + **`ux-design-specification.md`**.

### Implementation note (2.3)

- **DB-only delete in 2.3:** No filesystem removal of `storage_path`; disk cleanup can follow when a single documented media root exists (e.g. Story 2.5 upload directory).

## References

- `_bmad-output/planning-artifacts/epics.md` — Epic 2, Story 2.3
- `_bmad-output/planning-artifacts/architecture.md` — API, formats, localization, structure
- `_bmad-output/planning-artifacts/ux-design-specification.md` — Destructive actions, dialogs, French UI
- `_bmad-output/implementation-artifacts/2-2-admin-page-listing-all-videos-with-ingestion-status.md` — admin UI patterns, proxy, file list
- `backend/app/models/video.py`, `backend/app/routers/videos.py`, `backend/app/services/video_service.py`
- `frontend/components/admin/AdminVideoList.tsx`, `frontend/app/api/videos/route.ts`, `frontend/lib/strings.ts`

## Dev Agent Record

### Agent Model Used

_(filled by implementer)_

### Debug Log References

### Completion Notes List

- Implemented `DELETE /videos/{video_id}` with **204 No Content**; `delete_video` in service with Story **2.4+** cancellation hook comment; `Video` delete cascades ORM + DB FK to `ingestion_jobs`.
- **400** for malformed UUID via existing `RequestValidationError` handler (maps to `VALIDATION_ERROR`).
- Next.js **`DELETE`** proxy at `app/api/videos/[video_id]/route.ts`; admin table column **Supprimer** + native `<dialog>` confirm modal (`DeleteVideoConfirmDialog`); French strings; success/error banner; refetch via `load()` after delete.
- **DB-only** in 2.3 (no storage file deletion); documented in Dev Notes.
- Tests: pytest coverage for delete happy path, job count, running status, 404, 400; full backend `16 passed` in Docker with `TEST_DATABASE_URL`; frontend `npm run build` + vitest OK.

### File List

- `backend/app/services/video_service.py`
- `backend/app/routers/videos.py`
- `backend/tests/test_videos_api.py`
- `frontend/app/api/videos/[video_id]/route.ts`
- `frontend/components/admin/AdminVideoList.tsx`
- `frontend/components/admin/DeleteVideoConfirmDialog.tsx`
- `frontend/lib/strings.ts`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-22 — Story 2.3: DELETE video API, admin remove UI with confirm dialog, French copy, pytest and build verification.
