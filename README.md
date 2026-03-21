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

This builds/starts services defined in `docker-compose.yml`. For Story 1.1, the only application service is **`db`**: PostgreSQL using the **`pgvector/pgvector`** image (pg16) with a named volume for data and init scripts under `docker/postgres/init/`.

### Verify `db` is healthy

```bash
docker compose ps
```

The **`db`** service should show as **healthy** once `pg_isready` succeeds.

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
