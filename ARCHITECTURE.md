# Architecture

## Services

| Service | Stack | Port | Notes |
|---|---|---|---|
| `frontend` | Next.js 15 App Router, TypeScript, Tailwind v4 | 3000 | `output: "standalone"`; proxies `/api/*` to the backend via `next.config.ts` rewrites |
| `backend` | FastAPI, SQLAlchemy, Pydantic v2 | 8000 | REST + one WebSocket; entrypoint runs `alembic upgrade head` |
| `db` | PostgreSQL 16 | 5432 | volume-backed; `pg_isready` healthcheck gates the backend |

## Backend layout (`backend/app/`)

```
main.py            app assembly, lifespan diagnostics, exception handlers, /api/health
config.py          pydantic-settings; every tunable + SECRET_FROM_ENV
database.py        engine + SessionLocal (pool_pre_ping on Postgres)
logging_config.py  one formatter; request-id via contextvar
middleware.py      RequestContext (id + access log) + RateLimit (in-memory sliding window)
deps.py            get_current_user (access-token only)
security.py        bcrypt; access JWT (jti, type=access); opaque rotating refresh tokens
models.py          User, Prediction, RefreshToken
schemas.py         all request/response models
jobs.py            in-memory batch-job store + async pub/sub for the WS
routers/
  auth.py          register / login / refresh (rotating) / logout / me
  predict.py       /text /url /image /audio /batch (sync)
  batch_jobs.py    POST /batch/jobs, GET status, WS /batch/jobs/{id}/ws
  history.py       list / delete
  analytics.py     summary (by_day bucketed in Python for SQLite+PG portability)
  assist.py        summarize / chat (RAG-grounded)
  rag.py           search / status
ml/
  preprocess.py    text cleaning
  inference.py     ModelBundle, predict(), predict_smart(), confidence_band()
  llm_verdict.py   Groq call, RAG retrieval, JSON parse, citations
  media.py         analyze_image (vision -> OCR fallback), analyze_audio (whisper)
  source_credibility.py   static domain -> tier advisory lookup
rag/
  retriever.py     TF-IDF index over corpus/*.md + data/fact_checks.csv; joblib cache
  corpus/*.md      curated media-literacy notes
```

## Request → verdict flow (text)

1. `POST /api/predict/text` → `predict_smart(text)`.
2. `predict()` runs the local pipeline: `clean_text` → TF-IDF → classifier →
   label, probabilities, `confidence_band`, and `signal_words` (linear-model
   coefficients × the row's TF-IDF weights).
3. `get_llm_verdict()`:
   - `rag.retrieve(text[:2000])` → top-k passages (TF-IDF cosine).
   - Groq chat call with the system prompt + references + text → strict JSON
     `{label, confidence, reasoning, citation_ids}`.
   - Parse; map `citation_ids` back to passage objects.
4. If the LLM call fails for any reason, the local result is returned with
   `verdict_source: "classic_fallback"`. The LLM never becomes a hard
   dependency.
5. The row is logged to `predictions`; the response includes everything
   above plus (for URLs) `source_credibility`.

Image and audio add a pre-step (`ml/media.py`) that produces text +
optional analyst notes, then join this same flow with `modality` set.

## Batch flow

`POST /api/batch/jobs` creates an in-memory `BatchJob`, spawns an
`asyncio` task (`jobs.run_batch_job`), and returns `{job_id}` immediately.
The task parses the file, then classifies rows one at a time with
`asyncio.to_thread`, calling `job.publish()` after each. Subscribers
(`asyncio.Queue` per WS connection) receive every snapshot. The WS handler
authenticates via a `?token=` query param (browsers can't set headers on a
WebSocket) and closes with `4404` on auth failure. `GET /api/batch/jobs/{id}`
is the polling fallback.

## Auth

- **Access token**: JWT, `type=access`, `jti`, 30-minute expiry. Sent as
  `Authorization: Bearer`. `decode_access_token` rejects any token whose
  `type` isn't `access`, so a refresh token can't be used as a bearer.
- **Refresh token**: opaque `secrets.token_urlsafe(48)`, stored only as a
  SHA-256 hash in `refresh_tokens`. `POST /auth/refresh` consumes (revokes)
  the presented row and issues a fresh pair — **rotation**. Presenting an
  already-revoked token is treated as theft: every live token for that user
  is revoked. `login` prunes expired rows and caps live tokens per user.

See [`docs/auth.md`](docs/auth.md).

## Data / DB

SQLAlchemy models in `models.py`; migrations in `backend/alembic/`. Local
dev can use `DB_CREATE_ALL=true` (SQLite or Postgres). Containers and CI use
Alembic. `analytics.summary` deliberately buckets the 14-day trend in Python
rather than `func.date()` / `CAST(... AS date)`, which behave differently
across SQLite and PostgreSQL.

## Frontend

All pages are client components — the app is auth-gated and dynamic. Auth
state lives in `localStorage` via `lib/auth.tsx`; `lib/api.ts` is an axios
instance whose response interceptor transparently refreshes a 401 once
before redirecting to `/login`. `(dashboard)/layout.tsx` is the protected
shell (sidebar + mobile menu). Charts use Recharts.
