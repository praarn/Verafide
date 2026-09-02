# Deployment

## Docker Compose (reference deployment)

```bash
SECRET_KEY=$(openssl rand -hex 32) \
GROQ_API_KEY=your_key \
docker compose up --build
```

Three services:

| Service | Image | Healthcheck | Depends on |
|---|---|---|---|
| `db` | `postgres:16-alpine` | `pg_isready` | — |
| `backend` | `./backend` (python:3.12-slim) | `curl /api/health` | `db` healthy |
| `frontend` | `./frontend` (node:20-slim, Next standalone) | `curl /` | `backend` healthy |

- The backend image trains the ML models and builds the RAG index at
  **build time**, runs as a non-root user, and its entrypoint runs
  `alembic upgrade head` (with retry) before `uvicorn`.
- The frontend image is a multi-stage Next `output: "standalone"` build,
  also non-root.
- `DB_CREATE_ALL=false` in the container — Alembic owns the schema.

### Environment

| Var | Where | Notes |
|---|---|---|
| `SECRET_KEY` | backend | **required in prod** — random fallback logs everyone out on restart |
| `GROQ_API_KEY` | backend | optional; without it, local model + OCR only |
| `GROQ_MODEL` | backend | set to a current model if the default 404s |
| `DATABASE_URL` | backend | compose sets `postgresql+psycopg://verafide:verafide@db:5432/verafide` |
| `CORS_ORIGINS` | backend | comma-separated; no `*` in prod (startup errors) |
| `BACKEND_ORIGIN` | frontend | server-side proxy target for `/api/*` (default `http://backend:8000`) |
| `NEXT_PUBLIC_WS_ORIGIN` | frontend **build arg** | only needed if the browser can't reach `ws://<host>:8000`; otherwise computed client-side |

## CI (`.github/workflows/ci.yml`)

- **backend** job: ruff → apply+rollback Alembic migrations against a real
  `postgres:16` service → train models + build RAG index → `pytest`
  (SQLite, no network).
- **frontend** job: `npm ci` → `eslint` → `tsc --noEmit` → `next build`.

Runs on push to `main` and every PR. No Kubernetes, no Jenkins.

## Scaling beyond one instance

- Put a gateway / shared-store rate limiter in front and set
  `RATE_LIMIT_ENABLED=false`.
- Move the batch job store (`app/jobs.py`) to Redis / a task queue.
- Run `alembic upgrade head` as a one-off release step rather than per
  replica.
