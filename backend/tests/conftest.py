"""Shared pytest fixtures.

Tests run against a throwaway SQLite database (never the dev/Postgres one)
and with the rate limiter disabled — the limiter has its own dedicated
test that re-enables it explicitly. No test hits the network: GROQ_API_KEY
is forced empty so every verdict falls back to the local model.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./_test_boot.db")
os.environ.setdefault("DB_CREATE_ALL", "true")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("SECRET_KEY", "test-secret-not-random")
os.environ.setdefault("GROQ_API_KEY", "")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture()
def auth_client(client):
    """A TestClient with a registered user's access token pre-attached."""
    resp = client.post(
        "/api/auth/register",
        json={"email": "tester@example.com", "full_name": "Tester", "password": "supersecret1"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    client.headers.update({"Authorization": f"Bearer {body['access_token']}"})
    client.refresh_token = body["refresh_token"]  # type: ignore[attr-defined]
    return client
