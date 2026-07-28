# Verafide — Fake News Detection Desk

A full-stack web app that analyzes news text, articles, and CSV batches for
credibility signals using machine learning, and presents the verdict through
an editorial "verification desk" interface.

```
fake-news-detection/
├── backend/     FastAPI + SQLAlchemy + scikit-learn
└── frontend/    React + Vite + Tailwind CSS v4 + Recharts
```

## Features

- **Text & URL analysis** — paste an article or hand it a link; Verafide
  fetches the article text itself and returns a verdict (real/fake) with a
  confidence score. The verdict itself comes from an LLM (Groq/Llama 3.3
  70B) that reasons about the actual writing — sourcing, tone, internal
  consistency, sensationalism — rather than matching against a fixed
  training vocabulary. If Groq isn't configured or is unavailable, this
  automatically and silently falls back to the local TF-IDF model, so
  Analyze never hard-depends on an external API. Signal words (the
  specific words that drove the verdict) always come from the local model
  regardless of which one produced the final label, since that
  explainability feature is free/instant and doesn't need an LLM.
- **Two model modes**
  - `classic` — TF-IDF + Logistic Regression (fast, fully interpretable)
  - `advanced` — TF-IDF + a multi-layer neural network (scikit-learn `MLPClassifier`)
- **Explainability** — every verdict comes with the specific words in the
  text that pushed the model toward "real" or "fake."
- **Batch review** — upload a CSV of articles/headlines, or a PDF (each
  page is analyzed as its own story — handy for a full newspaper-edition
  PDF), and get every verdict back in one pass (up to 200 rows/pages per
  file). Pages with normal embedded text are read directly. Two other
  cases are handled automatically via OCR (Tesseract): scanned/image-only
  pages, and — very common with Indian newspaper e-papers specifically —
  pages built with custom embedded fonts whose text *encoding* is broken,
  where the page displays as normal English visually but the underlying
  extracted characters are garbage Unicode codepoints. Both cases are
  detected (not just "is there text," but "is the text actually readable
  letters") and routed through OCR, which reads the rendered pixels rather
  than the broken text layer. OCR pages are processed **concurrently**
  (thread pool sized to your CPU core count) rather than one at a time —
  on a multi-core machine this cuts wall-clock time roughly proportional
  to core count for documents needing OCR on many pages. A hard cap
  (40 OCR pages per upload) bounds worst-case request time on very long
  scanned documents. After every PDF upload you'll see an honest
  extraction report — how many pages had real text, how many needed OCR,
  and how many couldn't be read at all — instead of a silent partial
  result. Batch Review deliberately uses the fast local model (not the
  LLM-reasoned verdict) for individual row/page scoring — running an LLM
  call per page would undo the concurrency work that keeps large PDFs
  responsive. The whole-document summarizer/chatbot below the results
  table still uses the LLM, since that's a single call regardless of how
  many pages were uploaded.
- **Accounts** — JWT-based auth; every user has their own private case
  history.
- **Case history** — every analysis is logged and can be reviewed or deleted.
- **Analytics dashboard** — verdict split, a 14-day activity trend, and
  live model performance metrics (accuracy/precision/recall/F1).
- **AI summarizer + chatbot** — after any text/URL analysis, generate a
  neutral summary or ask follow-up questions about the analyzed content,
  powered by Groq's API (Llama 3.3 70B by default). Requires your own free
  Groq API key — see setup below.
- **Attractive, distinctive UI** — a newsroom-forensics visual identity
  (ink/paper palette, Fraunces + Inter + IBM Plex Mono type system, an
  animated "verdict stamp" as the signature interaction).

## ⚠️ About the bundled model — read this first

The models are trained on a **blend of four sources** totaling ~13,300
balanced rows across 13 topic buckets (politics, world, business, sci/tech,
sports, health, finance, entertainment, environment, and general/satire):

| Source | What it contributes |
|---|---|
| `train_data_synthetic.csv` | Template-generated clickbait-vs-measured-prose pairs across 8 topics (built by `scripts/generate_dataset.py`) |
| `train_data_real.csv` | 6,335 real 2016-era political news articles, real vs. fabricated ([lutzhamel/fake-news](https://github.com/lutzhamel/fake-news), the McIntire dataset) |
| `train_data_agnews.csv` | Genuine published news blurbs across World/Sports/Business/Sci-Tech ([AG News](https://github.com/mhjabreel/CharCnn_Keras)) — real-only, added purely for topic/length diversity |
| `train_data_onion.csv` | Satirical vs. genuine headlines across almost every topic ([Onion-or-Not](https://github.com/lukefeilberg/onion)) |

**Why bother mixing four sources?** Trained on the political dataset alone,
the model hit 95% held-out accuracy — but that number was inflated: it had
learned "real == 2016-election vocabulary" rather than general credibility
signals, and failed on anything else (tech news, Fed announcements, literary
quotes). After broadening the training mix, held-out accuracy is a more
honest **~86%**, and it now correctly handles real news about the Fed,
Apple security patches, sports, etc. — content the narrower model got wrong.
This is a real, general lesson for this kind of project: a higher accuracy
number on one narrow dataset is often *worse*, not better.

**Before shipping this for real use**, consider adding: more non-English
sources, more recent real-world fake news examples (each dataset above
predates ~2018), and a genuine transformer model rather than TF-IDF —
bag-of-words models fundamentally can't reason about a claim's factual
content, only its lexical style.

To regenerate everything from scratch:
```bash
cd backend
python scripts/generate_dataset.py       # rebuilds the synthetic slice
# re-download the three real-world CSVs (see the docstring at the top of
# each build_*.py script for the curl command) into data/, then:
python scripts/build_real_dataset.py
python scripts/build_agnews_dataset.py
python scripts/build_onion_dataset.py
python scripts/combine_datasets.py       # merges + balances into train_data.csv
python scripts/train_models.py           # retrains both models
```

Similarly, the "advanced" mode is a real, from-scratch-trained neural
network — **not** a pretrained transformer like BERT (this build
environment has no access to download pretrained model weights). The
inference code in `backend/app/ml/inference.py` is written so you can drop
in a `transformers` pipeline as a third mode later without restructuring
the API.

## Quick start (local, no Docker)

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# generate the training data + train both models (only needed once,
# artifacts are already included in this zip under app/ml/artifacts/)
python scripts/generate_dataset.py
python scripts/train_models.py

cp .env.example .env            # edit SECRET_KEY for real deployments
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### Enabling OCR for scanned PDFs (recommended)

Batch Review can read scanned/image-only PDF pages (e.g. newspaper scans),
but this needs the Tesseract OCR engine installed on your machine — it's a
small, separate binary, not just a pip package:

- **Windows**: install from https://github.com/UB-Mannheim/tesseract/wiki
  (the `.exe` installer). After installing, make sure the install folder
  (e.g. `C:\Program Files\Tesseract-OCR`) is on your PATH, or set:
  ```
  # in backend/.env, or as a system env var
  TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
  ```
- **macOS**: `brew install tesseract`
- **Linux**: `sudo apt install tesseract-ocr`

Without Tesseract installed, everything else still works — regular
(non-scanned) PDFs, CSVs, text, and URLs are unaffected. Scanned pages will
just be reported as "unreadable" in the extraction summary instead of
being OCR'd, with a clear message pointing back to this section.

### Enabling the summarizer + chatbot (optional but recommended)

1. Get a free API key at https://console.groq.com/keys
2. Open `backend/.env` and set:
   ```
   GROQ_API_KEY=your-actual-key-here
   ```
3. Restart uvicorn. That's it — the Summarize/Ask-about-this panel on the
   Analyze page will start working. Without a key set, those two features
   return a clear error message instead of crashing; the core detection
   features work fine either way.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
App: http://localhost:5173 (proxies `/api` to `http://localhost:8000` in dev)

## Quick start (Docker)

```bash
docker compose up --build
```
- Frontend: http://localhost
- Backend: http://localhost:8000

Set a real `SECRET_KEY` env var before deploying anywhere public:
```bash
SECRET_KEY=$(openssl rand -hex 32) docker compose up --build
```

## Tech stack

| Layer      | Choice |
|------------|--------|
| Backend    | FastAPI, SQLAlchemy, Pydantic v2, python-jose (JWT), passlib (bcrypt) |
| ML         | scikit-learn (TF-IDF, Logistic Regression, MLPClassifier), pandas |
| Scraping   | requests + BeautifulSoup4 |
| PDF/OCR    | pypdf, PyMuPDF (page rasterization), Tesseract via pytesseract |
| Database   | SQLite by default (swap `DATABASE_URL` for Postgres/MySQL in production) |
| Frontend   | React 19, Vite, Tailwind CSS v4, React Router, Recharts, Axios, lucide-react |

## Production notes

- Swap SQLite for Postgres by changing `DATABASE_URL` (e.g.
  `postgresql://user:pass@host:5432/db`) — SQLAlchemy handles the rest.
- Put a real secret in `SECRET_KEY` and don't commit `.env`.
- The batch endpoint caps at 200 rows/request by design
  (`app/config.py: MAX_BATCH_ROWS`) — raise it if you add background/queued
  processing for larger files.
- CORS origins are configurable via `CORS_ORIGINS` in `.env`.

## Ideas for what to add next

- Real transformer model (DistilBERT) as a third analysis mode
- Rate limiting / per-user API quotas
- Team/workspace sharing of case history
- Export batch results as CSV/PDF
- Source-credibility lookup (cross-reference the domain) alongside the text model

Got suggestions or a different direction you'd like this pushed in? Let me
know and I'm happy to extend any part of this.
