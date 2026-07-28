import json
import re

from app.services.groq_client import GroqError, chat_completion

# Deliberately honest about what this can and can't do: Groq's hosted models
# have no internet access or real-time knowledge, so they cannot verify a
# specific claim against reality. What they CAN do is judge the same kind of
# surface patterns a careful human reader would — sourcing, tone, internal
# consistency — but with actual language understanding instead of matching
# against a fixed training vocabulary (which is the core limitation of the
# TF-IDF models). This is framed explicitly in the prompt so the model
# doesn't hallucinate false certainty about facts it has no way to check.
SYSTEM_PROMPT = (
    "You are a careful media-literacy analyst helping assess whether a piece of text "
    "shows the hallmarks of credible journalism or fabricated/misleading content. "
    "You do NOT have internet access or real-time knowledge, so you cannot verify "
    "specific facts, names, or events against ground truth — never claim to have "
    "confirmed or debunked a specific real-world fact. Instead, judge based on "
    "OBSERVABLE PATTERNS in the writing itself: sensationalized or emotionally "
    "manipulative language, vague or missing sourcing/attribution, logical leaps or "
    "unsupported claims presented as settled fact, clickbait structure, excessive "
    "urgency or fear appeals — versus measured tone, specific attributed sourcing, "
    "and normal journalistic conventions. "
    "Respond with ONLY a JSON object, no other text, no markdown fences: "
    '{"label": "real" or "fake", "confidence": a number between 0.0 and 1.0, '
    '"reasoning": "one or two sentence explanation of the patterns you observed"}'
)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class LLMVerdictError(Exception):
    pass


def get_llm_verdict(text: str, max_chars: int = 6000) -> dict:
    """Returns {"label": "real"|"fake", "confidence": float, "reasoning": str}.

    Raises LLMVerdictError if Groq is unavailable, errors, or returns
    something unparseable — callers should catch this and fall back to the
    local TF-IDF model so the core Analyze feature never hard-depends on an
    external API being configured and reachable.
    """
    snippet = text[:max_chars]
    try:
        raw = chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Assess this text:\n\n{snippet}"},
            ],
            temperature=0.1,
            max_tokens=250,
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

    return {"label": label, "confidence": round(confidence, 4), "reasoning": reasoning}
