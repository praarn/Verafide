import json
import logging
import re

from app.config import settings
from app.rag import retrieve
from app.services.groq_client import GroqError, chat_completion

logger = logging.getLogger(__name__)

# The model has no internet access and cannot verify a specific fact against
# reality. It CAN judge surface patterns a careful reader would — sourcing,
# tone, internal consistency — with real language understanding rather than
# a fixed training vocabulary. When RAG context is supplied, it may also
# lean on the retrieved media-literacy notes / prior fact-checks. This is
# stated in the prompt so the model doesn't fabricate false certainty.
SYSTEM_PROMPT = (
    "You are a careful media-literacy analyst assessing whether a piece of text shows "
    "the hallmarks of credible journalism or fabricated/misleading content. You do NOT "
    "have internet access or real-time knowledge, so you cannot verify specific facts, "
    "names, or events — never claim to have confirmed or debunked a specific real-world "
    "fact. Judge OBSERVABLE PATTERNS: sensationalized or emotionally manipulative "
    "language, vague or missing sourcing, logical leaps, clickbait structure, fear "
    "appeals — versus measured tone, specific attributed sourcing, and normal "
    "journalistic conventions. If reference notes are provided, you may use them to "
    "inform your reasoning and cite them by number. "
    'Respond with ONLY a JSON object, no markdown fences: '
    '{"label": "real" or "fake", "confidence": number 0.0-1.0, '
    '"reasoning": "one or two sentences on the patterns you observed", '
    '"citation_ids": [list of reference numbers you actually used, may be empty]}'
)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class LLMVerdictError(Exception):
    pass


def _format_references(passages: list[dict]) -> str:
    lines = []
    for i, p in enumerate(passages, start=1):
        lines.append(f"[{i}] ({p['title']}) {p['snippet']}")
    return "\n".join(lines)


def get_llm_verdict(text: str, max_chars: int = 6000, media_context: str | None = None) -> dict:
    """Returns {"label", "confidence", "reasoning", "citations"}.

    Raises LLMVerdictError if Groq is unavailable/errors/returns garbage so
    callers can fall back to the local TF-IDF model.
    """
    snippet = text[:max_chars]

    passages: list[dict] = []
    if settings.RAG_ENABLED:
        try:
            passages = retrieve(text[:2000])
        except Exception:  # retrieval must never break the verdict
            logger.exception("RAG retrieval failed; continuing without references")
            passages = []

    user_parts = []
    if media_context:
        user_parts.append(f"ANALYST NOTES ON THE SOURCE MEDIA:\n{media_context}\n")
    if passages:
        user_parts.append("REFERENCE NOTES (media-literacy guidance / prior fact-checks):\n"
                          + _format_references(passages) + "\n")
    user_parts.append(f"Assess this text:\n\n{snippet}")
    user_content = "\n".join(user_parts)

    try:
        raw = chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=350,
        )
    except GroqError as exc:
        raise LLMVerdictError(str(exc)) from exc

    match = _JSON_BLOCK_RE.search(raw)
    if not match:
        raise LLMVerdictError(f"No JSON object found in LLM response: {raw[:200]!r}")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise LLMVerdictError(f"Could not parse LLM JSON: {exc}") from exc

    label = str(data.get("label", "")).strip().lower()
    if label not in ("real", "fake"):
        raise LLMVerdictError(f"LLM returned an invalid label: {label!r}")
    try:
        confidence = float(data.get("confidence"))
    except (TypeError, ValueError):
        raise LLMVerdictError("LLM returned an invalid confidence value")
    confidence = max(0.0, min(1.0, confidence))
    reasoning = str(data.get("reasoning", "")).strip()

    used_ids = data.get("citation_ids") or []
    citations = []
    if isinstance(used_ids, list):
        for n in used_ids:
            try:
                idx = int(n) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= idx < len(passages):
                citations.append(passages[idx])
    # If the model cited nothing but retrieval was confident, still surface
    # the top hit so the UI can show "grounded in:".
    if not citations and passages:
        citations = passages[:2]

    return {
        "label": label,
        "confidence": round(confidence, 4),
        "reasoning": reasoning,
        "citations": citations,
    }
