# RAG (retrieval-augmented grounding)

Every LLM verdict and every chatbot answer retrieves supporting passages
and passes them to the model as numbered references; the passages it
actually used come back as **citations** shown in the UI.

## Why TF-IDF, not embeddings

- Groq has no embeddings endpoint; `sentence-transformers` would drag in
  PyTorch (~2 GB) — a poor trade for a corpus this small.
- scikit-learn is already in the stack. A `TfidfVectorizer` + cosine
  similarity over a few hundred short chunks retrieves the *right
  media-literacy concept* reliably and in microseconds, fully offline.

The retrieval interface (`retrieve(query, k) -> list[Citation]`) is the
seam — swapping in a vector DB later touches only `rag/retriever.py`.

## The index

Two sources, one unified index (`backend/app/rag/retriever.py`):

1. **`app/rag/corpus/*.md`** — ~14 hand-written notes on misinformation
   techniques (sensationalism, sourcing, fallacies, satire markers,
   propaganda devices, deepfake tells, statistics misuse, scam framing,
   lateral reading, coordinated inauthentic behavior…). Each file is split
   into chunks on `##` headings.
2. **`backend/data/fact_checks.csv`** — a fact-check dataset. Seeded with
   ~25 well-documented debunked claims; columns are auto-detected
   (`claim`/`statement`/…, `rating`/`verdict`/…, `source`/`url`/…,
   `explanation`/`review`/…). Drop in a bigger CSV to expand.

Build: lazy on first use, or eagerly via `python scripts/build_rag_index.py`
(the Docker image bakes it in). Cached to
`app/rag/artifacts/rag_index.joblib` (gitignored). `RAG_ENABLED=false`
turns the whole thing off; verdicts then use no references.

## Config

| Env | Default | Meaning |
|---|---|---|
| `RAG_ENABLED` | `true` | master switch |
| `RAG_TOP_K` | `4` | passages retrieved per query |
| `RAG_MIN_SCORE` | `0.08` | min cosine similarity to include a passage |

## Endpoints

- `POST /api/rag/search` `{query, k}` → ranked `Citation[]` (debug / explore).
- `GET /api/rag/status` → `{enabled, ready, total_chunks, media_literacy_docs, fact_check_entries, built_at}`.

## How it grounds a verdict

`ml/llm_verdict.py` builds the user message as:

```
[ANALYST NOTES ON THE SOURCE MEDIA: ...]   (image/audio only)
REFERENCE NOTES:
[1] (title) snippet…
[2] (title) snippet…
Assess this text:
<text>
```

The model returns `citation_ids`; those indices map back to the passage
objects. If it cites nothing but retrieval was confident, the top 1–2
passages are still surfaced as "grounded in:".
