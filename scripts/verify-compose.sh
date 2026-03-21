#!/usr/bin/env bash
# Validates docker-compose + pgvector init contract (Story 1.1) and api service (Story 1.2).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f docker-compose.yml ]] || [[ ! -f .env.example ]]; then
  echo "missing docker-compose.yml or .env.example" >&2
  exit 1
fi

grep -qE 'image:[[:space:]]*pgvector/pgvector:pg[0-9]+' docker-compose.yml || {
  echo "expected pgvector/pgvector:pg<major> image (e.g. pg16) in docker-compose.yml" >&2
  exit 1
}
grep -q 'pg_isready' docker-compose.yml || {
  echo "expected db healthcheck (pg_isready)" >&2
  exit 1
}
grep -q 'docker-entrypoint-initdb.d' docker-compose.yml || {
  echo "expected init scripts mount" >&2
  exit 1
}
grep -q '^CREATE EXTENSION IF NOT EXISTS vector' docker/postgres/init/01-pgvector.sql || {
  echo "expected vector extension init SQL" >&2
  exit 1
}
grep -qE '^[[:space:]]*api:' docker-compose.yml || {
  echo "expected api service in docker-compose.yml" >&2
  exit 1
}
grep -q 'condition: service_healthy' docker-compose.yml || {
  echo "expected api depends_on db with condition: service_healthy" >&2
  exit 1
}
grep -q 'POSTGRES_HOST:' docker-compose.yml || {
  echo "expected POSTGRES_HOST for api service in docker-compose.yml" >&2
  exit 1
}
echo "static compose contract checks: OK"

if command -v docker >/dev/null 2>&1; then
  docker compose --env-file .env.example config >/dev/null
  echo "docker compose config: OK"
  echo "Manual runtime check (optional): cp .env.example .env && docker compose up --build -d && curl -sS http://localhost:\${API_PORT:-8000}/health"
else
  echo "warning: docker not in PATH; skipped docker compose config (install Docker for full check)" >&2
fi
