# Alembic migrations

`env.py` pulls the URL from `app.config.settings.DATABASE_URL` and the
target metadata from `app.database.Base`, so there is one source of truth.

```bash
alembic upgrade head                          # apply
alembic downgrade base                        # roll back everything
alembic revision --autogenerate -m "message"  # new migration from model changes
alembic history                               # list
```

`0001_initial` creates `users`, `predictions`, `refresh_tokens`. It is
dialect-agnostic — CI applies and rolls it back on real PostgreSQL, and it
also runs on SQLite.

Local dev without Postgres can skip Alembic and rely on `DB_CREATE_ALL=true`
(runs `Base.metadata.create_all` on startup). Containers set
`DB_CREATE_ALL=false` and the entrypoint runs `alembic upgrade head`.
