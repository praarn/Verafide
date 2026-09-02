import json
import logging
import os

import joblib
import numpy as np

from app.ml.llm_verdict import LLMVerdictError, get_llm_verdict
from app.ml.preprocess import clean_text

logger = logging.getLogger(__name__)

ARTIFACT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")

# Confidence banding. A raw 0.51 and a raw 0.98 are both "fake" but mean
# very different things to a reader; every consumer of a verdict (API
# response, batch row, UI copy) reads the band from here so the thresholds
# can't drift apart. "low" is effectively "the model is guessing" — the UI
# softens the wording to "leans …" in that band.
CONFIDENCE_BANDS = ((0.85, "high"), (0.65, "moderate"))


def confidence_band(confidence: float) -> str:
    for threshold, name in CONFIDENCE_BANDS:
        if confidence >= threshold:
            return name
    return "low"


class ModelBundle:
    """Lazily loads the vectorizer + both classifiers once per process."""

    _vectorizer = None
    _classic = None
    _advanced = None
    _metrics = None

    @classmethod
    def load(cls):
        if cls._vectorizer is None:
            cls._vectorizer = joblib.load(os.path.join(ARTIFACT_DIR, "vectorizer.joblib"))
            cls._classic = joblib.load(os.path.join(ARTIFACT_DIR, "classic_model.joblib"))
            cls._advanced = joblib.load(os.path.join(ARTIFACT_DIR, "advanced_model.joblib"))
            metrics_path = os.path.join(ARTIFACT_DIR, "metrics.json")
            if os.path.exists(metrics_path):
                with open(metrics_path) as f:
                    cls._metrics = json.load(f)
        return cls._vectorizer, cls._classic, cls._advanced

    @classmethod
    def metrics(cls):
        cls.load()
        return cls._metrics or {}


def top_signal_words(vectorizer, classic_model, vector, top_k=6):
    """Returns the words in this specific text that pushed the classic
    (linear) model's decision most strongly toward FAKE or REAL. Used as a
    lightweight, human-readable explanation regardless of which model
    (classic or advanced) produced the final verdict."""
    feature_names = np.array(vectorizer.get_feature_names_out())
    coefs = classic_model.coef_[0]
    row = vector.toarray()[0]
    nonzero_idx = np.where(row != 0)[0]
    if len(nonzero_idx) == 0:
        return []
    contributions = row[nonzero_idx] * coefs[nonzero_idx]
    order = np.argsort(np.abs(contributions))[::-1][:top_k]
    words = []
    for idx in order:
        feat_idx = nonzero_idx[idx]
        weight = float(contributions[idx])
        words.append({
            "word": feature_names[feat_idx],
            "weight": round(weight, 4),
            "direction": "real" if weight > 0 else "fake",
        })
    return words


def predict(text: str, mode: str = "classic"):
    vectorizer, classic, advanced = ModelBundle.load()
    cleaned = clean_text(text)
    if not cleaned:
        raise ValueError("Text has no analyzable content after cleaning.")
    vector = vectorizer.transform([cleaned])

    model = advanced if mode == "advanced" else classic
    proba = model.predict_proba(vector)[0]  # [P(fake), P(real)]
    pred_label = int(np.argmax(proba))
    confidence = float(proba[pred_label])

    explanation = top_signal_words(vectorizer, classic, vector)

    return {
        "label": "real" if pred_label == 1 else "fake",
        "confidence": round(confidence, 4),
        "confidence_band": confidence_band(confidence),
        "probabilities": {"fake": round(float(proba[0]), 4), "real": round(float(proba[1]), 4)},
        "mode": mode,
        "signal_words": explanation,
    }


def predict_smart(text: str, mode: str = "classic", modality: str = "text",
                  media_context: str | None = None):
    """Tries an LLM-reasoned verdict (Groq, RAG-grounded) first — it judges
    actual writing patterns rather than matching a fixed training
    vocabulary, the core limitation of the local TF-IDF models. Falls back
    to the local model automatically if Groq isn't configured, errors, or
    times out, so this never hard-depends on an external API.

    Signal words always come from the local classic model regardless of
    which verdict wins. `media_context` carries analyst notes from the
    image/audio pre-processing step so the LLM can factor them in.
    """
    base = predict(text, mode=mode)
    base["modality"] = modality
    base["citations"] = []

    try:
        llm_result = get_llm_verdict(text, media_context=media_context)
    except LLMVerdictError as exc:
        logger.info("LLM verdict unavailable, using local model: %s", exc)
        base["verdict_source"] = "classic_fallback"
        base["llm_reasoning"] = None
        return base
    except Exception as exc:  # safety net — never let this feature break core analysis
        logger.warning("unexpected error calling LLM verdict, using local model: %s", exc)
        base["verdict_source"] = "classic_fallback"
        base["llm_reasoning"] = None
        return base

    label = llm_result["label"]
    confidence = llm_result["confidence"]
    probabilities = (
        {"fake": round(1 - confidence, 4), "real": round(confidence, 4)}
        if label == "real"
        else {"fake": round(confidence, 4), "real": round(1 - confidence, 4)}
    )

    return {
        "label": label,
        "confidence": confidence,
        "confidence_band": confidence_band(confidence),
        "probabilities": probabilities,
        "mode": mode,
        "modality": modality,
        "signal_words": base["signal_words"],
        "citations": llm_result.get("citations", []),
        "verdict_source": "llm",
        "llm_reasoning": llm_result["reasoning"],
    }
