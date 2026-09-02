"""Pre-processing for the image and audio modalities.

Each turns a non-text upload into (a) analyzable text and (b) optional
analyst notes, which are then handed to the same `predict_smart` pipeline
the text and URL routes use.
"""

import io
import logging

from app.config import settings
from app.services.groq_client import GroqError, transcribe_audio, vision_completion

logger = logging.getLogger(__name__)


class MediaError(Exception):
    pass


def _ocr_image(image_bytes: bytes) -> str:
    """Local fallback when a Groq vision model isn't available on the key.
    Reads text from the pixels with Tesseract; no 'visual manipulation'
    observations, but the screenshot's text still gets analyzed."""
    try:
        import pytesseract
        from PIL import Image

        if settings.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        img = Image.open(io.BytesIO(image_bytes))
        return (pytesseract.image_to_string(img) or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.info("image OCR fallback failed: %s", exc)
        return ""


_VISION_PROMPT = (
    "You are assisting a misinformation-analysis tool. Look at this image (it may be a "
    "news screenshot, a social-media post, a headline card, a meme, or a photo).\n\n"
    "Return EXACTLY two labelled sections:\n"
    "TEXT: verbatim transcription of ALL readable text in the image (headline, body, "
    "captions, username/handle, timestamps, watermarks). If there is no text, write "
    "'(none)'.\n"
    "OBSERVATIONS: 2-4 short bullet points on anything relevant to credibility — the "
    "apparent source/outlet, whether it looks like an authentic screenshot vs a "
    "fabricated graphic, signs of digital manipulation, emotional or clickbait framing, "
    "missing attribution. Do NOT give a real/fake verdict."
)


def _split_sections(raw: str) -> tuple[str, str]:
    text_part, obs_part = "", ""
    lower = raw.lower()
    if "text:" in lower:
        after = raw[lower.index("text:") + 5:]
        if "observations:" in after.lower():
            cut = after.lower().index("observations:")
            text_part = after[:cut].strip()
            obs_part = after[cut + len("observations:"):].strip()
        else:
            text_part = after.strip()
    else:
        text_part = raw.strip()
    if text_part.strip().lower() in ("(none)", "none", ""):
        text_part = ""
    return text_part.strip(), obs_part.strip()


def analyze_image(image_bytes: bytes, mime_type: str) -> dict:
    """-> {"extracted_text": str, "observations": str}

    Prefers the Groq vision model (text transcription + credibility
    observations). If the key has no vision access, degrades to local
    Tesseract OCR for text extraction only.
    """
    try:
        raw = vision_completion(image_bytes, mime_type, _VISION_PROMPT, max_tokens=800)
        extracted_text, observations = _split_sections(raw)
        return {"extracted_text": extracted_text, "observations": observations}
    except GroqError as exc:
        logger.info("Groq vision unavailable (%s); falling back to local OCR", exc)

    ocr_text = _ocr_image(image_bytes)
    if not ocr_text:
        raise MediaError(
            "Could not analyze that image: the Groq vision model is unavailable on this "
            "API key and local OCR found no readable text. Try an image with clearer text."
        )
    return {
        "extracted_text": ocr_text,
        "observations": "(Visual analysis unavailable - text extracted locally via OCR.)",
    }


def analyze_audio(audio_bytes: bytes, filename: str) -> dict:
    """-> {"transcript": str}"""
    try:
        transcript = transcribe_audio(audio_bytes, filename)
    except GroqError as exc:
        raise MediaError(
            f"Audio transcription needs the Groq Whisper model and it was unavailable: {exc}"
        ) from exc
    return {"transcript": transcript}
