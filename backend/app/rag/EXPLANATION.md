# RAG retriever

Full rationale + config: [`docs/rag.md`](../../../docs/rag.md).

## Files

| Path | Role |
|---|---|
| `retriever.py` | index build + load + `retrieve()` + `rag_status()` |
| `corpus/*.md` | ~14 curated media-literacy notes; split into chunks on `##` headings |
| `artifacts/rag_index.joblib` | cached `{chunks, vectorizer, matrix, meta}` (gitignored) |
| `../../data/fact_checks.csv` | optional fact-check dataset, columns auto-detected |

## Design points

- **TF-IDF + cosine similarity** (`sklearn`), not embeddings — no extra
  service, no PyTorch, fully offline, fast on a small corpus. The
  `retrieve(query, k) -> list[dict]` signature is the swap-point for a
  vector DB later.
- **Lazy singleton** `get_index()` — loads the joblib artifact if present,
  else builds and persists it. Thread-safe via a module lock;
  `_load_attempted` prevents a rebuild storm if the corpus is broken.
  `reset_cache()` exists for tests.
- Failure is non-fatal everywhere: `retrieve()` returns `[]` if the index
  can't be built, and `RAG_ENABLED=false` short-circuits it.
- `rag_status()` powers `GET /api/rag/status`, `/api/health`, and the
  Analytics page.

## Rebuild

`python scripts/build_rag_index.py` — also run at Docker build time. Rerun
after editing anything in `corpus/` or replacing `fact_checks.csv`.

## Tests

`backend/tests/test_rag.py` — index builds from the corpus, retrieves the
right media-literacy note for a clickbait query, matches a seed fact-check
("5G / COVID"), and the `/api/rag/{search,status}` endpoints.
