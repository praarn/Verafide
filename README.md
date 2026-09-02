# Verafide

**Multimodal misinformation analysis desk.** Paste text, a link, a
screenshot, or an audio clip and Verafide scores its credibility — combining
a locally-trained scikit-learn model, an LLM that reasons over the writing,
and retrieval-augmented grounding in a media-literacy corpus and a
fact-check index. It presents the verdict through an editorial
"verification desk" interface.

> Verdicts are model estimates, not fact-checks. Always confirm with primary
> sources.

---

## About

Verafide is a portfolio-grade full-stack project built to exercise a modern
production stack end to end:

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 15 (App Router) · TypeScript · Tailwind CSS v4 |
| **Backend** | Python · FastAPI · Pydantic v2 · REST + WebSockets |
| **Database** | PostgreSQL · SQLAlchemy · Alembic migrations |
| **AI / Data** | scikit-learn · pandas · NumPy · Groq LLM API · RAG (TF-IDF retriever) · Whisper STT · vision LLM |
| **Auth** | JWT access + refresh tokens (rotating, revocable) |
| **Infra** | Docker · Docker Compose · GitHub Actions |
| **Testing** | pytest · FastAPI `TestClient` (incl. WebSocket) |

It is deliberately **not** a microservice sprawl: two services (plus
Postgres), one compose file, no Kubernetes.

---

## What it does

### Four input modalities, one verdict pipeline
| Modality | How it's handled |
|---|---|
| **Text** | Cleaned → TF-IDF → local classifier, then an LLM re-reasons over the raw writing. |
| **URL** | Article text is fetched and extracted server-side, then analyzed as text. Known domains also get an advisory source-reputation tier. |
| **Image** | A vision LLM transcribes the text and notes manipulation cues; **falls back to local Tesseract OCR** if the API key has no vision access. |
| **Audio** | Transcribed with Groq Whisper, then analyzed as text. |

### RAG-grounded reasoning
Every LLM verdict and every chatbot answer retrieves from a unified index:

- **~14 curated media-literacy notes** (`backend/app/rag/corpus/*.md`) —
  sensationalism, sourcing standards, logical fallacies, satire markers,
  propaganda techniques, deepfake tells, and more.
- **An ingestible fact-check dataset** (`backend/data/fact_checks.csv`, seeded
  with ~25 well-documented debunked claims; drop in your own CSV to expand).

Retrieval is a scikit-learn **TF-IDF + cosine-similarity** index — offline,
fast, and inside the stack. Retrieved passages are shown to the user as
citations.

### Live batch review over WebSockets
Upload a CSV or a full newspaper PDF. A background job classifies each
row/page and streams `processed / total` progress over a WebSocket
(`/api/batch/jobs/{id}/ws`); the client falls back to HTTP polling if the
socket can't be established. Scanned or broken-encoding PDF pages are routed
through OCR, concurrently.

### The rest
- **Explainability** — the specific words that pushed the local model toward
  real/fake, on every verdict.
- **Confidence banding** — `high` / `moderate` / `low`, with the UI softening
  "FLAGGED" to "LEANS FLAGGED" in the low band.
- **Auth** — register / login issue an access token (30 min) + a rotating
  refresh token (14 days) stored hashed; reuse of a consumed refresh token
  revokes the whole session family.
- **Case history & analytics** — every analysis is logged; the dashboard
  charts verdict split, a 14-day trend, input-type breakdown, RAG index
  status, and live model metrics.
- **AI summarizer + chatbot** — neutral summary or grounded Q&A over any
  analyzed content.
- **Ops** — per-client rate limiting, request-id correlation + structured
  logs, a consistent error envelope, and a readiness `/api/health`.

---

## Architecture

```
                 ┌───────────────────────────┐
  browser ─────▶ │  Next.js 15 (TS, :3000)   │
                 │  /api/* → proxy to API    │
                 │  ws://host:8000 for batch │
                 └───────────┬───────────────┘
                             │ REST + WS
                 ┌───────────▼───────────────┐        ┌──────────────┐
                 │  FastAPI (:8000)          │───────▶│ PostgreSQL   │
                 │  routers/ · middleware    │  ORM   │ (SQLAlchemy) │
                 │  ┌─────────────────────┐  │        └──────────────┘
                 │  │ ml/  inference      │  │
                 │  │      llm_verdict ───┼──┼──▶ Groq API (chat / vision / whisper)
                 │  │      media (OCR)    │  │
                 │  │ rag/ retriever ─────┼──┼──▶ TF-IDF index (corpus + fact_checks.csv)
                 │  │ jobs (batch + WS)   │  │
                 │  └─────────────────────┘  │
                 └───────────────────────────┘
```

More detail: [`ARCHITECTURE.md`](ARCHITECTURE.md) and the topic docs in
[`docs/`](docs/) (`auth.md`, `rag.md`, `multimodal.md`, `websockets.md`,
`deployment.md`). Component-level notes live in `EXPLANATION.md` files under
`backend/app/`, `backend/app/ml/`, `backend/app/rag/`, `backend/tests/`, and
`frontend/src/`.

---

## Quick start (Docker — nothing else to install)

```bash
git clone https://github.com/praarn/Verafide.git
cd Verafide
cp backend/.env.example backend/.env   # optional: add GROQ_API_KEY for LLM features
SECRET_KEY=$(openssl rand -hex 32) GROQ_API_KEY=your_key docker compose up --build
```

- Web: http://localhost:3000
- API docs: http://localhost:8000/docs

Without a `GROQ_API_KEY` everything still works — the verdict falls back to
the local scikit-learn model, and image analysis uses local OCR.

## Local development

### Backend

```bash
cd backend
python3.12 -m venv venv && . venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env                                   # defaults to SQLite for local dev
python scripts/train_models.py                         # build ML artifacts (gitignored)
python scripts/build_rag_index.py                      # build the RAG index (gitignored)
uvicorn app.main:app --reload --port 8000
```

For Postgres locally: set `DATABASE_URL=postgresql+psycopg://…` in `.env`,
then `alembic upgrade head` instead of relying on `DB_CREATE_ALL`.

### Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:3000, proxies /api to :8000
```

### Handy targets

```bash
make help          # list everything
make test          # backend pytest
make lint          # ruff + eslint
make typecheck     # tsc --noEmit
make migrate       # alembic upgrade head
```

## The bundled ML model — read this

The classifier is trained on a **blend of four sources** (~13,300 balanced
rows across 13 topic buckets): a synthetic clickbait/measured-prose set, the
McIntire political real-vs-fake set, AG News (real-only, for topic
diversity), and Onion-or-Not (satire). Held-out accuracy is a deliberately
honest **~86%** — training on the political set alone gave an inflated 95%
that failed on everything else.

A bag-of-words model fundamentally cannot reason about a claim's factual
content, only its lexical style. That is exactly why Verafide layers an LLM
verdict and RAG grounding on top, and why `backend/app/ml/inference.py` is
structured to accept a transformer as a third mode.

Retrain: `python scripts/train_models.py` (needs `data/train_data.csv`,
which is committed). Regenerate the whole dataset: see
[`docs/dataset.md`](docs/dataset.md).

## Testing

```bash
cd backend && pytest        # 50 tests, SQLite, no network (Groq mocked / disabled)
```

Covers auth + refresh rotation + reuse detection, all four predict
modalities, the batch job lifecycle **and its WebSocket**, RAG retrieval,
rate limiting, and the analytics shape. CI additionally applies the Alembic
migrations against a real PostgreSQL service container.

## Production notes

- Set a real `SECRET_KEY`; startup logs an error in `ENV=production` if it's
  ephemeral.
- The rate limiter is in-memory / per-process — front multi-replica
  deployments with a gateway or shared store and set `RATE_LIMIT_ENABLED=false`.
- `DB_CREATE_ALL=false` in containers; the entrypoint runs `alembic upgrade head`.
- Groq rotates its hosted model catalogue — if `GROQ_MODEL` starts 404-ing,
  pick a current one from https://console.groq.com/docs/models.
