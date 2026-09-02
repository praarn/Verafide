import io
import logging

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.ml import source_credibility
from app.ml.inference import predict as run_prediction
from app.ml.inference import predict_smart
from app.ml.media import MediaError, analyze_audio, analyze_image
from app.models import Prediction, User
from app.schemas import (
    BatchResponse,
    BatchResultRow,
    PredictRequest,
    PredictResponse,
    PredictURLRequest,
)
from app.utils.pdf_extract import PDFExtractError, extract_chunks_from_pdf
from app.utils.scraper import ArticleFetchError, fetch_article_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/predict", tags=["predict"])

_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_AUDIO_EXTS = (".mp3", ".m4a", ".wav", ".webm", ".ogg", ".flac", ".mp4", ".mpeg", ".mpga")


def _log_prediction(db: Session, user: User, source_type: str, source_ref, text: str, result: dict):
    db.add(Prediction(
        owner_id=user.id,
        source_type=source_type,
        source_ref=source_ref,
        input_excerpt=text[:300],
        label=result["label"],
        confidence=result["confidence"],
        mode=result["mode"],
    ))
    db.commit()


@router.post("/text", response_model=PredictResponse)
def predict_text(payload: PredictRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        result = predict_smart(payload.text, mode=payload.mode, modality="text")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    _log_prediction(db, user, "text", None, payload.text, result)
    return PredictResponse(**result, analyzed_text=payload.text)


@router.post("/url", response_model=PredictResponse)
def predict_url(payload: PredictURLRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        article = fetch_article_text(payload.url)
    except ArticleFetchError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    try:
        result = predict_smart(article["text"], mode=payload.mode, modality="url")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    _log_prediction(db, user, "url", payload.url, article["text"], result)
    credibility = source_credibility.lookup(payload.url)  # advisory only
    return PredictResponse(
        **result,
        source_title=article["title"],
        source_credibility=credibility,
        analyzed_text=article["text"],
    )


@router.post("/image", response_model=PredictResponse)
async def predict_image(
    file: UploadFile = File(...),
    mode: str = "classic",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    raw = await file.read()
    if len(raw) > settings.MAX_IMAGE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Image exceeds {settings.MAX_IMAGE_MB:g} MB.")
    mime = (file.content_type or "").lower()
    if mime not in _IMAGE_TYPES:
        raise HTTPException(status_code=422, detail="Upload a JPEG, PNG, WebP, or GIF image.")

    try:
        vision = analyze_image(raw, mime)
    except MediaError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    extracted = vision["extracted_text"].strip()
    observations = vision["observations"].strip()
    if len(extracted) < 20 and len(observations) < 20:
        raise HTTPException(
            status_code=422,
            detail="No readable text or usable visual detail found in that image.",
        )
    analyzable = extracted if len(extracted) >= 20 else observations
    try:
        result = predict_smart(analyzable, mode=mode, modality="image", media_context=observations)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    _log_prediction(db, user, "image", file.filename, analyzable, result)
    return PredictResponse(
        **result,
        analyzed_text=analyzable,
        extracted_text=extracted or None,
        media_observations=observations or None,
    )


@router.post("/audio", response_model=PredictResponse)
async def predict_audio(
    file: UploadFile = File(...),
    mode: str = "classic",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    raw = await file.read()
    if len(raw) > settings.MAX_AUDIO_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Audio exceeds {settings.MAX_AUDIO_MB:g} MB.")
    name = (file.filename or "audio").lower()
    if not name.endswith(_AUDIO_EXTS):
        raise HTTPException(status_code=422, detail=f"Unsupported audio format. Use one of: {', '.join(_AUDIO_EXTS)}")

    try:
        out = analyze_audio(raw, file.filename or "audio.m4a")
    except MediaError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    transcript = out["transcript"].strip()
    if len(transcript) < 20:
        raise HTTPException(status_code=422, detail="Transcript too short to analyze.")
    try:
        result = predict_smart(transcript, mode=mode, modality="audio")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    _log_prediction(db, user, "audio", file.filename, transcript, result)
    return PredictResponse(**result, analyzed_text=transcript, transcript=transcript)


@router.post("/batch", response_model=BatchResponse)
def predict_batch(
    file: UploadFile = File(...),
    mode: str = "classic",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Synchronous batch. For a live progress bar on large PDFs use the
    job + WebSocket flow under /api/batch instead."""
    filename = file.filename.lower()
    raw = file.file.read()
    extraction_summary = None

    if filename.endswith(".pdf"):
        try:
            extraction = extract_chunks_from_pdf(raw, max_chunks=settings.MAX_BATCH_ROWS)
        except PDFExtractError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        chunks = extraction["chunks"]
        extraction_summary = extraction["summary"]
        rows = [{"text": c["text"], "source_ref": c["source_ref"]} for c in chunks]
    elif filename.endswith(".csv"):
        try:
            df = pd.read_csv(io.BytesIO(raw))
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not parse CSV: {exc}")
        text_col = next(
            (c for c in ["text", "Text", "article", "content", "headline"] if c in df.columns), None
        )
        if text_col is None:
            raise HTTPException(status_code=422, detail="CSV must contain a 'text' (or 'article'/'content'/'headline') column.")
        df = df.dropna(subset=[text_col]).head(settings.MAX_BATCH_ROWS)
        rows = [{"text": str(r[text_col]), "source_ref": None} for _, r in df.iterrows() if len(str(r[text_col]).strip()) >= 20]
        extraction_summary = {}
    else:
        raise HTTPException(status_code=422, detail="Please upload a .csv or .pdf file.")

    results, fake_count, real_count, skipped_count = [], 0, 0, 0
    combined_parts, combined_chars = [], 0
    MAX_COMBINED_CHARS = settings.GROQ_MAX_CONTEXT_CHARS

    for row in rows:
        text = row["text"]
        try:
            result = run_prediction(text, mode=mode)
        except ValueError as exc:
            skipped_count += 1
            logger.info("batch: skipped %s: %s", row.get("source_ref"), exc)
            continue
        if result["label"] == "fake":
            fake_count += 1
        else:
            real_count += 1
        results.append(BatchResultRow(
            text_excerpt=text[:160],
            label=result["label"],
            confidence=result["confidence"],
            confidence_band=result.get("confidence_band", "moderate"),
            source_ref=row["source_ref"],
            signal_words=result["signal_words"],
        ))
        _log_prediction(db, user, "batch", row["source_ref"] or file.filename, text, result)
        if combined_chars < MAX_COMBINED_CHARS:
            combined_parts.append(text)
            combined_chars += len(text)

    if extraction_summary is not None:
        extraction_summary["chunks_extracted"] = len(rows)
        extraction_summary["chunks_skipped_at_classification"] = skipped_count

    return BatchResponse(
        results=results,
        total=len(results),
        fake_count=fake_count,
        real_count=real_count,
        extraction_summary=extraction_summary,
        combined_text="\n\n".join(combined_parts)[:MAX_COMBINED_CHARS],
    )
