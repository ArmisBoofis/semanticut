# semanticut

Monorepo for semantic video search: `backend/` (FastAPI), `frontend/` (Next.js), PostgreSQL with **pgvector** via Docker Compose.

## Prerequisites

- **Docker** and **Docker Compose v2** (`docker compose`, not legacy `docker-compose`)
- Optional: **`psql`** on the host for manual checks against the published port

## Environment

1. Copy the template and adjust if needed:

   ```bash
   cp .env.example .env
   ```

2. Variables (snake_case, shared with future `api` / Alembic):

   | Variable | Purpose |
   |----------|---------|
   | `POSTGRES_USER` | Database user |
   | `POSTGRES_PASSWORD` | Database password (keep secret in real `.env`) |
   | `POSTGRES_DB` | Database name |
   | `POSTGRES_PORT` | Host port mapped to PostgreSQL (default `5432`) |
   | `API_PORT` | Host port for the FastAPI **`api`** service (default `8000`) |
   | `POSTGRES_HOST` | DB hostname for the API (Compose sets **`db`**; local dev often **`localhost`**) |
   | `DB_CONNECT_TIMEOUT` / `DB_COMMAND_TIMEOUT` | Optional asyncpg timeouts (seconds) for connect / commands |

The **`api`** service receives the same **`POSTGRES_USER`**, **`POSTGRES_PASSWORD`**, and **`POSTGRES_DB`** as **`db`**, plus **`POSTGRES_HOST`** (e.g. **`db`** on the Compose network). The app builds an async **`DATABASE_URL`** with **URL-encoded** credentials (so special characters in passwords are safe). You can still set **`DATABASE_URL`** explicitly to override.

The committed **`.env.example`** lists defaults without secrets; **`.env`** is gitignored.

**Host shells:** commands that use `$POSTGRES_*` on your machine must load `.env` first (see [pgvector](#pgvector) — host `psql` example).

## Docker: start the stack

From the **repository root**:

```bash
docker compose up
```

Or detached:

```bash
docker compose up -d
```

This builds/starts services defined in `docker-compose.yml`. The stack includes:

- **`db`**: PostgreSQL using the **`pgvector/pgvector`** image (pg16) with a named volume for data and init scripts under `docker/postgres/init/`.
- **`api`**: FastAPI (Story 1.2), exposed on **`API_PORT`** (default **8000**).

The **`web`** (Next.js) service is added in **Story 1.3**.

### Verify `db` and `api`

```bash
docker compose ps
```

The **`db`** service should show as **healthy** once `pg_isready` succeeds. The **`api`** service should be **running** after the image builds.

**Health check (API + database):**

```bash
curl -sS "http://localhost:${API_PORT:-8000}/health"
```

Expect **HTTP 200** and JSON like `{"status":"ok","database":"ok"}`. If PostgreSQL is down or unreachable, **`GET /health`** returns **503** with `database: "error"` (not a false “all OK”).

## pgvector

PostgreSQL is expected to run **with the pgvector extension** available. This is required for **semantic search** in later epics.

- On a **fresh** data volume, `docker/postgres/init/01-pgvector.sql` runs `CREATE EXTENSION IF NOT EXISTS vector;` automatically.
- To confirm from inside the **`db`** container (uses DB env vars **inside** the container — no host `.env` needed):

  ```bash
  docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"'
  ```

  (Should succeed; extension may already exist.)

- List extensions:

  ```bash
  docker compose exec db sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -c '\\dx'"
  ```

  You should see **`vector`**.

Host-side (if `psql` is installed and the port is published), load `.env` then connect:

```bash
set -a && source .env && set +a
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT:-5432}/${POSTGRES_DB}" -c '\dx'
```

## Tests

```bash
npm test
```

Validates `docker compose` configuration and expected files (uses `.env.example` so a local `.env` is not required).
