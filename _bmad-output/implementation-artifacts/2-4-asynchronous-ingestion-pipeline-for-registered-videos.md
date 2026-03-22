# Story 2.4: Asynchronous ingestion pipeline for registered videos

Status: review

<!-- Ultimate context engine analysis completed — comprehensive developer guide created. -->

## Story

As an admin,
I want a background ingestion pipeline that processes registered videos through audio extraction, transcription, chunking, embeddings, and indexing,
so that videos become searchable without blocking the UI and with clear status reporting.

## Acceptance Criteria

1. **Async execution:** Given a video has been registered via `POST /videos`, when the ingestion job starts, then it runs **outside the HTTP request lifecycle** (dedicated worker process, separate Compose service, or equivalent — **not** a blocking call inside `POST /videos`) and transitions through well-defined job states: `pending` → `running` → `completed` or `failed`.
2. **Observable progress:** Given an ingestion job is running, when the admin polls **`GET /videos`** or **`GET /videos/{video_id}/status`**, then the response exposes at least **current phase** (e.g. `extracting_audio`, `transcribing`, `chunking`, `embedding`, `indexing` — align names in code and OpenAPI) and an **overall progress** indicator (`ingestion_jobs.progress_percent` 0–100 and/or phase step index documented in Dev Notes).
3. **Success outcome:** Given ingestion completes successfully, when status is fetched, then **`ingestion_jobs.status`** is `completed`, and **persisted** `transcript_segments` (with `start_ts` / `end_ts` / text) plus **embeddings** (pgvector) exist for that `video_id` so Epic 3 search can run against real data — i.e. add the **schema + migrations** missing today (only `videos` + `ingestion_jobs` exist in `20260321_0001_initial_videos_and_ingestion_jobs.py`).
4. **Failure outcome:** Given ingestion fails at any step, when the admin views the list or status endpoint, then **`status`** is `failed`, internal details are **logged** server-side, and the API exposes a **concise, safe** failure hint for the UI (extend `ingestion_jobs` with something like `error_message` / `error_code` if needed — avoid raw stack traces in JSON).
5. **Architecture alignment:** New endpoints and fields follow `architecture.md` (snake_case, `GET /videos/{video_id}/status`, direct JSON success payloads, wrapped errors `{ "error": { "code", "message" } }`).
6. **Deletion interaction:** The worker must tolerate **video/job deletion** (Story 2.3): if a row disappears mid-run, the worker should exit cleanly without crashing the process; wire **cancellation** into the hook left in `delete_video` in `video_service.py` if using in-process tasks, or ensure the worker checks DB existence before each phase.

## Tasks / Subtasks

- [x] **Schema & migrations**
  - [x] Add `transcript_segments` and embeddings storage (dedicated `embeddings` table or `vector` on segments per `architecture.md`).
  - [x] Extend `ingestion_jobs` if needed: `error_message` (nullable), ensure `phase` / `progress_percent` usage is documented.
  - [x] Alembic revision after `20260321_0001`; enable pgvector in migration if not already enabled at DB level (`CREATE EXTENSION IF NOT EXISTS vector`).
- [x] **Worker / async runner**
  - [x] After `POST /videos` commits, **enqueue** work (DB poll loop, queue, or `asyncio.create_task` only if acceptable for CPU-bound steps — prefer **separate worker** or **subprocess** for ffmpeg/Mistral to keep API responsive).
  - [x] Implement phases: resolve `storage_path` to a readable file inside the demo constraints → extract audio → transcribe (Mistral Voxtral) → chunk → embed (Mistral embeddings) → write DB → set `completed`.
  - [x] Update `phase`, `progress_percent`, `status`, `updated_at` at boundaries; use transactions where appropriate.
- [x] **API**
  - [x] Implement **`GET /videos/{video_id}/status`** with detailed job payload (status, phase, progress, optional error summary).
  - [x] Ensure **`GET /videos`** list items remain consistent with existing `VideoListItem` (already has phase/progress).
- [x] **Config & dependencies**
  - [x] Add **`MISTRAL_API_KEY`** (or project naming) to env and Docker Compose; document in README or `.env.example`.
  - [x] Add **official Mistral Python SDK** (and any ffmpeg invocation — system package in Dockerfile or documented host dependency).
- [x] **Frontend (minimal)**
  - [x] If status shape changes, update **`AdminVideoList`** / types; add **French** labels for new phases in `frontend/lib/strings.ts` (and optionally map phase codes in `ingestionStatus.ts` or adjacent helper).
- [x] **Tests**
  - [x] pytest: registration leaves `pending` then worker transitions (integration test may mock Mistral/ffmpeg or use fixtures — at minimum unit tests for state machine + API contract).
  - [x] Status endpoint: 404 for unknown video, shape matches OpenAPI.

## Dev Notes

### Scope guardrails

- **In scope:** End-to-end async pipeline, DB artifacts for segments + vectors, status API, worker wiring, failure handling, progress fields.
- **Out of scope:** Admin upload form (**Story 2.5**), full search endpoint (**Epic 3**), auth, WebSockets (polling only per architecture).

### Architecture compliance

- **REST:** `GET /videos/{video_id}/status` [Source: `architecture.md` — API & Communication Patterns].
- **Data:** `videos`, `ingestion_jobs`, `transcript_segments`, embeddings/pgvector [Source: `architecture.md` — Data Architecture].
- **JSON:** snake_case; success = direct payload; errors = wrapped `error` object [Source: `architecture.md` — Format Patterns].
- **AI stack:** **Mistral only** for transcription and embeddings — no other providers [Source: `architecture.md`, `prd.md`].
- **Frontend:** French user-visible strings [Source: `architecture.md` — Localization; `config.yaml` `product_ui_language`].

### File structure requirements

- **Backend:** Prefer `backend/app/services/ingestion_service.py` (or `pipeline/`) for orchestration; `backend/app/worker.py` or `backend/app/jobs/` entrypoint if separate process; extend `backend/app/routers/videos.py` or add `routers/ingestion.py` mounted in `main`; models in `backend/app/models/`; new Alembic under `backend/alembic/versions/`.
- **Docker:** Consider a **`worker`** service in `docker-compose.yml` sharing the backend image or a slim variant, same env as `api`, `depends_on: db`, no public ports.
- **Tests:** `backend/tests/` mirroring existing `test_videos_api.py` patterns.

### Library / framework requirements

- **FastAPI** + **SQLAlchemy 2 async** + **asyncpg** (existing).
- **Mistral:** Official SDK — pin version in `backend/requirements.txt` [add at implementation time; verify current stable on PyPI].
- **ffmpeg:** Required for audio extraction from video; install in **`backend/Dockerfile`** or document as system dependency for local runs.

### Pipeline phases (suggested constants)

Align OpenAPI and DB with a single enum or string union in Python, e.g.:

- `extracting_audio` → `transcribing` → `chunking` → `embedding` → `indexing` → done.

Map to **`progress_percent`** monotonically or by step (document the rule in code comments).

### Previous story intelligence (2.3)

- **`delete_video`** in `video_service.py` includes a **Story 2.4+** hook comment for cancelling workers — implement cancellation or cooperative shutdown there [Source: `2-3-admin-can-remove-videos-and-associated-ingestion-data.md`].
- **CASCADE:** New tables referencing `videos.id` must use **`ON DELETE CASCADE`** so delete behavior from 2.3 remains correct.
- **`ingestion_jobs`** already tied 1:1 to `video_id` with unique constraint.

### Git intelligence (recent commits)

- **`b6385a2`** — Admin listing, `GET /videos` with phase/progress fields.
- **`15575b4`** — Video registration, models, `POST/GET /videos`.

### Latest technical notes

- **Worker model:** For long-running CPU/network steps, a **separate container** that polls `ingestion_jobs` for `pending` or uses a simple locking strategy (e.g. `SELECT … FOR UPDATE SKIP LOCKED`) scales better than blocking the API process; aligns with `architecture.md` “background-execution mechanism”.
- **Mistral:** Use current **Voxtral** transcription and **embedding** models per product brief; confirm model IDs from Mistral docs when implementing.
- **pgvector:** Dimension of embedding vectors must match the chosen Mistral embedding model — store dimension in migration or as a documented constant.

### Project context reference

- No `project-context.md` in repo; this file plus `architecture.md` + `epics.md` + `ux-design-specification.md` are authoritative.

### UX compliance

- **Honest progress:** Phase labels + progress — avoid indeterminate-only UI during long ingest [Source: `ux-design-specification.md` — ingestion transparency].
- Admin list already polls **`GET /videos`** every **8 s** [Source: `2-2` story]; richer detail can use **`GET /videos/{video_id}/status`** if you add a call from the UI later (optional for 2.4 if list payload is sufficient).

### Testing requirements

- **pytest:** Cover `GET /videos/{video_id}/status` happy path and 404; job state transitions with test doubles for external APIs where needed.
- Prefer **idempotent** pipeline steps where possible so retries remain safe in future stories.

## References

- `_bmad-output/planning-artifacts/epics.md` — Epic 2, Story 2.4
- `_bmad-output/planning-artifacts/architecture.md` — Data model, API, stack, patterns
- `_bmad-output/planning-artifacts/prd.md` — Ingestion SLA, async pipeline
- `_bmad-output/planning-artifacts/ux-design-specification.md` — Progress and trust during ingest
- `_bmad-output/implementation-artifacts/2-3-admin-can-remove-videos-and-associated-ingestion-data.md` — Delete + cascade + cancellation hook
- `backend/app/models/video.py`, `backend/app/services/video_service.py`, `backend/app/routers/videos.py`
- `backend/alembic/versions/20260321_0001_initial_videos_and_ingestion_jobs.py`

## Dev Agent Record

### Agent Model Used

Cursor / Composer (implementation agent)

### Debug Log References

### Completion Notes List

- Implemented Story 2.4: Alembic `20260322_0002` adds `transcript_segments` with pgvector `embedding vector(1024)` (Mistral `mistral-embed`), `ingestion_jobs.error_message` / `error_code`, and indexes.
- Separate **`worker`** Compose service runs `python -m app.worker`: claims pending jobs with `SELECT … FOR UPDATE SKIP LOCKED`, runs ffmpeg → Mistral Voxtral transcription (HTTP `POST /v1/audio/transcriptions` via `httpx`; embeddings use the official `mistralai` SDK) → chunking → Mistral embeddings → bulk insert segments, updates phase/progress at boundaries (`app/ingestion/phases.py` documents percent rule).
- **`GET /videos/{video_id}/status`** returns `VideoIngestionStatusResponse`; **`delete_video`** calls `request_cancel_ingestion`; worker exits cleanly when the video row is gone (CASCADE) or cancellation is requested.
- Frontend: French phase labels via `frenchIngestionPhaseLabel` in `ingestionStatus.ts`.
- Integration tests require `TEST_DATABASE_URL` and DB credentials matching the running Postgres (see `backend/tests/conftest.py`). Unit tests: `test_ingestion_phases.py`. Status API tests added to `test_videos_api.py`.

### File List

- `backend/alembic/versions/20260322_0002_transcript_segments_and_job_errors.py`
- `backend/alembic/env.py`
- `backend/app/config.py`
- `backend/app/ingestion/__init__.py`
- `backend/app/ingestion/phases.py`
- `backend/app/ingestion/cancellation.py`
- `backend/app/models/__init__.py`
- `backend/app/models/transcript_segment.py`
- `backend/app/models/video.py`
- `backend/app/routers/videos.py`
- `backend/app/schemas/video.py`
- `backend/app/services/ingestion_service.py`
- `backend/app/services/mistral_client.py`
- `backend/app/services/video_service.py`
- `backend/app/worker.py`
- `backend/requirements.txt`
- `backend/Dockerfile`
- `backend/tests/test_ingestion_phases.py`
- `backend/tests/test_videos_api.py`
- `docker-compose.yml`
- `.env.example`
- `data/videos/.gitkeep`
- `frontend/components/admin/AdminVideoList.tsx`
- `frontend/lib/ingestionStatus.ts`

### Change Log

- 2026-03-22: Story 2.4 implementation — async ingestion worker, schema/migrations, status API, Mistral + ffmpeg, frontend phase labels, tests.
