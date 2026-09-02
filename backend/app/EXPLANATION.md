# Backend cross-cutting infrastructure

Feature code (routers, ml, rag) is documented next to itself. This covers
the plumbing.

## `logging_config.py`

`configure_logging(level)` (called once in `main.py`) owns the root
handler + format. `request_id_ctx` is a `ContextVar` set per request by the
middleware; a logging `Filter` stamps its value onto every record as
`%(request_id)s`, so any log line is attributable to a request without
threading an id through signatures. Idempotent.

## `middleware.py`

Two `BaseHTTPMiddleware` classes, registered so `RequestContextMiddleware`
is **outermost** (times/logs even a rate-limit `429`).

- **`RequestContextMiddleware`** — request id (inbound `X-Request-ID` wins,
  else a 12-char uuid), echoed back as a header, `request.state.request_id`
  set; logs `METHOD /path -> STATUS (Nms)`.
- **`RateLimitMiddleware`** — in-memory sliding window, per-process,
  dependency-free. Key = `sha256(bearer)[:16]` or `ip:<host>`. Two buckets:
  `RATE_LIMIT_REQUESTS` normally, `RATE_LIMIT_HEAVY_REQUESTS` for
  `/api/auth/(login|register)`, `/api/predict`, `/api/assist`. Only mutating
  methods count. Exceed → `429` + `Retry-After` + frontend-compatible
  `{"detail": ...}`. Adds `X-RateLimit-*`. Stale keys evicted past 4096.
  **Not shared across replicas** — set `RATE_LIMIT_ENABLED=false` behind a
  gateway.

## `main.py`

- **`lifespan`** — logs a startup banner and flags insecure config:
  ephemeral `SECRET_KEY` (`config.SECRET_FROM_ENV` false) → ERROR in
  production else WARNING; wildcard CORS in production → ERROR. DB schema is
  ensured here via `create_all` **only if `DB_CREATE_ALL`** (dev
  convenience); containers/CI set it false and run `alembic upgrade head`
  from the entrypoint. ML artifacts + the RAG index are pre-warmed.
- **Exception handlers** — `HTTPException`, `RequestValidationError`, and a
  catch-all `Exception`, all returning `{"detail", "request_id"}` (the
  shape the frontend reads). The catch-all logs a full traceback and
  returns a clean 500.
- **`/api/health`** — `status` (`ok` | `degraded`), `version`, `env`,
  `models_loaded`, `groq_configured`, `ocr_available`, `rag_ready`,
  `rag_chunks`. Used by the Docker/compose healthchecks.

## `config.py`

`pydantic-settings`; `.env` loaded, unknown keys ignored (`extra="ignore"`).
`SECRET_FROM_ENV` (module-level, not a field — pydantic-settings reserves
leading underscores) records whether `SECRET_KEY` was supplied. See
`.env.example` for the full tunable list.

## `jobs.py`

In-memory batch-job store + async pub/sub — see
[`docs/websockets.md`](../../docs/websockets.md).
