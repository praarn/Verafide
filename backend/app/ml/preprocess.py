import re

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_HTML_RE = re.compile(r"<.*?>")
_NON_ALPHA_RE = re.compile(r"[^a-zA-Z\s]")
_MULTISPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """Normalize raw article/headline text before vectorization.

    Kept deliberately simple (no external NLTK corpora / downloads) so the
    pipeline is fully reproducible offline: lowercase, strip URLs/HTML,
    drop punctuation & digits, collapse whitespace.
    """
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = _URL_RE.sub(" ", text)
    text = _HTML_RE.sub(" ", text)
    text = _NON_ALPHA_RE.sub(" ", text)
    text = _MULTISPACE_RE.sub(" ", text).strip()
    return text
