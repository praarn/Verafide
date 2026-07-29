# Verafide — Implementation Documentation

**A full-stack fake news detection platform** combining a locally-trained
machine learning classifier, an LLM-reasoned verdict layer, OCR-capable
document ingestion, and an AI summarizer/chatbot — presented through a
custom "verification desk" editorial interface.

This document describes what was built, how it works, and why specific
design decisions were made. For setup/run commands, see `README.md`.

---

## 1. Architecture Overview

```
fake-news-detection/
├── backend/                  FastAPI application
│   ├── app/
│   │   ├── main.py            App entrypoint, CORS, router registration
│   │   ├── config.py          Centralized settings (env-driven)
│   │   ├── database.py        SQLAlchemy engine/session
│   │   ├── models.py          ORM models: User, Prediction
│   │   ├── schemas.py         Pydantic request/response contracts
│   │   ├── security.py        Password hashing (bcrypt) + JWT
│   │   ├── deps.py            Auth dependency (current-user resolution)
│   │   ├── ml/
│   │   │   ├── preprocess.py    Text cleaning shared by train + inference
│   │   │   ├── inference.py     Local model inference + LLM verdict orchestration
│   │   │   ├── llm_verdict.py   Groq-based credibility reasoning
│   │   │   └── artifacts/       Trained vectorizer + classic + advanced models
│   │   ├── routers/
│   │   │   ├── auth.py          Register / login / me
│   │   │   ├── predict.py       Text / URL / batch (CSV+PDF) analysis
│   │   │   ├── history.py       Case history list/delete
│   │   │   ├── analytics.py     Aggregate stats + model metrics
│   │   │   └── assist.py        Groq summarizer + chatbot endpoints
│   │   ├── services/
│   │   │   └── groq_client.py   Thin Groq (OpenAI-compatible) API client
│   │   └── utils/
│   │       ├── scraper.py       Article text extraction from URLs
│   │       └── pdf_extract.py   PDF → text chunks, with OCR fallback
│   ├── data/                  Combined training dataset (CSV)
│   ├── scripts/                Dataset build/combine + model training scripts
│   └── requirements.txt
│
├── frontend/                  React 19 + Vite SPA
│   └── src/
│       ├── pages/              Landing, Login, Register, Dashboard (Analyze),
│       │                       History, BatchUpload, Analytics
│       ├── components/         Sidebar, ProtectedLayout, VerdictStamp,
│       │                       AssistPanel, StatCard, Loader
│       ├── context/             AuthContext (token/user state)
│       └── api/client.js       Axios instance with auth interceptor
│
├── docker-compose.yml          Backend + frontend (nginx) orchestration
└── README.md                   Setup/run instructions
```

**Data flow, end to end (single-article analyze):**
```
User pastes text or URL
   → (URL only) scraper.py fetches + extracts article text
   → inference.predict_smart()
        → tries Groq LLM verdict (reasoned, pattern-based judgment)
        → falls back to local TF-IDF model if Groq unavailable/fails
        → signal words always computed locally regardless of which won
   → Prediction row logged to SQLite (per-user history)
   → response includes: label, confidence, probabilities, signal words,
     verdict source, LLM reasoning (if used), full analyzed text
   → frontend renders verdict stamp, probability bar, signal words
   → AssistPanel (summarize / chat) becomes available using the same text
```

**Data flow, end to end (batch CSV/PDF):**
```
File uploaded (.csv or .pdf)
   → CSV: pandas reads rows from a text/article/content/headline column
   → PDF: pdf_extract.py, two passes:
        1. Fast native text extraction per page, validated for REAL
           readable content (not just word count — see §5)
        2. Pages that fail validation are OCR'd concurrently (thread pool)
   → each resulting chunk scored by the local model only (not the LLM —
     see §6 for why)
   → results table + extraction report (pages/OCR/failures) returned
   → all chunk text concatenated (capped) into combined_text
   → AssistPanel (whole-document summary/chat) uses combined_text
```

---

## 2. Backend

### 2.1 Framework & structure
- **FastAPI** app (`app/main.py`), routers mounted under `/api/*`
- **SQLAlchemy** ORM over **SQLite** by default (swappable to Postgres/MySQL
  via `DATABASE_URL`)
- **Pydantic v2** schemas define every request/response contract
- CORS origins configurable via `.env` (`CORS_ORIGINS`, comma-separated,
  parsed via a `cors_origins_list` property rather than a `list[str]` field
  — a `list[str]` Pydantic-settings field expects JSON-encoded values from
  `.env` and throws on a plain comma-separated string, which was a real bug
  hit and fixed during development)

### 2.2 Authentication
- JWT-based, via `python-jose`
- Passwords hashed with **`bcrypt`, called directly** (not through
  `passlib`) — `passlib`'s bcrypt backend had a version-compatibility bug
  with newer `bcrypt` releases that broke registration; calling `bcrypt`
  directly removes that dependency entirely
- Token issued on register/login, required (`Authorization: Bearer`) on
  every other endpoint via a `get_current_user` FastAPI dependency
- Every prediction/history row is scoped to `owner_id` — no cross-user data
  access

### 2.3 Database models (`app/models.py`)
- **`User`**: id, email (unique), full_name, hashed_password, created_at
- **`Prediction`**: id, owner_id (FK), source_type (`text`/`url`/`batch`),
  source_ref (URL or "page N"), input_excerpt, label, confidence, mode,
  created_at — every analysis (single or batch) writes one row per item

### 2.4 Configuration (`app/config.py`)
Single `Settings` object (pydantic-settings, reads `.env`), covering:
- `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `DATABASE_URL`
- `CORS_ORIGINS` (+ `cors_origins_list` property)
- `MAX_BATCH_ROWS` (200) — batch upload row/page cap
- `GROQ_API_KEY`, `GROQ_BASE_URL`, `GROQ_MODEL` (default
  `llama-3.3-70b-versatile`)
- `GROQ_MAX_CONTEXT_CHARS` (28,000) — **single source of truth** for how
  much text gets sent to Groq per request. Both the batch document builder
  and the summarize/chat endpoints read this one value, specifically to
  prevent the two from drifting out of sync (this happened once during
  development: one was raised to fix a truncation bug without updating the
  other, and the mismatch caused confusing behavior until unified here)
- `TESSERACT_CMD` — optional explicit path to the Tesseract OCR binary
  (needed on Windows if not on PATH)

---

## 3. Machine Learning — Local Model

### 3.1 Pipeline
- **TF-IDF vectorizer** (`max_features=6000`, unigrams+bigrams, `min_df=2`)
- Two classifiers trained on the same vectorizer output:
  - **`classic`** — Logistic Regression (fast, linearly interpretable)
  - **`advanced`** — a scikit-learn `MLPClassifier` (128→64 hidden layers)
- Both trained via `scripts/train_models.py`; artifacts (`vectorizer.joblib`,
  `classic_model.joblib`, `advanced_model.joblib`, `metrics.json`) are
  shipped pre-built so no training step is required to run the app

### 3.2 Text preprocessing (`app/ml/preprocess.py`)
Lowercasing, URL/HTML stripping, non-alphabetic character removal,
whitespace collapsing — identical function used at both training and
inference time to avoid train/serve skew.

### 3.3 Explainability ("signal words")
For any prediction, the classic (linear) model's coefficients are
multiplied against the input's TF-IDF vector to find which specific words
pushed the verdict most strongly toward "real" or "fake." This is computed
**even when the LLM verdict is the one shown** — it's local, instant, and
free, so it's always available regardless of which scoring path produced
the final label.

### 3.4 Training dataset
`data/train_data.csv` — **13,343 balanced rows across 13 topic buckets**,
built by combining four sources (`scripts/generate_dataset.py` +
`build_real_dataset.py` + `build_agnews_dataset.py` + `build_onion_dataset.py`
→ `combine_datasets.py`):

| Source | Contribution |
|---|---|
| Synthetic templates | Clickbait-vs-measured-prose pairs across 8 topics |
| McIntire dataset ([lutzhamel/fake-news](https://github.com/lutzhamel/fake-news)) | 6,335 real 2016-era political articles, real vs. fabricated |
| AG News ([mhjabreel/CharCnn_Keras](https://github.com/mhjabreel/CharCnn_Keras)) | Genuine World/Sports/Business/Sci-Tech blurbs — real-only, added for topic/length diversity |
| Onion-or-Not ([lukefeilberg/onion](https://github.com/lukefeilberg/onion)) | Satire vs. genuine headlines across almost every topic |

**Key finding from development:** trained on the political dataset alone,
held-out accuracy was 95% — but that number was misleading. The model had
learned "real = 2016-election vocabulary," not general credibility
signals, and failed on anything else (Fed announcements, tech news,
literary quotes all misclassified). After broadening the training mix,
accuracy dropped to a more honest **~86%**, but the model now correctly
handles topics far outside its original training domain. This is
documented prominently in the README as a general lesson: a higher
accuracy number on a narrow dataset is often *worse*, not better.

### 3.5 Known limitations of the local model
- Bag-of-words / TF-IDF fundamentally cannot reason about a claim's
  factual content — only its lexical style
- All four training sources predate ~2018; no recent examples
- English-only

---

## 4. Machine Learning — LLM-Reasoned Verdict

### 4.1 What it is and why it exists
`app/ml/llm_verdict.py` sends the analyzed text to Groq (Llama 3.3 70B by
default) with a system prompt that is explicit about the model's actual
capability boundary: **it has no internet access or real-time knowledge,
so it cannot verify a specific claim against reality.** Instead, it's
instructed to judge *observable writing patterns* — sensationalized
language, missing/vague sourcing, logical leaps, clickbait structure,
urgency/fear appeals — versus measured tone and normal journalistic
conventions. This is the same fundamental judgment a careful human reader
makes, but with real language understanding instead of matching against a
fixed training vocabulary, which is the core limitation of the TF-IDF
models.

### 4.2 Response contract & parsing robustness
The model is instructed to return **only** a JSON object:
```json
{"label": "real" | "fake", "confidence": 0.0-1.0, "reasoning": "..."}
```
Parsing is defensive against real-world LLM output variance — tested
against: clean JSON, markdown-fenced JSON, JSON preceded by prose, invalid
label values, missing/out-of-range confidence, and non-JSON responses.
Every failure mode raises a specific `LLMVerdictError` rather than
crashing, which triggers automatic fallback (§4.3).

### 4.3 Automatic fallback — no hard dependency on Groq
`predict_smart()` in `inference.py`:
1. Always computes the local TF-IDF prediction first (fast, free, also
   the source of signal words)
2. Attempts the Groq LLM verdict
3. On **any** failure (no API key configured, network error, rate limit,
   malformed response) — logs the reason server-side and returns the local
   model's result instead, marked `verdict_source: "classic_fallback"`
4. On success, returns the LLM's label/confidence, still paired with the
   local model's signal words, marked `verdict_source: "llm"`

This means the core Analyze feature works identically whether or not a
Groq API key is configured — the LLM verdict is a pure enhancement, never
a requirement.

### 4.4 Deliberate scope: Analyze only, not Batch Review
The LLM verdict is used for `/predict/text` and `/predict/url` (the
Analyze tab) but **not** for individual rows/pages in Batch Review. Running
an LLM call per page would mean a 20+ page newspaper batch making 20+
sequential Groq requests, which would completely undo the OCR concurrency
work described in §5.3. Batch Review's per-item scoring stays on the fast
local model; only the whole-document summarizer/chatbot (one call
regardless of page count) uses the LLM.

---

## 5. Document Ingestion (URL + PDF)

### 5.1 URL scraping (`app/utils/scraper.py`)
- Real browser User-Agent + headers (some sites serve a stripped-down page
  to unrecognized bot user-agents and the full page to browsers)
- Layered extraction strategy: known article-container selectors
  (`<article>`, `itemprop="articleBody"`, common CMS class patterns) →
  generic `<p>` sweep → `meta description`/`og:description` as a last
  resort, so genuinely short wire-service articles aren't rejected just
  for being short

### 5.2 PDF extraction (`app/utils/pdf_extract.py`)
Two-pass strategy:
1. **Fast pass** — native text extraction (pypdf) across every page
2. **Validation** — a page's text must pass `_has_real_text()`, which
   checks *actual readable letter density*, not just word count (see §5.4
   for why this specific check exists)
3. **OCR pass** — pages that fail validation are rasterized (PyMuPDF) and
   OCR'd (Tesseract via pytesseract), **concurrently** across a thread
   pool sized to CPU core count (§5.3)

Within a page, text is split into per-article chunks where real paragraph
breaks exist; pages with no detectable breaks (common — PDF extraction is
position-based, not semantic) fall back to fixed-size word windows so no
single verdict has to cover an entire page's unrelated content.

A hard cap (40 OCR pages/upload) bounds worst-case request time on very
long scanned documents.

### 5.3 OCR concurrency
Each OCR worker opens its **own** PyMuPDF document instance (verified this
is required — PyMuPDF documents aren't safe to render from multiple
threads sharing one instance) and calls Tesseract via `pytesseract`, which
shells out to an external binary and releases Python's GIL during that
call — meaning a `ThreadPoolExecutor` gives genuine wall-clock speedup on
multi-core machines despite Python's GIL, unlike pure-Python CPU work.

Measured on this project's single-core test environment: 20 pages, all
requiring OCR, completed in 36 seconds (no parallelism benefit available
on 1 core). On a multi-core machine, wall-clock time drops roughly
proportional to core count.

### 5.4 The broken-font-encoding problem (a specific, real bug found and fixed)
Many newspaper e-paper PDFs — this was reproduced and confirmed during
development — are typeset with custom embedded fonts that have **broken
text encoding**: the page displays as completely normal English visually,
but the underlying extracted characters are garbage Unicode codepoints,
not real letters. A naive "does this page have enough words" check
(counting whitespace-separated tokens) is fooled by this just as easily as
by real text, since garbage tokens still count as "words." The page then
silently passes extraction, gets stripped to nothing by the classifier's
text-cleaning step (which strips non-alphabetic characters), and the
prediction call raises an error that was being silently swallowed —
meaning entire newspaper pages would vanish from batch results with zero
explanation.

**Fix:** `_has_real_text()` checks the fraction of actual ASCII a-z
letters in the extracted text, not just token count. Pages that fail this
stricter check — whether truly image-scanned or broken-encoding — are
routed through OCR, which reads the rendered pixels and bypasses the
broken text layer entirely. This was verified against a synthetic PDF
reproducing the exact failure mode (garbage-encoded text overlaying a real
rendered image) before shipping.

### 5.5 Honest reporting instead of silent partial results
Every PDF batch upload returns an extraction summary: total pages, pages
with normal text, pages recovered via OCR, pages that couldn't be read at
all, whether OCR was available, and whether the OCR page cap was hit. The
frontend surfaces this as a visible banner rather than silently returning
a subset of results with no explanation (a real problem encountered and
fixed during development).

---

## 6. Batch Review

- Accepts **CSV** (a `text`/`article`/`content`/`headline` column) or
  **PDF** (each page/chunk treated as its own item)
- Up to 200 rows/pages per upload (`MAX_BATCH_ROWS`)
- Each result row is expandable (click to see full text + signal words),
  backed by the same `signal_words` computation as single-article Analyze
- `combined_text` (all chunk text, capped at `GROQ_MAX_CONTEXT_CHARS`) is
  returned alongside results specifically so the whole-document
  summarizer/chatbot (via `AssistPanel`) can operate on the entire
  uploaded document, not just one row
- Deliberately uses the **local model only** for per-item scoring (see
  §4.4) — the LLM is used exactly once per batch, for the document-level
  summary/chat, regardless of how many pages were uploaded

---

## 7. AI Summarizer + Chatbot (`app/routers/assist.py`)

- **Two endpoints**, both Groq-backed: `/assist/summarize` (short/detailed
  length options) and `/assist/chat` (multi-turn, stateless API replayed
  with trimmed history each request)
- Same `AssistPanel` component used in **both** Analyze (single article)
  and Batch Review (whole document) — the only difference is what text is
  passed as context and a `label` prop for natural copy ("summarize this
  text" vs. "summarize whole document")
- History retention capped (last 6 turns, 1,000 chars each) so a long
  conversation can't slowly grow a request back over Groq's rate limit
- Context length capped at `GROQ_MAX_CONTEXT_CHARS` (28,000 chars) — sized
  specifically to fit within Groq's free-tier 12,000-token-per-minute
  limit with headroom for the system prompt, history, and response. This
  number was tuned after hitting a real 413 "request too large" error in
  testing with a genuinely long document
- Both endpoints degrade gracefully with a clear error message (not a
  crash) if Groq isn't configured, rate-limited, or returns an error

---

## 8. Frontend

### 8.1 Stack
React 19, Vite, Tailwind CSS v4, React Router, Recharts (analytics
charts), Axios, lucide-react (icons).

### 8.2 Visual identity
A deliberate "newsroom forensics" concept rather than generic dashboard
styling:
- **Palette**: ink navy background, cream "paper" surfaces, verified-green
  and flagged-red verdict colors, signal-gold accent
- **Type system**: Fraunces (display serif, masthead feel), Inter (UI
  text), IBM Plex Mono (data/scores/timestamps)
- **Signature interaction**: an animated circular "verdict stamp" (SVG,
  rotated, ink-roughened via an SVG filter) that thuds onto the result
  card — green "VERIFIED" or red "FLAGGED" — as the one bold, memorable
  visual element

### 8.3 Pages
| Page | Purpose |
|---|---|
| `Landing.jsx` | Public marketing page with a live-feeling demo card |
| `Login.jsx` / `Register.jsx` | Auth forms, JWT stored client-side |
| `Dashboard.jsx` | **Analyze** — text/URL input, verdict stamp, probability split, signal words, AssistPanel |
| `BatchUpload.jsx` | CSV/PDF upload, extraction report, expandable results table, AssistPanel (whole document) |
| `History.jsx` | Past predictions, delete individual/all |
| `Analytics.jsx` | Verdict split (pie), 14-day trend (area chart), live model metrics |

### 8.4 Key components
- `VerdictStamp.jsx` — the signature animated SVG stamp
- `AssistPanel.jsx` — summarizer + chatbot, reused across Analyze and
  Batch Review with a `label` prop for context-appropriate copy
- `Sidebar.jsx` / `ProtectedLayout.jsx` — app shell + auth-gated routing
- `StatCard.jsx`, `Loader.jsx` — shared display primitives

### 8.5 State & auth
- `AuthContext.jsx` — holds user/token, persists to `localStorage`,
  validates the token against `/auth/me` on load
- `api/client.js` — Axios instance auto-attaching the bearer token and
  redirecting to `/login` on a 401

### 8.6 Deliberate UX simplification
An earlier iteration exposed a `classic` / `advanced` model toggle in both
Analyze and Batch Review. This was **removed entirely** at the user's
request — it added a decision with no clear benefit to the person actually
using the tool. Every request now silently uses the best available
verdict path (LLM with local fallback for Analyze; local model for Batch
Review) with no user-facing mode selection.

---

## 9. Deployment

- **Docker**: `docker-compose.yml` builds both services — backend
  (Python 3.11-slim, trains/bundles models at image build time) and
  frontend (multi-stage build served via nginx, which also proxies `/api`
  to the backend container)
- **Local dev**: documented per-OS (Windows/macOS/Linux) in `README.md`,
  each a complete top-to-bottom command sequence
- Production notes documented: swapping SQLite for Postgres via
  `DATABASE_URL`, setting a real `SECRET_KEY`, CORS configuration, and the
  batch row cap

---

## 10. Notable Bugs Found & Fixed During Development

Documented here because the *process* of finding them is part of the
project's implementation history:

1. **`CORS_ORIGINS` as `list[str]`** — pydantic-settings expects JSON for
   list-typed env fields; a plain comma-separated string crashed on
   startup. Fixed by using a `str` field + a `cors_origins_list` property.
2. **`passlib` + newer `bcrypt`** — a known compatibility break between
   `passlib`'s bcrypt backend and `bcrypt` ≥4.1. Fixed by calling `bcrypt`
   directly, dropping `passlib` entirely.
3. **Silent PDF batch under-reporting** — pages that failed classification
   (e.g. empty after text cleaning) were silently `continue`d with no
   visibility. Fixed by counting and surfacing skips in the extraction
   summary, plus server-side logging.
4. **Broken-font-encoding pages** — see §5.4. The single highest-impact
   bug found: a raw word-count check couldn't distinguish real text from
   garbage-encoded text, causing entire newspaper pages to silently vanish
   from results.
5. **OCR performance** — sequential, single-page-at-a-time OCR made large
   scanned PDFs feel hung with zero feedback. Fixed with concurrent
   OCR (thread pool) + a hard page cap for bounded worst-case time.
6. **Chatbot context truncation mismatch** — `combined_text` (batch) and
   the assist endpoints' context limit were two independently-set
   constants that drifted apart, silently cutting off page 3+ of a
   document from the chatbot's view. Fixed by centralizing the limit in
   `config.py` as a single source of truth.
7. **Groq 413 (request too large)** — raising the context limit to fix
   (6) without checking it against Groq's actual 12,000 TPM rate limit
   caused oversized requests to be rejected outright. Fixed by tuning the
   centralized limit down to a value that fits Groq's free tier, with
   history trimming as a second safeguard.

---

## 11. Explicitly Out of Scope (documented, not built)

These were discussed and intentionally deferred:
- Source-credibility/domain-reputation lookup
- Export batch/history results (CSV/PDF)
- Real transformer model (e.g. DistilBERT) as a third analysis mode
- Feedback loop (flagging incorrect verdicts to inform retraining)
- Side-by-side compare mode
- Shareable public case-report links
- Browser extension
- Org/team workspaces
- API keys + rate limiting for external consumers
