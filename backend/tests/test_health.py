def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert body["models_loaded"] is True  # artifacts ship in the repo
    assert "version" in body


def test_request_id_header_present(client):
    resp = client.get("/api/health")
    assert resp.headers.get("X-Request-ID")


def test_request_id_is_echoed_back(client):
    resp = client.get("/api/health", headers={"X-Request-ID": "abc123"})
    assert resp.headers.get("X-Request-ID") == "abc123"
