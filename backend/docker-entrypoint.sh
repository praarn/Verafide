#!/usr/bin/env bash
set -e

# Wait for Postgres, then bring the schema up to date before serving.
echo "[entrypoint] running migrations..."
for attempt in $(seq 1 30); do
  if alembic upgrade head; then
    break
  fi
  echo "[entrypoint] alembic failed (attempt $attempt) — DB not ready? retrying in 2s"
  sleep 2
done

echo "[entrypoint] starting uvicorn"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
