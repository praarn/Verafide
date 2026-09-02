import io
import time

CSV = (
    "text\n"
    '"Officials confirmed a modest decline in seasonal flu cases according to figures released Tuesday."\n'
    '"SHOCKING miracle cure they are HIDING from you - share before it is DELETED!!!"\n'
    '"The central bank held rates steady, citing stable inflation, per its published statement."\n'
).encode()


def _start(auth_client):
    r = auth_client.post(
        "/api/batch/jobs",
        files={"file": ("stories.csv", io.BytesIO(CSV), "text/csv")},
    )
    assert r.status_code == 202, r.text
    return r.json()["job_id"]


def test_job_completes_via_polling(auth_client):
    job_id = _start(auth_client)
    deadline = time.time() + 20
    body = None
    while time.time() < deadline:
        body = auth_client.get(f"/api/batch/jobs/{job_id}").json()
        if body["state"] in ("complete", "error"):
            break
        time.sleep(0.15)
    assert body and body["state"] == "complete", body
    assert body["result"]["total"] == 3
    assert body["result"]["fake_count"] + body["result"]["real_count"] == 3


def test_job_not_found_for_other_user(auth_client, client):
    job_id = _start(auth_client)
    other = client.post("/api/auth/register", json={"email": "other@x.com", "password": "password123"}).json()
    r = client.get(
        f"/api/batch/jobs/{job_id}",
        headers={"Authorization": f"Bearer {other['access_token']}"},
    )
    assert r.status_code == 404


def test_websocket_streams_progress_to_completion(auth_client):
    token = auth_client.headers["Authorization"].split(" ", 1)[1]
    job_id = _start(auth_client)
    seen_states = []
    with auth_client.websocket_connect(f"/api/batch/jobs/{job_id}/ws?token={token}") as ws:
        for _ in range(200):
            msg = ws.receive_json()
            if msg.get("type") == "keepalive":
                continue
            seen_states.append(msg["state"])
            if msg["state"] in ("complete", "error"):
                assert msg["result"]["total"] == 3
                break
    assert "complete" in seen_states


def test_websocket_rejects_bad_token(auth_client):
    job_id = _start(auth_client)
    try:
        with auth_client.websocket_connect(f"/api/batch/jobs/{job_id}/ws?token=garbage") as ws:
            ws.receive_json()
        raised = False
    except Exception:
        raised = True
    assert raised
