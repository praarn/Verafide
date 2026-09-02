"""Image + audio endpoints, with the Groq vision / Whisper calls mocked so
the tests stay offline. The downstream verdict still runs the real local
model (no GROQ key -> classic_fallback)."""

import io

import pytest

from app.ml import media


@pytest.fixture()
def mock_vision(monkeypatch):
    def _fake(image_bytes, mime_type, prompt, temperature=0.2, max_tokens=700):
        return (
            "TEXT: BREAKING!! Doctors HATE this one weird trick that cures everything. "
            "Share before Big Pharma DELETES this!!!\n"
            "OBSERVATIONS:\n- Looks like a low-quality graphic, not a real newsroom screenshot\n"
            "- Heavy clickbait and suppression framing\n- No outlet name or byline visible"
        )
    monkeypatch.setattr(media, "vision_completion", _fake)


@pytest.fixture()
def mock_whisper(monkeypatch):
    def _fake(audio_bytes, filename):
        return (
            "According to a statement released Tuesday, the health department reported a "
            "modest decline in seasonal flu cases and said further details would follow."
        )
    monkeypatch.setattr(media, "transcribe_audio", _fake)


def test_image_endpoint(auth_client, mock_vision):
    r = auth_client.post(
        "/api/predict/image",
        files={"file": ("post.png", io.BytesIO(b"\x89PNG\r\n\x1a\n fake bytes"), "image/png")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["modality"] == "image"
    assert body["extracted_text"] and "trick" in body["extracted_text"].lower()
    assert body["media_observations"]
    assert body["label"] in ("real", "fake")


def test_image_rejects_non_image(auth_client, mock_vision):
    r = auth_client.post(
        "/api/predict/image",
        files={"file": ("x.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert r.status_code == 422


def test_audio_endpoint(auth_client, mock_whisper):
    r = auth_client.post(
        "/api/predict/audio",
        files={"file": ("clip.m4a", io.BytesIO(b"fake audio bytes"), "audio/mp4")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["modality"] == "audio"
    assert body["transcript"].startswith("According to a statement")
    assert body["label"] in ("real", "fake")


def test_audio_rejects_unknown_extension(auth_client, mock_whisper):
    r = auth_client.post(
        "/api/predict/audio",
        files={"file": ("clip.xyz", io.BytesIO(b"fake"), "application/octet-stream")},
    )
    assert r.status_code == 422
