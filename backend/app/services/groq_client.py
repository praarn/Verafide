"""Thin wrapper over Groq's OpenAI-compatible API.

Three capabilities, all over plain `requests` so the only dependency is one
we already have:
  - chat_completion      : text chat / reasoning
  - vision_completion     : image + prompt -> text (Llama 4 Scout)
  - transcribe_audio      : audio bytes -> text (Whisper)
"""

import base64
import logging

import requests

from app.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 45


class GroqError(Exception):
    pass


def _require_key() -> None:
    if not settings.GROQ_API_KEY:
        raise GroqError(
            "No Groq API key configured. Set GROQ_API_KEY in backend/.env "
            "(free key at https://console.groq.com/keys)."
        )


def _raise_for_status(resp: requests.Response) -> None:
    if resp.status_code == 401:
        raise GroqError("Groq rejected the API key. Check GROQ_API_KEY in backend/.env.")
    if resp.status_code == 429:
        raise GroqError("Groq rate limit hit — wait a moment and try again.")
    if resp.status_code == 413:
        raise GroqError(
            "Payload too large for your Groq plan's rate limit. Lower "
            "GROQ_MAX_CONTEXT_CHARS or upgrade your Groq tier."
        )
    if not resp.ok:
        raise GroqError(f"Groq API error ({resp.status_code}): {resp.text[:300]}")


def chat_completion(messages: list[dict], temperature: float = 0.3, max_tokens: int = 700,
                    model: str | None = None) -> str:
    _require_key()
    try:
        resp = requests.post(
            f"{settings.GROQ_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model or settings.GROQ_MODEL,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise GroqError(f"Could not reach Groq's API: {exc}") from exc

    _raise_for_status(resp)
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise GroqError(f"Unexpected response shape from Groq: {data}") from exc


def vision_completion(image_bytes: bytes, mime_type: str, prompt: str,
                      temperature: float = 0.2, max_tokens: int = 700) -> str:
    """Send one image + a text prompt to the vision model."""
    _require_key()
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{b64}"
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]
    try:
        resp = requests.post(
            f"{settings.GROQ_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.GROQ_VISION_MODEL,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise GroqError(f"Could not reach Groq's API: {exc}") from exc

    _raise_for_status(resp)
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise GroqError(f"Unexpected response shape from Groq: {data}") from exc


def transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    """Groq Whisper transcription. Returns plain text."""
    _require_key()
    try:
        resp = requests.post(
            f"{settings.GROQ_BASE_URL}/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            files={"file": (filename or "audio.m4a", audio_bytes)},
            data={"model": settings.GROQ_WHISPER_MODEL, "response_format": "json"},
            timeout=_TIMEOUT * 2,
        )
    except requests.RequestException as exc:
        raise GroqError(f"Could not reach Groq's API: {exc}") from exc

    _raise_for_status(resp)
    data = resp.json()
    text = (data.get("text") or "").strip()
    if not text:
        raise GroqError("Transcription came back empty.")
    return text
