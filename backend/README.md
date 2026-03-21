# backend

FastAPI service for **semanticut** (Story 1.2).

- **App:** `app/main.py` — FastAPI + `GET /health` (checks PostgreSQL with `SELECT 1`).
- **Config:** set **`DATABASE_URL`**, or **`POSTGRES_USER`**, **`POSTGRES_PASSWORD`**, **`POSTGRES_DB`**, and **`POSTGRES_HOST`** / **`POSTGRES_PORT`** (the app builds a `postgresql+asyncpg://` URL with safe password encoding). Optional **`DB_CONNECT_TIMEOUT`** / **`DB_COMMAND_TIMEOUT`** (seconds) bound connect and queries.
- **Run locally (with venv):** `pip install -r requirements.txt`, set env as above, then `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` from this directory.
- **Tests:** `pip install -r requirements-dev.txt` then `pytest`. Tests set **`SKIP_DB_STARTUP=1`** (skip real DB on startup / skip engine dispose in shutdown) and mock DB checks — **do not set `SKIP_DB_STARTUP` in production**.

Production-like runs use the root **`docker compose`** **`api`** service (see root `README.md`).
