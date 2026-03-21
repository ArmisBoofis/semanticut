# Story 1.2: Dockerized FastAPI backend wired to PostgreSQL

Status: review

<!-- Ultimate context engine analysis completed — comprehensive developer guide created. -->

## Story

As a reviewer,
I want a Dockerized FastAPI service connected to the PostgreSQL database,
so that the API can start up and talk to the database in a reproducible way.

## Acceptance Criteria

1. **API service up:** Given I run `docker compose up` from the repo root, when services are healthy, then an `api` service is running **FastAPI**, exposed on a **documented host port** (e.g. **8000**), reachable from the host (e.g. browser or `curl`).
2. **DB connectivity:** Given the `api` service has started, when it initializes its database access using **environment variables from Docker Compose** (aligned with existing `POSTGRES_*` / connection URL contract from Story 1.1), then it **successfully connects** to the `db` service on the Compose network and runs **at least one trivial query** (e.g. `SELECT 1`). If the database is unreachable, the process **fails fast** with a **clear log message** (not a silent hang).
3. **Health check:** Given the stack is up, when I call a **simple health endpoint** (e.g. `GET /health` — preferred for clarity), then I receive **HTTP 200** with a JSON body that indicates the API is alive **and** that the database check succeeded (so a broken DB is not reported as “healthy”).

## Tasks / Subtasks

- [x] **Backend package** (AC: 1, 2)
  - [x] Add a minimal FastAPI app under `backend/` (e.g. `app/main.py` or project layout you choose, but keep it conventional and documented).
  - [x] Use **Pydantic v2** settings or equivalent for configuration; read DB URL from env (e.g. `DATABASE_URL` built from `POSTGRES_*` in Compose, or explicit `DATABASE_URL` in `.env.example`).
  - [x] Use **SQLAlchemy 2.x** with **async** engine/session **or** a minimal async driver path; execute `SELECT 1` (or `SELECT 1 AS one`) against PostgreSQL on startup or on first request — must satisfy AC2.
- [x] **Dockerfile + Compose** (AC: 1, 2)
  - [x] Add `backend/Dockerfile` (multi-stage acceptable) running **uvicorn** with reload disabled in container unless you document dev-only behavior.
  - [x] Extend root `docker-compose.yml` with an **`api`** service: `build` context `backend/`, **depends_on** `db` with **`condition: service_healthy`**, publish **8000** (or document another port consistently in README and env).
  - [x] Pass the same DB identity as Story 1.1: reuse `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` from `.env` / `.env.example`; document how they map to the API connection string.
- [x] **Health endpoint** (AC: 3)
  - [x] Implement `GET /health` returning **200** with a **direct JSON payload** (per architecture: success = unwrapped body), e.g. `{ "status": "ok", "database": "ok" }` or include a `db_ok: true` field. If DB check fails, return **503** (or fail readiness — prefer explicit HTTP error for reviewer demos).
- [x] **Documentation** (AC: 1–3)
  - [x] Update root `README.md`: how to bring up **`db` + `api`**, expected URL for health (e.g. `http://localhost:8000/health`), and that **`web`** is Story 1.3.
- [x] **Verification script / CI hook (optional but recommended)**
  - [x] Extend `scripts/verify-compose.sh` or add a small check that `docker compose config` includes `api` and that a documented curl against `/health` is described (full runtime check only if Docker is available).

## Dev Notes

### Scope guardrails (this story vs 1.1 / 1.3)

- **In scope:** `api` Docker image, FastAPI app, PostgreSQL connectivity from `api` to `db`, documented env, `GET /health` proving DB.
- **Out of scope:** Next.js / `web` service (Story **1.3**), Alembic migrations and application tables (land when schema work starts — **not** required to satisfy “`SELECT 1`”), business endpoints (`/videos`, etc.), Mistral clients.

### Architecture compliance

- **Stack:** FastAPI + Pydantic, PostgreSQL accessed in a way that scales to **SQLAlchemy + Alembic** later. [Source: `_bmad-output/planning-artifacts/architecture.md` — Core Architectural Decisions, Data Architecture]
- **Services:** Compose must eventually expose **`api`**, **`db`**, **`web`** — this story adds **`api`** alongside existing **`db`**. [Source: `architecture.md` — Infrastructure & Deployment]
- **API responses:** Success = **direct JSON payload**; errors later use `{ "error": { "code", "message" } }`. Health success should remain a simple unwrapped body. [Source: `architecture.md` — Format Patterns]
- **Naming:** Python modules **`snake_case`**, classes **`PascalCase`**; env and future JSON **`snake_case`**. [Source: `architecture.md` — Naming Patterns]
- **Logging:** On DB connection failure, log a clear reason (host, “connection refused”, timeout) without leaking passwords.

### File structure requirements

- Keep **monorepo** layout: `backend/` owns Python project, root owns `docker-compose.yml`.
- Suggested (adjust if you standardize differently, but document in README):
  - `backend/Dockerfile`
  - `backend/pyproject.toml` or `backend/requirements.txt` with pinned major versions
  - `backend/app/` — FastAPI app package (`main.py`, `deps.py` or `db.py` for engine/session)
- Do **not** move `docker/postgres/init` or Story 1.1 DB init without reason.

### Library / runtime requirements

- **Python:** 3.11+ recommended (align with FastAPI wheels).
- **ASGI server:** `uvicorn` (with `uvicorn[standard]` if you use workers/tools).
- **DB:** `asyncpg` + SQLAlchemy 2 async, *or* `psycopg` v3 async — pick one stack and pin versions in `requirements.txt` / `pyproject.toml`.
- **FastAPI:** Current stable 0.115+ line with Pydantic v2.

### Testing requirements

- **Manual (required for reviewer):**
  - `cp .env.example .env` → `docker compose up --build` → wait for `db` healthy and `api` up.
  - `curl -sS http://localhost:8000/health` → **200**, JSON shows DB OK.
  - Stop `db` or break `DATABASE_URL` → API logs clear error; `/health` should **not** return a false “all OK” (503 or failed health).
- **Automated (optional):** `pytest` with TestClient and mocked DB only if you already have CI; otherwise defer to keep scope tight.

### Previous story intelligence (Story 1.1)

- **Compose:** `db` service is **`pgvector/pgvector:pg16`**, named volume, healthcheck via `pg_isready`, init SQL enables `vector` extension. [Source: `1-1-set-up-initial-project-from-starter-template-docker-pgvector.md`]
- **Env contract:** `.env.example` defines `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`. API should consume the **same** variables (or a single `DATABASE_URL` derived from them) so reviewers do not maintain two conflicting configs.
- **Verification:** `scripts/verify-compose.sh` and `npm test` exist for static/compose checks — extend rather than replace.
- **Dev agent note:** Story 1.1 file still shows `Status: review` in its header; **sprint-status** marks 1.1 **done** — treat 1.1 as complete for dependencies.

### Git / codebase intelligence

- Recent commits: Docker + PostgreSQL setup (`chore: Postgre configuration using docker compose and starter template`), planning docs. **Backend code is still a stub** (`backend/README.md` only). Expect greenfield FastAPI implementation in `backend/`.

### Latest technical specifics

- Prefer **official async PostgreSQL** access patterns with SQLAlchemy 2.0 (`create_async_engine`, `async_sessionmaker`) for alignment with later Alembic/async workloads.
- **Connection URL inside Docker:** host name **`db`** (Compose service name), port **5432** (container port), not `localhost` from inside `api`.
- Pin **image tags** and Python dependencies for reproducibility (matches Story 1.1 pinning philosophy).

### UX / product UI

- No browser UI in this story. Product UI language (**French**) applies from Story 1.3 onward; API messages can stay English for now. [Source: `_bmad-output/planning-artifacts/architecture.md` — Localization & UI language]

### References

- Epic & AC: `_bmad-output/planning-artifacts/epics.md` — Epic 1, Story 1.2.
- PRD: `_bmad-output/planning-artifacts/prd.md` — Technical Success (Docker Compose, stack constraints).
- Architecture: `_bmad-output/planning-artifacts/architecture.md` — stack, Compose services, naming, API response formats.

## Dev Agent Record

### Agent Model Used

Composer (Cursor agent)

### Debug Log References

### Completion Notes List

- Implemented FastAPI app with Pydantic Settings (`DATABASE_URL`), SQLAlchemy 2 async engine + `async_sessionmaker`, `SELECT 1` on startup (fail-fast with clear logs) and on `GET /health` (503 if DB down).
- Added `api` service to `docker-compose.yml` with `depends_on: db: condition: service_healthy`, port `API_PORT` (default 8000), `DATABASE_URL` built from `POSTGRES_*`.
- Pytest tests mock `check_db_connection` for 200/503; `SKIP_DB_STARTUP` + skip engine dispose in tests.
- Docker runtime verified: `docker compose --env-file .env.example up -d db api` → `curl http://localhost:8000/health` → 200 and `{"status":"ok","database":"ok"}`. If an existing Postgres volume was initialized with different credentials, recreate the volume or align `.env` with the volume (standard Postgres behavior).

### File List

- `backend/requirements.txt`
- `backend/requirements-dev.txt`
- `backend/pytest.ini`
- `backend/Dockerfile`
- `backend/.dockerignore`
- `backend/app/__init__.py`
- `backend/app/config.py`
- `backend/app/db.py`
- `backend/app/main.py`
- `backend/tests/conftest.py`
- `backend/tests/test_health.py`
- `backend/README.md`
- `docker-compose.yml`
- `.env.example`
- `.gitignore`
- `README.md`
- `scripts/verify-compose.sh`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/1-2-dockerized-fastapi-backend-wired-to-postgresql.md`

## Change Log

- **2026-03-21:** Story context created (create-story workflow); status `ready-for-dev`.
- **2026-03-21:** Implemented Story 1.2 — FastAPI `api` service, PostgreSQL connectivity, `/health`, Docker Compose, docs, verification script; status `review`.
