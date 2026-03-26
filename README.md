# semanticut

Semantic video search monorepo: `backend/` (FastAPI), `frontend/` (Next.js), PostgreSQL + **pgvector**, orchestrated with Docker Compose.

## Phase 1 — Onboarding (run the app)

### Prerequisites

- **Docker** + **Docker Compose v2** (use `docker compose`, not `docker-compose`)
- Optional (host dev): **Node.js 22+** / npm, and `psql`

### 1) Create your `.env`

From the repo root:

```bash
cp .env.example .env
```

Then edit `.env` as needed. At minimum, the defaults work for local DB + API + web.

If you want ingestion (transcription + embeddings) to complete, you must set:

- `MISTRAL_API_KEY=...`

Video storage is backed by a host folder mounted into containers:

- host path: `VIDEO_STORAGE_HOST_PATH` (default `./data/videos`)
- container path: `VIDEO_STORAGE_ROOT` (default `/data/videos`)

### 2) Start the containers

Build and start everything (including the ingestion `worker`):

```bash
docker compose up --build
```

Or detached:

```bash
docker compose up --build -d
```

### 3) Open the app + verify health

- **Web UI**: `http://localhost:${WEB_PORT:-3000}`
- **Admin UI** (upload + status): `http://localhost:${WEB_PORT:-3000}/admin`
- **API health**: `http://localhost:${API_PORT:-8000}/health`

Quick health check:

```bash
curl -sS "http://localhost:${API_PORT:-8000}/health"
```

### Useful Docker commands

```bash
docker compose ps
docker compose logs -f api worker
docker compose down
```

If you want to reset the database volume (destructive):

```bash
docker compose down -v
```

### Optional: run the frontend on the host (hot reload)

Keep `db`, `api`, `worker` running in Docker, and run Next.js locally:

```bash
cd frontend
npm ci
export API_INTERNAL_URL=http://127.0.0.1:8000
npm run dev
```

## Uploading a video

There are two supported ways: **Admin UI upload (recommended)** or **API calls**.

### Option A — Upload from the Admin UI

1. Open `http://localhost:${WEB_PORT:-3000}/admin`
2. In “Ajouter une vidéo”, set:
   - **Label** (display name)
   - **File** (`.mp4`, `.webm`, `.mov`, `.mkv`, …)
3. Submit. The file is saved under the shared volume, and a DB row + ingestion job are created.

Notes:

- Uploaded files are stored under `VIDEO_STORAGE_ROOT/uploads/…` inside the containers (host: `VIDEO_STORAGE_HOST_PATH/uploads/…`).
- If `MISTRAL_API_KEY` is missing, ingestion will fail with `MISTRAL_NOT_CONFIGURED` (the upload/registration still works).

### Option B — Upload via the API (`multipart/form-data`)

```bash
curl -sS -X POST "http://127.0.0.1:${API_PORT:-8000}/videos/upload" \
  -F "label=Ma vidéo" \
  -F "file=@./path/to/video.mp4"
```

### Option C — Register an existing file path (`application/json`)

This does not upload bytes: it registers a path the `worker` must be able to read.

- **Relative paths** are resolved under `VIDEO_STORAGE_ROOT` (so `uploads/foo.mp4` means `/data/videos/uploads/foo.mp4` in Compose).
- **Absolute paths** are accepted (with validation), but must exist in the container filesystem.

```bash
curl -sS -X POST "http://127.0.0.1:${API_PORT:-8000}/videos" \
  -H "Content-Type: application/json" \
  -d '{"label":"Demo","storage_path":"uploads/demo.mp4"}'
```

## Phase 2 — Tech stack and pipelines

### Tech stack (high level)

- **Frontend**: Next.js (App Router) + TypeScript + TailwindCSS
  - Uses server-side proxy routes under `frontend/app/api/**` to call FastAPI via `API_INTERNAL_URL` (avoids browser CORS).
- **Backend API**: FastAPI + Pydantic + SQLAlchemy (async) + Alembic migrations
- **Database**: PostgreSQL 16 with **pgvector** (embedding vectors stored as `vector(1024)`)
- **Worker**: a dedicated Python process (`python -m app.worker`) for ingestion steps (keeps HTTP requests fast)
- **Media tools**: `ffmpeg` / `ffprobe` (installed in the backend image)
- **AI provider**: Mistral (transcription + embeddings + “anchor” extraction)

### Ingestion pipeline (what happens after registration)

When you register a video (`POST /videos` or `POST /videos/upload`), the API writes:

- a `videos` row (label + storage path)
- an `ingestion_jobs` row (`pending`, then updated by the worker)

The **worker** continuously claims `pending` jobs and runs phases:

- **Audio extraction**: `ffmpeg` → mono 16kHz WAV
- **Transcription**: Mistral Voxtral (`MISTRAL_TRANSCRIPTION_MODEL`, default `voxtral-mini-latest`)
- **Chunking**:
  - **micro segments**: timestamped spans for precise seeks
  - **macro segments**: groups of micros to form context-rich blocks (targeted by words/chars via `TRANSCRIPT_MACRO_TARGET_*`)
- **Embeddings**:
  - micro embeddings (per micro segment)
  - macro embeddings (per macro block)
- **Indexing**: writes segments + vectors into PostgreSQL (pgvector)

### Search pipeline (what happens on `POST /videos/{id}/search`)

The search is designed to return a **timestamped micro segment** plus a **macro context block** for display/highlighting:

1. **Embed the query** (Mistral embeddings)
2. **Phase 1 — macro retrieval (hybrid)**
   - Dense retrieval: cosine distance on macro embeddings (pgvector)
   - Lexical retrieval: Postgres full-text ranking on macro text (BM25-like)
   - **Fuse** the rankings with **Reciprocal Rank Fusion (RRF)** (`SEARCH_RRF_K`, default `60`)
   - Keep an adaptive shortlist (distance threshold + gap from best), then take top-K macros for context (`SEARCH_MACRO_TOP_K`)
3. **Phase 2 — anchor extraction (LLM)**
   - Send a structured JSON payload (macros + their micros) to a Mistral chat model (`MISTRAL_ANCHOR_MODEL`)
   - The model returns an **anchor** and an inferred intent (**quote** vs **scene**)
4. **Resolve anchor → micro segment**
   - Lexical overlap resolution over candidate micros (quote intent is stricter)
   - Safety: keep result near the “peak” similarity region (bounded time window)
5. **Response contract**
   - `start_ts`, `end_ts`, `text` (micro)
   - `macro_context_text` (macro)
   - `match_start_offset`, `match_end_offset` (highlight inside the macro string)
   - `confidence` and `match_quality` tier

## pgvector notes (optional checks)

- On a **fresh** DB volume, `docker/postgres/init/01-pgvector.sql` runs `CREATE EXTENSION IF NOT EXISTS vector;`.
- Check extensions inside the container:

```bash
docker compose exec db sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -c '\\dx'"
```

## Tests

- Root (static Compose contract checks):

```bash
npm test
```

- Frontend (Vitest):

```bash
cd frontend && npm ci && npm test
```
