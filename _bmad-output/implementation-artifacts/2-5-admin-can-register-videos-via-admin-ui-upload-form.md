# Story 2.5: Admin can register videos via upload form on the admin page

Status: review

<!-- Ultimate context engine analysis completed — comprehensive developer guide created. -->

## Story

As an admin,
I want to register a new video for ingestion using an upload form on the admin page,
so that I can run the demo without calling the HTTP API manually.

## Acceptance Criteria

1. **Happy path:** Given the stack is running and the admin is on the admin page, when they choose a video file and provide required fields (at minimum **label**, aligned with `VideoCreateRequest`) and submit, then the client completes registration using the **same backend outcome as Story 2.1** — i.e. a video row plus pending ingestion job — with **loading** feedback on submit and **success** or **structured error** feedback afterward.
2. **Contract alignment:** Registration must end with the same semantics as `POST /videos` today: persisted `label`, `storage_path` pointing at a file the **worker** can open via `resolve_video_file_path()` in `ingestion_service.py` (relative paths under `VIDEO_STORAGE_ROOT` or absolute paths per existing validation). Choose **multipart upload handled by the API** (preferred: extend FastAPI to accept `multipart/form-data` with file + label, save under `VIDEO_STORAGE_ROOT`, store a **relative** `storage_path` such as `uploads/<uuid>.mp4`) **or** a BFF route that writes the file into the shared volume then calls the existing JSON `POST /videos` — document the chosen approach in Dev Notes and keep OpenAPI accurate.
3. **Error UX:** Given invalid or unsupported input, when the API returns an error, then the admin UI shows a **clear French** message derived from `{ "error": { "code", "message" } }` (same pattern as `AdminVideoList` delete/load paths), with **no** raw stack traces.
4. **List consistency:** Given a successful registration, when the admin views the list (existing **8 s** poll on `GET /videos`), then the new video appears with the same ingestion status behavior as API-registered videos (Story 2.2 / 2.4).

## Tasks / Subtasks

- [x] **Backend — upload path**
  - [x] Implement file intake (multipart or dedicated `POST` sub-route) that saves the file under `settings.video_storage_root`, validates extension via existing rules in `validate_registration` / `_ALLOWED_VIDEO_SUFFIXES`, and calls `create_video_with_job` with a safe `storage_path`.
  - [x] Ensure **path traversal** cannot escape `VIDEO_STORAGE_ROOT` (only allow relative segments like `uploads/<safe_name>`).
  - [x] Return `VideoCreatedResponse` (201) on success; map failures to `AppError` / standard error wrapper (existing middleware).
- [x] **Docker / ops**
  - [x] Mount the same host video directory into the **`api`** service as **read-write** at `VIDEO_STORAGE_ROOT` (today **`worker`** mounts `./data/videos` but **`api`** does not — uploads from the UI will fail or write to an ephemeral layer until this is fixed). Align with `VIDEO_STORAGE_HOST_PATH` / `.env.example`.
- [x] **Frontend — admin form (UX spec)**
  - [x] Add a **section above the table** on the admin page (same route as Story 2.2): file input (`accept` video types matching backend), label field, primary submit, **disabled + loading** while submitting.
  - [x] Call a Next **Route Handler** (e.g. extend `frontend/app/api/videos/route.ts` with `POST`) that proxies multipart to the API or streams the file per chosen design; reuse centralized French copy in `frontend/lib/strings.ts`.
  - [x] On success: optional short confirmation + rely on poll so the new row appears; on error: `Alert` or inline error using mapped API message.
- [x] **Tests**
  - [x] `pytest`: registration via new upload path (or multipart) creates video + job; invalid file type / oversize if enforced.
  - [x] Keep / extend existing JSON `POST /videos` tests unchanged in behavior.

## Dev Notes

### Current implementation facts (do not guess)

- **`POST /videos`** is **JSON-only** today: `VideoCreateRequest` with `label` + `storage_path` (`backend/app/routers/videos.py`, `backend/app/schemas/video.py`).
- **Path resolution:** `resolve_video_file_path()` joins relative `storage_path` with `settings.video_storage_root` (`backend/app/services/ingestion_service.py`).
- **Validation:** `validate_registration()` enforces non-empty label, safe path (no `..`), allowed video suffixes (`backend/app/services/video_service.py`).
- **Admin list:** `AdminVideoList` polls `GET /api/videos` every **8 s**; delete flow shows how to parse structured errors (`frontend/components/admin/AdminVideoList.tsx`).
- **French:** All user-visible strings belong in `frontend/lib/strings.ts` per architecture.

### Architecture compliance

- REST: `POST /videos` remains the registration entry; extend with multipart if needed, or document an additional route — avoid duplicating business rules outside `video_service` / `create_video_with_job`.
- JSON: success = direct payload (`VideoCreatedResponse`); errors = `{ "error": { "code", "message" } }` (`architecture.md` — Format Patterns).
- **No auth** (local POC); **French** UI only (`ux-design-specification.md` — Admin upload form section ~453–472).

### File structure (suggested)

- `backend/app/routers/videos.py` — upload handler or second endpoint.
- `backend/app/services/video_service.py` — optional helper `save_uploaded_video(...)` keeping validation in one place.
- `frontend/app/admin/page.tsx` — compose new form component above `AdminVideoList`.
- `frontend/components/admin/RegisterVideoForm.tsx` (or similar) — form UI only.
- `frontend/app/api/videos/route.ts` — add `POST` proxy.

### Previous story intelligence (2.4)

- Ingestion is **async** (worker); after upload, behavior matches existing **pending → running → …** flow. No change to worker phases required if `storage_path` is correct.
- **`docker-compose.yml`:** add **`volumes`** for `api` matching `worker`’s video mount pattern so API-written files are visible to **`worker`** (worker currently uses `:ro`; ensure written files are readable — same bind mount path inside both containers).

### Git intelligence

- Recent history shows incremental epic 2 work (`feat: Admin page listing…`, `feat: backend video registration`); follow existing **fetch + error mapping** patterns in admin components.

### Latest technical notes

- FastAPI: `UploadFile` + `Form` for multipart; limit upload size if needed (`Starlette` / middleware).
- Next.js Route Handlers: `request.formData()` to forward `File` + fields to FastAPI.

### Project context reference

- No `project-context.md` in repo; authoritative: this file, `epics.md` Story 2.5, `architecture.md`, `ux-design-specification.md` (Admin — video registration).

### Testing requirements

- Backend: extend `backend/tests/test_videos_api.py` (or new module) for multipart success + validation errors.
- Frontend: manual or lightweight test per project norms; no requirement for Playwright in this story unless already standard.

## References

- `_bmad-output/planning-artifacts/epics.md` — Epic 2, Story 2.5
- `_bmad-output/planning-artifacts/architecture.md` — API formats, French UI, stack
- `_bmad-output/planning-artifacts/ux-design-specification.md` — Admin upload form (placement, French, feedback)
- `_bmad-output/planning-artifacts/prd.md` — Admin registration via web UI
- `_bmad-output/implementation-artifacts/2-4-asynchronous-ingestion-pipeline-for-registered-videos.md` — worker, paths, list polling
- `backend/app/routers/videos.py`, `backend/app/services/video_service.py`, `backend/app/services/ingestion_service.py`
- `frontend/components/admin/AdminVideoList.tsx`, `frontend/app/api/videos/route.ts`, `frontend/lib/strings.ts`

## Dev Agent Record

### Agent Model Used

Composer (Cursor agent)

### Debug Log References

### Completion Notes List

- Implemented **`POST /videos/upload`** (multipart `label` + `file`): streams file to `VIDEO_STORAGE_ROOT/uploads/<uuid>.<ext>`, stores relative `storage_path`, reuses `create_video_with_job` / `validate_registration` semantics. Added `VIDEO_UPLOAD_MAX_BYTES` (default 500 MiB) and `python-multipart` dependency.
- **Docker:** `api` service now mounts `VIDEO_STORAGE_HOST_PATH` → `/data/videos` read-write (aligned with worker).
- **Frontend:** `RegisterVideoForm` above the admin table; **`POST /api/videos`** proxies FormData to the API; French copy in `strings.ts`; success/error inline; list refresh via existing 8 s poll after successful register.
- **Tests:** `test_videos_api.py` extended with upload happy path, bad extension, oversize; all 14 tests pass (mounted backend + `TEST_DATABASE_URL` from `.env`).

### File List

- `backend/app/config.py`
- `backend/app/routers/videos.py`
- `backend/app/services/video_service.py`
- `backend/requirements.txt`
- `backend/tests/test_videos_api.py`
- `docker-compose.yml`
- `.env.example`
- `frontend/app/api/videos/route.ts`
- `frontend/components/admin/AdminVideoList.tsx`
- `frontend/components/admin/RegisterVideoForm.tsx`
- `frontend/lib/strings.ts`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/2-5-admin-can-register-videos-via-admin-ui-upload-form.md`

### Change Log

- 2026-03-22: Story 2.5 — multipart admin upload (`POST /videos/upload`), API volume mount, admin form + Next proxy, pytest coverage.
