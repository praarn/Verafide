def _register(client, email="ref@example.com"):
    r = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201
    return r.json()


def test_refresh_rotates_tokens(client):
    first = _register(client)
    r = client.post("/api/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert r.status_code == 200, r.text
    second = r.json()
    assert second["access_token"] != first["access_token"]
    assert second["refresh_token"] != first["refresh_token"]

    # New access token works
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {second['access_token']}"})
    assert me.status_code == 200


def test_old_refresh_token_is_revoked_after_use(client):
    first = _register(client, "ref2@example.com")
    client.post("/api/auth/refresh", json={"refresh_token": first["refresh_token"]})
    reuse = client.post("/api/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert reuse.status_code == 401


def test_reuse_detection_revokes_all_sessions(client):
    first = _register(client, "ref3@example.com")
    r2 = client.post("/api/auth/refresh", json={"refresh_token": first["refresh_token"]})
    live = r2.json()["refresh_token"]
    # Replay the consumed token -> should nuke the still-live one too
    client.post("/api/auth/refresh", json={"refresh_token": first["refresh_token"]})
    after = client.post("/api/auth/refresh", json={"refresh_token": live})
    assert after.status_code == 401


def test_logout_revokes_refresh_token(client):
    first = _register(client, "ref4@example.com")
    assert client.post("/api/auth/logout", json={"refresh_token": first["refresh_token"]}).status_code == 204
    assert client.post("/api/auth/refresh", json={"refresh_token": first["refresh_token"]}).status_code == 401


def test_refresh_token_cannot_be_used_as_bearer(client):
    first = _register(client, "ref5@example.com")
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {first['refresh_token']}"})
    assert r.status_code == 401


def test_unknown_refresh_token_rejected(client):
    assert client.post("/api/auth/refresh", json={"refresh_token": "x" * 40}).status_code == 401
