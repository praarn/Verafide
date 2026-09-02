# Implementation notes

The detailed docs moved into dedicated files:

| Topic | Doc |
|---|---|
| System overview, service layout, request flows | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Auth (access + refresh, rotation, reuse detection) | [`docs/auth.md`](docs/auth.md) |
| RAG retriever + corpus + fact-check index | [`docs/rag.md`](docs/rag.md) |
| Image / audio / URL modalities | [`docs/multimodal.md`](docs/multimodal.md) |
| Batch jobs + WebSocket progress | [`docs/websockets.md`](docs/websockets.md) |
| Docker Compose, CI, scaling | [`docs/deployment.md`](docs/deployment.md) |
| Training dataset + regeneration | [`docs/dataset.md`](docs/dataset.md) |
| Version history | [`CHANGELOG.md`](CHANGELOG.md) |

Component-level notes sit next to the code in `EXPLANATION.md` files:
`backend/app/`, `backend/app/ml/`, `backend/app/rag/`, `backend/tests/`,
`frontend/src/`.

## Repo map

```
backend/
  app/            FastAPI app (routers, ml, rag, middleware, jobs)
  alembic/        migrations
  data/           train_data.csv, fact_checks.csv
  scripts/        train_models.py, build_rag_index.py, dataset builders
  tests/          pytest suite
frontend/
  src/app/        Next.js App Router pages
  src/components/  UI
  src/lib/        api client, auth, types, helpers
docs/             topic docs
```
