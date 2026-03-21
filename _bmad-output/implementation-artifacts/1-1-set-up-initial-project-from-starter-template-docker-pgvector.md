# Story 1.1: Set up initial project from starter template (Docker + pgvector)

Status: review

<!-- Ultimate context engine analysis completed — comprehensive developer guide created. -->

## Story

As a reviewer,
I want to set up the initial project from the starter-aligned layout and ensure Docker brings up PostgreSQL with pgvector and a simple health check,
so that the rest of the implementation can rely on a consistent, reproducible database environment.

## Acceptance Criteria

1. **Compose up:** Given a fresh clone and documented prerequisites, when the reviewer runs `docker compose up` from the repo root (per README), Docker builds/starts successfully and a **`db`** service is running PostgreSQL, reachable from the Docker network.
2. **pgvector:** Given the `db` container is running, when connecting from inside `db` or another service on the same Compose network (e.g. `psql`), then `CREATE EXTENSION IF NOT EXISTS vector` succeeds (extension installed and usable).
3. **Documentation:** Given the repo README (or equivalent “Environment” / “Docker” section), when the reviewer reads it, they see how to start the stack and that **`db`** is expected to run with **pgvector**.

## Tasks / Subtasks

- [x] **Repository layout** (AC: 1, 3)
  - [x] Align root layout with architecture: monorepo-style `backend/` (FastAPI, future) and `frontend/` (Next.js, future), plus root `docker-compose.yml` (or `compose.yaml`) — see [Source: `_bmad-output/planning-artifacts/architecture.md` — Starter Template Evaluation, Infrastructure & Deployment].
  - [x] If the chosen starter scaffolds API/web in one shot, it is acceptable; **this story’s verification** still focuses on **`db` + pgvector** (API/web hardening is Stories 1.2 / 1.3).
- [x] **Database image & service** (AC: 1, 2)
  - [x] Use a maintained PostgreSQL image **with pgvector** preinstalled (e.g. **`pgvector/pgvector`** tags such as `pg16` / `pg17` — pin a specific image digest or minor version tag; avoid abandoned `ankane/pgvector` for new work). [Latest tech: see “Latest technical specifics” below.]
  - [x] Name the service **`db`** to match architecture and downstream stories.
  - [x] Expose PostgreSQL on a documented host port (e.g. `5432`) only if needed for host-side tools; default reviewer path can stay in-network.
  - [x] Persist data with a named volume for local dev.
- [x] **Enable pgvector on init** (AC: 2)
  - [x] Provide `docker-entrypoint-initdb.d` SQL (or equivalent) so a fresh volume runs `CREATE EXTENSION IF NOT EXISTS vector;` automatically — satisfies AC without requiring Alembic yet.
- [x] **Health check** (AC: 1, epic “simple health check”)
  - [x] Add Docker **`healthcheck`** on `db` using `pg_isready` (or equivalent) so `docker compose ps` shows healthy database when ready.
- [x] **Environment contract** (AC: 1, 3)
  - [x] Document `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (or chosen names) and how other services will reuse them later — snake_case env names consistent with architecture.
  - [x] Add `.env.example` at repo root (or documented placeholder) listing DB variables **without secrets**; real `.env` gitignored.
- [x] **README** (AC: 3)
  - [x] Prerequisites: Docker + Docker Compose v2, optional `psql` for manual checks.
  - [x] Single primary command: `docker compose up` (or `docker compose up -d`) from repo root.
  - [x] Short subsection: verifying pgvector (`CREATE EXTENSION` / `\dx` in `psql`).
  - [x] Note explicitly that **pgvector** is required for semantic search in later epics.

## Dev Notes

### Scope guardrails (this story vs 1.2 / 1.3)

- **In scope:** `docker compose` brings up **`db`** with **pgvector** verified, documented env + README, DB healthcheck, init extension.
- **Out of scope for 1.1:** FastAPI health endpoint, Next.js container, Alembic migrations for app tables (those land with schema work in later stories). Do not mark Stories 1.2/1.3 done here.

### Architecture compliance

- **Stack:** PostgreSQL + **pgvector** as the only DB; local deployment via **Docker Compose**; three target services **`api`**, **`db`**, **`web`** in the full system — only **`db`** must be implemented and healthy in this story. [Source: `_bmad-output/planning-artifacts/architecture.md` — Core Architectural Decisions, Infrastructure & Deployment]
- **Naming:** DB tables/columns later use **snake_case**; REST **snake_case**; this story sets **env var** naming convention early (e.g. `POSTGRES_*` for engine defaults).
- **Config:** `.env` / `.env.local` pattern for future API and web; document variable names once.

### File structure requirements

Suggested layout (adjust to starter if needed, but keep names discoverable):

- `docker-compose.yml` — `db` service, volume, healthcheck, init scripts mount.
- `db/init/` or `docker/postgres/init/` — `*.sql` for `CREATE EXTENSION IF NOT EXISTS vector`.
- `README.md` — Docker / Environment section (required AC).
- `.env.example` — non-secret defaults for DB.
- `backend/`, `frontend/` — create as stubs or via starter when you run initialization; do not leave repo with only `docs/` and planning artifacts if the epic expects a scaffolded project.

### Library / runtime requirements

- **Docker:** Docker Compose v2 (`docker compose` CLI).
- **PostgreSQL:** Version aligned with `pgvector/pgvector` tag (e.g. 16 or 17 — pick one and pin).
- **Python/Node:** Not required to execute tests in CI for **this** story unless you add a minimal smoke script; optional `Makefile` target `db-up` / `db-psql` is helpful.

### Testing requirements

- **Manual verification (required):**
  - `docker compose up -d` → `db` healthy.
  - `docker compose exec db psql -U ... -d ... -c "CREATE EXTENSION IF NOT EXISTS vector;"` → success.
  - `\dx` shows `vector`.
- **Automated (optional):** CI job that starts compose and runs the same SQL (only if CI exists — currently greenfield).

### Previous story intelligence

- None (first implementation story).

### Git / codebase intelligence

- Recent commits are documentation-only; **no application code** yet (`package.json` placeholder at root). Expect **greenfield** scaffold.
- [Source: `git log` — planning/docs commits only.]

### Latest technical specifics

- Prefer **`pgvector/pgvector`** images on Docker Hub over legacy **`ankane/pgvector`** for current PostgreSQL + pgvector combinations; pin by tag or digest for reproducibility.
- When adding `api` in Story 1.2, use SQLAlchemy connection URL from the same `POSTGRES_*` values documented here.

### UX / product UI

- No user-facing UI in this story. Product UI is **French (`fr-FR`)** in later stories; irrelevant for DB-only setup. [Source: `_bmad-output/planning-artifacts/architecture.md` — Localization & UI language]

### References

- Epic & AC: `_bmad-output/planning-artifacts/epics.md` — Epic 1, Story 1.1.
- PRD constraints: `_bmad-output/planning-artifacts/prd.md` — Technical Success, MVP scope (Docker Compose, stable schema path).
- Architecture: `_bmad-output/planning-artifacts/architecture.md` — Starter evaluation, Infrastructure & Deployment, Implementation Sequence (step 1).
- UX (downstream): `_bmad-output/planning-artifacts/ux-design-specification.md` — not blocking for 1.1.

## Change Log

- **2026-03-21:** Added `docker-compose.yml` (`db`, `pgvector/pgvector:pg16`, volume, healthcheck, init mount), `docker/postgres/init/01-pgvector.sql`, `.env.example`, root `README.md`, `backend/` + `frontend/` stubs, `scripts/verify-compose.sh`, `npm test`; `.gitignore` extended for `.env` / `.env.local`.
- **2026-03-21 (code review):** README — `docker compose exec` examples run `psql` in-container so `$POSTGRES_*` resolves inside `db`; host `psql` documents `set -a && source .env`. `scripts/verify-compose.sh` — image check uses `pgvector/pgvector:pg[0-9]+` (portable `grep -E`). `.gitignore` — POSIX final newline; `.vscode` ignored.

## Dev Agent Record

### Agent Model Used

Composer (Cursor agent)

### Debug Log References

- Local `docker compose up` not executed here: Docker daemon unavailable in agent environment (`Cannot connect to the Docker daemon`). **Armand:** run README manual verification on your machine.

### Completion Notes List

- **AC1–3:** Implemented via `docker-compose.yml` + docs + init SQL + `.env.example`; automated check `npm test` / `scripts/verify-compose.sh` (static + `docker compose config` when Docker CLI present).
- **Image:** `pgvector/pgvector:pg16` (pinned tag per story).
- **Compose env:** `POSTGRES_*` + `POSTGRES_PORT`; interpolation from `.env` (copy from `.env.example`).
- **Manual follow-up:** `cp .env.example .env` → `docker compose up -d` → `docker compose ps` (healthy) → README `docker compose exec db sh -c ...` for `\dx` / extension checks.
- **Code review follow-up:** README fixed host-vs-container env expansion; verify script no longer hard-codes `pg16`; `.gitignore` newline + `.vscode`.

### File List

- `docker-compose.yml`
- `docker/postgres/init/01-pgvector.sql`
- `.env.example`
- `.gitignore`
- `README.md`
- `backend/README.md`
- `frontend/README.md`
- `package.json`
- `scripts/verify-compose.sh`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/1-1-set-up-initial-project-from-starter-template-docker-pgvector.md`
