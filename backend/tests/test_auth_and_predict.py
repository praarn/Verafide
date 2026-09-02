import io


def test_register_login_me_flow(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "a@b.com", "full_name": "A", "password": "password123"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["refresh_token"]
    assert body["expires_in"] > 0
    token = body["access_token"]

    r = client.post("/api/auth/login", json={"email": "a@b.com", "password": "password123"})
    assert r.status_code == 200

    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.com"


def test_duplicate_registration_rejected(client):
    payload = {"email": "dup@b.com", "password": "password123"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 400


def test_predict_requires_auth(client):
    r = client.post("/api/predict/text", json={"text": "x" * 40})
    assert r.status_code == 401


def test_predict_text_local_model(auth_client):
    text = (
        "You won't believe this SHOCKING secret the government doesn't want you to know! "
        "Share before it gets DELETED forever!!!"
    )
    r = auth_client.post("/api/predict/text", json={"text": text})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["label"] in ("real", "fake")
    assert body["confidence_band"] in ("high", "moderate", "low")
    assert body["modality"] == "text"
    assert body["verdict_source"] == "classic_fallback"  # no GROQ key in tests
    assert isinstance(body["citations"], list)
    assert 0.0 <= body["probabilities"]["fake"] <= 1.0


def test_predict_text_too_short_is_422(auth_client):
    assert auth_client.post("/api/predict/text", json={"text": "too short"}).status_code == 422


def test_predict_text_too_long_is_422(auth_client):
    assert auth_client.post("/api/predict/text", json={"text": "word " * 20000}).status_code == 422


def test_batch_csv_roundtrip(auth_client):
    csv_bytes = b"text\n" + b"\n".join([
        b"Officials confirmed a modest decline in seasonal flu cases according to figures released Tuesday.",
        b"MIRACLE cure they are HIDING from you click now before deleted!!!",
    ])
    r = auth_client.post(
        "/api/predict/batch",
        files={"file": ("stories.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2
    assert body["fake_count"] + body["real_count"] == 2
    assert body["results"][0]["confidence_band"] in ("high", "moderate", "low")


def test_analytics_summary_shape(auth_client):
    auth_client.post("/api/predict/text", json={"text": "A calm, sourced report from the department, released Tuesday, on flu trends."})
    r = auth_client.get("/api/analytics/summary")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_predictions"] >= 1
    assert "by_modality" in body and isinstance(body["by_modality"], dict)
    assert "by_day" in body
