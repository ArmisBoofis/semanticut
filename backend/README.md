# backend

FastAPI service for **semanticut**.

## Stack

- **App:** `app/main.py` — FastAPI, `GET /health`, `POST /videos`, `GET /videos`.
- **Config:** set **`DATABASE_URL`**, or **`POSTGRES_USER`**, **`POSTGRES_PASSWORD`**, **`POSTGRES_DB`**, and **`POSTGRES_HOST`** / **`POSTGRES_PORT`** (the app builds a `postgresql+asyncpg://` URL with safe password encoding). Optional **`DB_CONNECT_TIMEOUT`** / **`DB_COMMAND_TIMEOUT`** (seconds).
- **Migrations:** **Alembic** (sync driver **`postgresql+psycopg://`** in `alembic/env.py`). From this directory with env loaded (same DB as the API):

  ```bash
  alembic upgrade head
  ```

  The **`api`** Docker image runs `alembic upgrade head` on startup, then **`uvicorn`** (see `docker-entrypoint.sh` + `Dockerfile` `CMD`).

## IDs and ingestion status

- **Primary keys** are **UUID** (v4) on `videos` and `ingestion_jobs`.
- New registrations create an **`ingestion_jobs`** row with status **`pending`** (canonical value for Epic 2 until background work advances jobs in later stories).
- Responses expose **`ingestion_status`**, copied from the related job’s **`status`**. The reserved value **`unknown`** is returned only when a video has **no** related ingestion job row (unexpected — indicates a data integrity problem).

## API examples

Replace host/port as needed (`8000` by default).

```bash
curl -sS -X POST "http://127.0.0.1:8000/videos" \
  -H "Content-Type: application/json" \
  -d '{"label":"Interview A","storage_path":"/data/videos/demo.mp4"}'
```

```bash
curl -sS "http://127.0.0.1:8000/videos"
```

**Errors** use shape `{ "error": { "code", "message" } }` with **4xx** as appropriate (e.g. **400** for validation / domain issues). Stable **`code`** values include **`VALIDATION_ERROR`**, **`UNSUPPORTED_MEDIA`**, **`INVALID_STORAGE_PATH`**.

## Run locally (venv)

```bash
pip install -r requirements.txt
# set DATABASE_URL or POSTGRES_* as above
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests set **`SKIP_DB_STARTUP=1`** (skip real DB on startup / skip engine dispose in shutdown) where appropriate — **do not set `SKIP_DB_STARTUP` in production**.

**Video API integration tests** (`tests/test_videos_api.py`) require PostgreSQL and **`TEST_DATABASE_URL`** (async URL, e.g. `postgresql+asyncpg://user:pass@localhost:5432/dbname`). If unset, those tests are **skipped**; validation unit tests still run.

For each run, the suite **resets the `public` schema** on that database (destructive) and applies the same **`alembic upgrade head`** migrations as production, so the test schema matches the Alembic revision — use a **throwaway** database or role, not production data.

## Notes

- **Python:** Docker image uses **3.12**; local venv should match for consistent wheels (e.g. **3.12** recommended).
- Product/browser UI may use **French** in frontend stories; **API** messages stay concise **English** with machine-oriented **`code`** fields.
