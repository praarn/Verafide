# Changelog

## 2.0.0 — Stack migration + multimodal + RAG

Full re-platform to the target stack. No feature removed; several added.

### Frontend
- **Rewritten from Vite + React + JavaScript to Next.js 15 (App Router) +
  TypeScript.** All screens ported (landing, auth, analyze, batch, history,
  analytics) plus new UI: 4-modality analyze tabs with drag-drop upload,
  RAG citation panels, live batch progress bar, RAG-index status card,
  input-type chart, mobile sidebar, skeleton/focus polish.
- axios client with transparent single-flight 401→refresh→retry.

### Backend
- **PostgreSQL** via SQLAlchemy + **Alembic** migrations (initial revision
  `0001_initial`). `DB_CREATE_ALL` toggles the dev `create_all` path.
- **JWT refresh tokens** — access (30 min, `type`/`jti` claims) + opaque
  rotating refresh (14 d, stored hashed, revocable); reuse detection
  cascades a session-wide revoke. `/auth/refresh`, `/auth/logout` added.
- **Multimodal** — `POST /api/predict/image` (Groq vision → local Tesseract
  OCR fallback) and `/api/predict/audio` (Groq Whisper). `modality` on every
  response.
- **RAG** — `app/rag/` TF-IDF retriever over ~14 media-literacy corpus docs
  + an ingestible `data/fact_checks.csv`. Grounds the LLM verdict and the
  chatbot; passages surface as `citations`. `/api/rag/search`,
  `/api/rag/status`.
- **WebSockets** — job-based batch review: `POST /api/batch/jobs` +
  `WS /api/batch/jobs/{id}/ws` streaming `processed/total`, HTTP-poll
  fallback. Sync `/api/predict/batch` retained.
- Analytics adds `by_modality`; the 14-day bucket moved to Python for
  SQLite/PostgreSQL portability.
- Groq client extended (`vision_completion`, `transcribe_audio`); default
  `GROQ_MODEL` set to a currently-available model.

### Infra / tooling
- `docker-compose.yml` — added `postgres:16` with healthcheck; backend
  entrypoint runs `alembic upgrade head`; both app images non-root with
  `HEALTHCHECK`; frontend is a Next `standalone` build.
- CI — Postgres service container + Alembic apply/rollback; frontend job
  runs eslint + `tsc --noEmit` + `next build`.
- Docs — new `ARCHITECTURE.md` and `docs/{auth,rag,multimodal,websockets,deployment,dataset}.md`;
  `EXPLANATION.md` refreshed across `backend/app`, `.../ml`, `.../rag`,
  `backend/tests`, `frontend/src`.
- Tests: 50, incl. refresh rotation/reuse, all 4 modalities, batch job +
  WebSocket, RAG retrieval.

## 1.1.0 — Robustness sweep

- Source-credibility advisory signal for URLs; confidence banding.
- In-memory rate limiting; request-id correlation + structured logging;
  consistent error envelope; startup diagnostics; richer `/api/health`.
- Payload size caps (schema + scraper); streamed URL download.
- Frontend: batch CSV export, confidence-band display.
- First `pytest` suite + CI + `Makefile` + Docker hardening.

## 1.0.0 — Initial

TF-IDF + LogisticRegression / MLPClassifier fake-news classifier, Groq
LLM verdict with local fallback, PDF/OCR batch review, JWT auth, case
history, analytics, React + Vite frontend.
