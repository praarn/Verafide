import io

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.ml.inference import predict as run_prediction
from app.ml.inference import predict_smart
from app.models import Prediction, User
from app.schemas import BatchResponse, BatchResultRow, PredictRequest, PredictResponse, PredictURLRequest
from app.utils.pdf_extract import PDFExtractError, extract_chunks_from_pdf
from app.utils.scraper import ArticleFetchError, fetch_article_text

router = APIRouter(prefix="/api/predict", tags=["predict"])


def _log_prediction(db: Session, user: User, source_type: str, source_ref, text: str, result: dict):
    entry = Prediction(
        owner_id=user.id,
        source_type=source_type,
        source_ref=source_ref,
        input_excerpt=text[:300],
        label=result["label"],
        confidence=result["confidence"],
        mode=result["mode"],
    )
    db.add(entry)
    db.commit()


@router.post("/text", response_model=PredictResponse)
def predict_text(payload: PredictRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        result = predict_smart(payload.text, mode=payload.mode)
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
        result = predict_smart(article["text"], mode=payload.mode)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    _log_prediction(db, user, "url", payload.url, article["text"], result)
    return PredictResponse(**result, source_title=article["title"], analyzed_text=article["text"])


@router.post("/batch", response_model=BatchResponse)
def predict_batch(
    file: UploadFile = File(...),
    mode: str = "classic",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
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

        text_col = None
        for candidate in ["text", "Text", "article", "content", "headline"]:
            if candidate in df.columns:
                text_col = candidate
                break
        if text_col is None:
            raise HTTPException(status_code=422, detail="CSV must contain a 'text' (or 'article'/'content'/'headline') column.")

        df = df.dropna(subset=[text_col]).head(settings.MAX_BATCH_ROWS)
        rows = [{"text": str(row[text_col]), "source_ref": None} for _, row in df.iterrows() if len(str(row[text_col]).strip()) >= 20]
        extraction_summary = {}
    else:
        raise HTTPException(status_code=422, detail="Please upload a .csv or .pdf file.")

    results = []
    fake_count = 0
    real_count = 0
    skipped_count = 0
    combined_parts = []
    combined_chars = 0
    MAX_COMBINED_CHARS = settings.GROQ_MAX_CONTEXT_CHARS  # single source of truth — see app/config.py

    for row in rows:
        text = row["text"]
        try:
            result = run_prediction(text, mode=mode)
        except ValueError as exc:
            skipped_count += 1
            print(f"[batch] skipped {row.get('source_ref')}: {exc}")  # visible in the uvicorn console
            continue
        if result["label"] == "fake":
            fake_count += 1
        else:
            real_count += 1
        results.append(BatchResultRow(
            text_excerpt=text[:160],
            label=result["label"],
            confidence=result["confidence"],
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

    combined_text = "\n\n".join(combined_parts)[:MAX_COMBINED_CHARS]

    return BatchResponse(
        results=results,
        total=len(results),
        fake_count=fake_count,
        real_count=real_count,
        extraction_summary=extraction_summary,
        combined_text=combined_text,
    )
