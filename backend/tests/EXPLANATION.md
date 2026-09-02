# Backend tests

`pytest`, from `backend/`:

```bash
pip install -r requirements-dev.txt
pytest
```

Config: `backend/pyproject.toml` (`[tool.pytest.ini_options]`).

## Hermetic by construction (`conftest.py`)

Env vars are set **before the app imports** so a test run never touches
Postgres or the network:

| var | value | why |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./_test_boot.db` | no Postgres needed; the `client` fixture still gives each test its own fresh `tmp_path` DB |
| `DB_CREATE_ALL` | `true` | schema via `create_all`, no Alembic in unit tests |
| `RATE_LIMIT_ENABLED` | `false` | the limiter has its own isolated test |
| `SECRET_KEY` | fixed | stable JWTs |
| `GROQ_API_KEY` | empty | forces the local-model path — **no network** |

Fixtures: `client` (TestClient + per-test SQLite via `get_db` override),
`auth_client` (adds a registered user's bearer token + `.refresh_token`).

## Coverage (50 tests)

| file | area |
|---|---|
| `test_health.py` | `/api/health` shape, `X-Request-ID` generate + echo |
| `test_auth_and_predict.py` | register/login/me, dup-email 400, predict needs auth, local-model predict shape (+`modality`, `citations`), text too-short/long → 422, batch CSV, analytics shape |
| `test_auth_refresh.py` | refresh rotation, consumed-token rejection, reuse-detection cascade, logout revocation, refresh-as-bearer rejection |
| `test_multimodal.py` | image + audio endpoints with Groq mocked; type/size guards |
| `test_batch_jobs.py` | job lifecycle via polling **and** `websocket_connect`; `4404` on bad token; owner isolation |
| `test_rag.py` | index build, retrieval relevance, seed fact-check match, `/api/rag/{search,status}` |
| `test_rate_limit.py` | throwaway app with a tiny limit: blocks after threshold, `429` + `Retry-After`, GETs never limited, `X-RateLimit-Remaining` |
| `test_source_credibility.py` | domain parsing (incl. two-part ccTLDs), tier lookups, unknown → None |
| `test_confidence_band.py` | threshold boundaries |

CI additionally applies + rolls back the Alembic migrations against a real
`postgres:16` service container.
