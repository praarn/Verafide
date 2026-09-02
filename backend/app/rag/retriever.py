"""Lightweight, offline RAG retriever.

No embedding API and no heavy vector store: the corpus is small and the
retrieval quality bottleneck here is recall of the *right* media-literacy
concept, which a TF-IDF + cosine-similarity index handles well while
staying inside the project's stack (scikit-learn) and needing zero extra
services. The index is built once and cached to a joblib artifact.

Two sources feed one unified index:
  1. `corpus/*.md`      - curated media-literacy / misinformation-technique notes
  2. `data/fact_checks.csv` (optional) - ingested public fact-check rows
"""

from __future__ import annotations

import csv
import datetime
import logging
import os
import re
import threading

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.path.join(_HERE, "corpus")
ARTIFACT_PATH = os.path.join(_HERE, "artifacts", "rag_index.joblib")
FACTCHECK_CSV = os.path.join(_HERE, "..", "..", "data", "fact_checks.csv")

_lock = threading.Lock()
_index: "RagIndex | None" = None
_load_attempted = False


class RagIndex:
    def __init__(self, chunks, vectorizer, matrix, meta):
        self.chunks = chunks  # list[dict]: id, title, source, text
        self.vectorizer = vectorizer
        self.matrix = matrix
        self.meta = meta  # dict

    def search(self, query: str, k: int, min_score: float) -> list[dict]:
        if not query.strip() or not self.chunks:
            return []
        q = self.vectorizer.transform([query])
        sims = cosine_similarity(q, self.matrix)[0]
        order = sims.argsort()[::-1][: max(k, 1)]
        out = []
        for i in order:
            score = float(sims[i])
            if score < min_score:
                continue
            c = self.chunks[i]
            out.append({
                "id": c["id"],
                "title": c["title"],
                "source": c["source"],
                "snippet": _snippet(c["text"]),
                "score": round(score, 4),
            })
        return out


def _snippet(text: str, limit: int = 320) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def _split_markdown(md: str) -> list[tuple[str, str]]:
    """(heading, body) pairs, splitting on '## ' sections."""
    parts = re.split(r"\n(?=##\s)", md)
    out = []
    for part in parts:
        lines = part.strip().splitlines()
        if not lines:
            continue
        head = lines[0].lstrip("#").strip() if lines[0].startswith("#") else ""
        body = "\n".join(lines[1:] if head else lines).strip()
        if len(body) < 40:
            continue
        out.append((head, body))
    return out


def _load_corpus_chunks() -> list[dict]:
    chunks: list[dict] = []
    if not os.path.isdir(CORPUS_DIR):
        return chunks
    for fname in sorted(os.listdir(CORPUS_DIR)):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(CORPUS_DIR, fname)
        with open(path, encoding="utf-8") as fh:
            md = fh.read()
        doc_title = fname[:-3].replace("-", " ").replace("_", " ").title()
        first = md.strip().splitlines()[0] if md.strip() else ""
        if first.startswith("# "):
            doc_title = first[2:].strip()
        for i, (head, body) in enumerate(_split_markdown(md)):
            title = f"{doc_title}: {head}" if head else doc_title
            chunks.append({
                "id": f"{fname[:-3]}#{i}",
                "title": title,
                "source": f"media-literacy/{fname}",
                "text": f"{title}\n{body}",
            })
    return chunks


def _load_factcheck_chunks() -> list[dict]:
    path = os.path.normpath(FACTCHECK_CSV)
    if not os.path.isfile(path):
        return []
    chunks: list[dict] = []
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        cols = {c.lower(): c for c in (reader.fieldnames or [])}

        def pick(*names):
            for n in names:
                if n in cols:
                    return cols[n]
            return None

        claim_c = pick("claim", "statement", "text", "headline", "title")
        rating_c = pick("rating", "verdict", "label", "truth_rating")
        src_c = pick("source", "url", "publisher", "fact_checker", "author")
        expl_c = pick("explanation", "review", "summary", "body", "description")
        if not claim_c:
            logger.warning("fact_checks.csv has no recognizable claim column; skipping")
            return []
        for i, row in enumerate(reader):
            claim = (row.get(claim_c) or "").strip()
            if not claim:
                continue
            rating = (row.get(rating_c) or "").strip() if rating_c else ""
            expl = (row.get(expl_c) or "").strip() if expl_c else ""
            src = (row.get(src_c) or "").strip() if src_c else "fact-check dataset"
            body = f"Claim: {claim}"
            if rating:
                body += f"\nRating: {rating}"
            if expl:
                body += f"\nExplanation: {expl}"
            chunks.append({
                "id": f"factcheck#{i}",
                "title": (f"Fact-check: {claim[:80]}" + ("…" if len(claim) > 80 else "")),
                "source": src or "fact-check dataset",
                "text": body,
            })
    return chunks


def build_index(persist: bool = True) -> RagIndex:
    corpus = _load_corpus_chunks()
    factchecks = _load_factcheck_chunks()
    chunks = corpus + factchecks
    if not chunks:
        raise RuntimeError("RAG corpus is empty — no markdown docs found in app/rag/corpus/")

    vectorizer = TfidfVectorizer(
        stop_words="english", ngram_range=(1, 2), min_df=1, max_df=0.9, sublinear_tf=True
    )
    matrix = vectorizer.fit_transform([c["text"] for c in chunks])
    meta = {
        "total_chunks": len(chunks),
        "media_literacy_docs": len({c["source"] for c in corpus}),
        "media_literacy_chunks": len(corpus),
        "fact_check_entries": len(factchecks),
        "built_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }
    index = RagIndex(chunks, vectorizer, matrix, meta)

    if persist:
        os.makedirs(os.path.dirname(ARTIFACT_PATH), exist_ok=True)
        joblib.dump(
            {"chunks": chunks, "vectorizer": vectorizer, "matrix": matrix, "meta": meta},
            ARTIFACT_PATH,
        )
        logger.info("RAG index built: %s", meta)
    return index


def get_index() -> RagIndex | None:
    """Lazy singleton. Loads the joblib artifact if present, else builds it.
    Returns None only if RAG is disabled or the corpus can't be assembled."""
    global _index, _load_attempted
    if not settings.RAG_ENABLED:
        return None
    if _index is not None:
        return _index
    with _lock:
        if _index is not None:
            return _index
        if _load_attempted and _index is None:
            return None
        _load_attempted = True
        try:
            if os.path.isfile(ARTIFACT_PATH):
                blob = joblib.load(ARTIFACT_PATH)
                _index = RagIndex(blob["chunks"], blob["vectorizer"], blob["matrix"], blob["meta"])
            else:
                _index = build_index()
        except Exception:
            logger.exception("Could not load/build the RAG index — retrieval disabled this run")
            _index = None
    return _index


def reset_cache() -> None:
    global _index, _load_attempted
    with _lock:
        _index = None
        _load_attempted = False


def retrieve(query: str, k: int | None = None) -> list[dict]:
    idx = get_index()
    if idx is None:
        return []
    return idx.search(query, k or settings.RAG_TOP_K, settings.RAG_MIN_SCORE)


def rag_status() -> dict:
    idx = get_index()
    if idx is None:
        return {
            "enabled": settings.RAG_ENABLED,
            "ready": False,
            "total_chunks": 0,
            "media_literacy_docs": 0,
            "fact_check_entries": 0,
            "built_at": None,
        }
    m = idx.meta
    return {
        "enabled": True,
        "ready": True,
        "total_chunks": m.get("total_chunks", len(idx.chunks)),
        "media_literacy_docs": m.get("media_literacy_docs", 0),
        "fact_check_entries": m.get("fact_check_entries", 0),
        "built_at": m.get("built_at"),
    }
