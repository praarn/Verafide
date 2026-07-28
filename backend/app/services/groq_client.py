import requests

from app.config import settings


class GroqError(Exception):
    pass


def chat_completion(messages: list[dict], temperature: float = 0.3, max_tokens: int = 700) -> str:
    """Calls Groq's OpenAI-compatible /chat/completions endpoint.

    `messages` follows the standard OpenAI chat format:
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
    """
    if not settings.GROQ_API_KEY:
        raise GroqError(
            "No Groq API key configured. Set GROQ_API_KEY in backend/.env "
            "(get a free key at https://console.groq.com/keys)."
        )

    try:
        resp = requests.post(
            f"{settings.GROQ_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.GROQ_MODEL,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        raise GroqError(f"Could not reach Groq's API: {exc}") from exc

    if resp.status_code == 401:
        raise GroqError("Groq rejected the API key. Double-check GROQ_API_KEY in backend/.env.")
    if resp.status_code == 429:
        raise GroqError("Groq rate limit hit — wait a moment and try again.")
    if resp.status_code == 413:
        raise GroqError(
            "This document is too large for a single request under your Groq plan's rate limit. "
            "Lower GROQ_MAX_CONTEXT_CHARS in backend/.env, or upgrade your Groq tier for a higher "
            f"token limit. (Groq's response: {resp.text[:200]})"
        )
    if not resp.ok:
        raise GroqError(f"Groq API error ({resp.status_code}): {resp.text[:300]}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise GroqError(f"Unexpected response shape from Groq: {data}") from exc
