"""The real app disables the limiter in tests (see conftest). Here we build
a throwaway app with the middleware and a deliberately tiny limit so the
sliding-window logic itself is exercised."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import middleware
from app.config import settings


def _tiny_app(monkeypatch, limit=3, window=60):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_REQUESTS", limit)
    monkeypatch.setattr(settings, "RATE_LIMIT_HEAVY_REQUESTS", limit)
    monkeypatch.setattr(settings, "RATE_LIMIT_WINDOW_SECONDS", window)

    app = FastAPI()
    app.add_middleware(middleware.RateLimitMiddleware)

    @app.post("/api/ping")
    def ping():
        return {"ok": True}

    @app.get("/api/ping")
    def ping_get():
        return {"ok": True}

    return app


def test_limits_after_threshold(monkeypatch):
    c = TestClient(_tiny_app(monkeypatch, limit=3))
    codes = [c.post("/api/ping").status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200]
    assert codes[3] == 429
    assert codes[4] == 429


def test_429_has_retry_after_and_detail(monkeypatch):
    c = TestClient(_tiny_app(monkeypatch, limit=1))
    c.post("/api/ping")
    blocked = c.post("/api/ping")
    assert blocked.status_code == 429
    assert blocked.headers.get("Retry-After")
    assert "Rate limit" in blocked.json()["detail"]


def test_get_requests_are_not_limited(monkeypatch):
    c = TestClient(_tiny_app(monkeypatch, limit=2))
    codes = [c.get("/api/ping").status_code for _ in range(10)]
    assert all(code == 200 for code in codes)


def test_remaining_header_counts_down(monkeypatch):
    c = TestClient(_tiny_app(monkeypatch, limit=5))
    first = c.post("/api/ping")
    assert first.headers["X-RateLimit-Limit"] == "5"
    assert first.headers["X-RateLimit-Remaining"] == "4"
