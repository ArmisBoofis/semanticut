# Story 2.1: Admin can register videos for ingestion

Status: review

<!-- Ultimate context engine analysis completed — comprehensive developer guide created. -->

## Story

As an admin,
I want to register a new video for ingestion,
so that the system can start preparing it for semantic search.

## Acceptance Criteria

1. **Register via API:** Given the stack is running, when I call `POST /videos` with minimal required metadata (at least **label** and a **storage path** or equivalent reference to the video file), then a new row exists in **`videos`** and a related row exists in **`ingestion_jobs`** with status **`pending`** (or **`queued`** — pick one canonical value, document it, and use it consistently through Epic 2).
2. **List includes new video:** Given a video has been registered, when I call `GET /videos`, then the response includes that video with an **initial ingestion status** matching the created job (e.g. `pending`).
3. **Structured errors:** Given invalid payloads or clearly unsupported media/path cases, when I call `POST /videos`, then the response uses the standard error shape `{ "error": { "code", "message" } }` with an appropriate HTTP status (typically **400** for client errors).

## Tasks / Subtasks

- [x] **Database schema & migrations** (AC: 1, 2)
  - [x] Add **`videos`** and **`ingestion_jobs`** tables per architecture (minimal columns for this story: ids, `label`, `storage_path`, timestamps; job: `video_id` FK, `status`, optional `phase`/`progress_percent` nullable for later stories).
  - [x] Introduce **Alembic** (project has SQLAlchemy async + `asyncpg` but **no Alembic yet**): `alembic.ini`, `alembic/env.py`, initial revision creating the two tables and indexes (e.g. index on `ingestion_jobs.video_id`).
  - [x] Ensure **fresh databases** get the schema: document how migrations run locally/Docker (e.g. `alembic upgrade head` before `uvicorn`, or a small entrypoint script — choose one approach and document in `backend/README.md`).
- [x] **SQLAlchemy models & session** (AC: 1, 2)
  - [x] Define models in clearly named modules (e.g. `app/models/` or `app/models.py`) matching table naming: `snake_case` columns, UUID or bigserial PKs — **document** ID type choice.
  - [x] Wire **dependency-injected `AsyncSession`** for route handlers (reuse/extend patterns from `app/db.py` — `async_session_maker` already exists).
- [x] **Pydantic schemas** (AC: 1–3)
  - [x] Request body for `POST /videos`: e.g. `label: str`, `storage_path: str` (both required unless you document optional fields).
  - [x] Response models: success payloads are **direct** (no `{ "data": ... }` wrapper) per architecture; list endpoint returns a **JSON array** of video summaries or a single agreed shape — **document OpenAPI** via FastAPI models.
- [x] **API routes** (AC: 1–3)
  - [x] `POST /videos`: create `Video` + `IngestionJob` in one transaction; return **201** with the created resource representation (include `id`, `label`, `storage_path`, `ingestion_status` / job status).
  - [x] `GET /videos`: return all videos with enough fields for Story 2.2 (at minimum **id**, **label**, **ingestion status**); order by `created_at` descending unless you document otherwise.
  - [x] Map validation and domain errors to **`{ "error": { "code", "message" } }`** (see Architecture — Format Patterns). Use stable **`code`** strings (e.g. `VALIDATION_ERROR`, `UNSUPPORTED_MEDIA`, `INVALID_STORAGE_PATH`).
- [x] **Out of scope guardrail:** Do **not** implement the async ingestion pipeline, background workers, or phase transitions beyond **`pending`** here — that is **Story 2.4**. This story only **persists** registration and exposes list/register APIs.
- [x] **Tests** (AC: 1–3)
  - [x] Add **async** API tests (e.g. `httpx` + `ASGITransport` or FastAPI `AsyncClient`) covering: happy path POST+GET, validation error shape, at least one domain error path.
  - [x] Use a **test database** strategy: SQLite async for speed *only if* models stay portable; otherwise document `DATABASE_URL` to a throwaway Postgres (e.g. same Compose stack, separate DB name) — avoid blocking the dev on heavy infra.
- [x] **Docs & dependencies** (AC: 1–3)
  - [x] Add **alembic** (and **psycopg2-binary** or official sync driver for Alembic offline/online if required by your `env.py` pattern) to `requirements.txt` / lock strategy consistent with the repo.
  - [x] Update **`backend/README.md`**: how to run migrations, example `curl`/`httpie` for `POST /videos` and `GET /videos`.

## Dev Notes

### Scope guardrails (this story vs neighbors)

- **In scope:** Persistence for **`videos`** + **`ingestion_jobs`**, **`POST /videos`**, **`GET /videos`**, standard error JSON, Alembic baseline, tests, README for API/migrations.
- **Out of scope:** Admin UI (Story **2.2**), delete ( **2.3** ), background ingestion / phases / progress ( **2.4** ), file upload multipart handling *unless* you explicitly extend AC — default is **register by path** as in epics (“file/path”).
- **Cross-story:** Story **2.2** will poll `GET /videos` (or per-id status later); keep list items **stable** and **snake_case** field names.

### Architecture compliance

- **Stack:** FastAPI + Pydantic; PostgreSQL + SQLAlchemy + **Alembic**; REST JSON; `snake_case` for JSON and DB. [Source: `_bmad-output/planning-artifacts/architecture.md` — Core Architectural Decisions, Naming Patterns, Format Patterns]
- **Endpoints:** `POST /videos`, `GET /videos` — plural resource. [Source: `architecture.md` — API & Communication Patterns]
- **Success vs errors:** Success = **direct** payload; errors = `{ "error": { "code", "message" } }`. [Source: `architecture.md` — Format Patterns, Process Patterns]
- **Tables:** `videos`, `ingestion_jobs` with FK `video_id`. [Source: `architecture.md` — Data Architecture, Naming Patterns]
- **No auth:** MVP local-only; no tokens. [Source: `architecture.md` — Authentication & Security]

### File structure requirements

- Keep backend layout coherent with existing **`backend/app/`** (`main.py`, `db.py`, `config.py`).
- Suggested additions (adjust names if you standardize differently — **document** in README):
  - `backend/alembic/` — versions + `env.py`
  - `backend/app/models/` — ORM models
  - `backend/app/schemas/` — Pydantic request/response
  - `backend/app/routers/videos.py` — router included from `main.py`
  - `backend/app/services/video_service.py` — optional thin service layer for create/list
- **Register router** in `app/main.py` with a prefix if desired (e.g. no prefix — routes are exactly `/videos`).

### Library / framework requirements

- **FastAPI** ~0.115.x, **Pydantic** v2, **SQLAlchemy** 2.0 async (already pinned). [Source: `backend/requirements.txt`]
- **Alembic:** Use a version compatible with SQLAlchemy 2.0; configure `env.py` for your async URL (common pattern: sync URL for migrations via `postgresql://` + psycopg2, or async template — follow official Alembic + SQLAlchemy 2 docs for the chosen pattern).
- **asyncpg** remains the runtime driver; migration tooling may use a **sync** Postgres driver for Alembic — acceptable and common.

### API contract hints (minimal — refine in implementation)

**`POST /videos`** (request JSON example):

```json
{ "label": "Interview A", "storage_path": "/data/videos/demo.mp4" }
```

**`POST /videos`** (201 response example — direct payload):

```json
{
  "id": "<uuid>",
  "label": "Interview A",
  "storage_path": "/data/videos/demo.mp4",
  "ingestion_status": "pending",
  "created_at": "<iso8601>"
}
```

**`GET /videos`** (200 response example — array):

```json
[
  {
    "id": "<uuid>",
    "label": "Interview A",
    "ingestion_status": "pending",
    "created_at": "<iso8601>"
  }
]
```

Adjust fields to match your models; keep **snake_case**. If `duration` is unknown at registration, omit or use `null`.

**Error example (400):**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "label is required"
  }
}
```

### Testing requirements

- Prefer **pytest** with async support (`pytest-asyncio` if needed).
- Cover: **201** + DB side effects (or response assertions if DB isolation is heavy), **GET** list after POST, **400** + error shape for malformed body.
- Do not weaken **`/health`** behavior from Story 1.2/1.3.

### Previous story intelligence (Epic 1 complete)

- **DB connectivity:** `app/db.py` uses `async_session_maker` and `verify_db_on_startup` — new endpoints should use the same session factory. [Source: `backend/app/db.py`, `backend/app/main.py`]
- **Config:** `DATABASE_URL` or `POSTGRES_*` — migrations must use the same database as the API. [Source: `backend/app/config.py`]
- **Docker:** API Dockerfile currently **copies only `app/`** — adding `alembic/` requires updating **`backend/Dockerfile`** `COPY` lines so migrations exist in the image.
- **Product UI French** applies to **browser** strings (Epic 2 frontend stories); **API error messages** can remain concise English unless UX spec says otherwise — structured `code` is for clients. [Source: `architecture.md` — Localization; epics Story 2.1 is API-centric]

### Git intelligence (recent commits)

- Recent work established **FastAPI health**, **async SQLAlchemy**, **Next.js + Compose** — this story is the first **domain schema + REST** feature; expect new files under `backend/` and possible **Dockerfile** / **README** touches only as required by migrations.

### Latest technical notes

- **SQLAlchemy 2.0** + **Alembic**: use the current Alembic documentation for “async” vs “sync migration” URL — pick one documented approach and stay consistent through Epic 2/3.
- **pgvector:** No vector columns required for **2.1**; later stories add `transcript_segments` / embeddings.

### Project context reference

- No `project-context.md` found in repo; rely on this file + `architecture.md` + `epics.md`.

## References

- `_bmad-output/planning-artifacts/epics.md` — Epic 2, Story 2.1 (acceptance criteria)
- `_bmad-output/planning-artifacts/architecture.md` — Data Architecture, API & Format Patterns, Naming Patterns
- `_bmad-output/planning-artifacts/prd.md` — MVP API expectations (supplementary)
- `backend/app/main.py`, `backend/app/db.py`, `backend/app/config.py` — existing patterns
- `backend/Dockerfile` — must include migration assets if migrations ship in the image

## Dev Agent Record

### Agent Model Used

Cursor agent (implementation session)

### Implementation Plan

- Add Alembic baseline + `videos` / `ingestion_jobs` (UUID PKs) with `ingestion_jobs.status = pending` for new registrations.
- Expose `POST /videos` and `GET /videos` (direct JSON payloads; errors as `{ "error": { "code", "message" } }`).
- Validate path/extension in domain layer (`AppError` with stable codes); map Pydantic validation to **400** + `VALIDATION_ERROR`.
- Docker: `alembic upgrade head` then `exec "$@"` with default `CMD` uvicorn.
- Tests: unit coverage for registration validation; async `httpx` API tests gated by `TEST_DATABASE_URL`.

### Debug Log References

### Completion Notes List

- Implemented `POST /videos` / `GET /videos`, SQLAlchemy models, Alembic revision `20260321_0001`, sync migration URL via `postgresql+psycopg://` (see `sync_database_url_for_alembic`).
- Ingestion job status canonical value: **`pending`** (documented in `backend/README.md`).
- `pytest`: 8 passed, 3 skipped (integration tests without `TEST_DATABASE_URL`).

### File List

- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/20260321_0001_initial_videos_and_ingestion_jobs.py`
- `backend/app/config.py`
- `backend/app/deps.py`
- `backend/app/errors.py`
- `backend/app/main.py`
- `backend/app/models/__init__.py`
- `backend/app/models/base.py`
- `backend/app/models/video.py`
- `backend/app/routers/__init__.py`
- `backend/app/routers/videos.py`
- `backend/app/schemas/video.py`
- `backend/app/services/video_service.py`
- `backend/docker-entrypoint.sh`
- `backend/Dockerfile`
- `backend/pytest.ini`
- `backend/README.md`
- `backend/requirements.txt`
- `backend/requirements-dev.txt`
- `backend/tests/conftest.py`
- `backend/tests/test_video_validation.py`
- `backend/tests/test_videos_api.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-21: Story 2.1 — videos + ingestion_jobs schema, Alembic, `POST/GET /videos`, structured errors, tests, Docker migration entrypoint, README.
