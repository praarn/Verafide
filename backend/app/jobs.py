"""In-memory batch-job store + async pub/sub for WebSocket progress.

Deliberately process-local and un-persisted: a batch job lives only as long
as the server process and is only meaningful to the client that started it.
For a multi-worker deployment this would move to a real queue (e.g. Redis /
RQ / Celery); the API shape here is designed so that swap is contained.
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
import uuid
from dataclasses import dataclass, field

import pandas as pd

from app.config import settings
from app.database import SessionLocal
from app.ml.inference import predict as run_prediction
from app.models import Prediction
from app.utils.pdf_extract import PDFExtractError, extract_chunks_from_pdf

logger = logging.getLogger(__name__)

_JOB_TTL_SECONDS = 3600
_MAX_JOBS = 200


@dataclass
class BatchJob:
    id: str
    owner_id: int
    total: int = 0
    processed: int = 0
    state: str = "pending"  # pending | running | complete | error
    error: str | None = None
    result: dict | None = None
    created_at: float = field(default_factory=time.time)
    _subscribers: list[asyncio.Queue] = field(default_factory=list)

    def snapshot(self) -> dict:
        return {
            "job_id": self.id,
            "state": self.state,
            "processed": self.processed,
            "total": self.total,
            "error": self.error,
            "result": self.result,
        }

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    def publish(self) -> None:
        snap = self.snapshot()
        for q in list(self._subscribers):
            q.put_nowait(snap)


_JOBS: dict[str, BatchJob] = {}


def _gc() -> None:
    now = time.time()
    stale = [j.id for j in _JOBS.values() if now - j.created_at > _JOB_TTL_SECONDS]
    for jid in stale:
        _JOBS.pop(jid, None)
    if len(_JOBS) > _MAX_JOBS:
        for jid in sorted(_JOBS, key=lambda k: _JOBS[k].created_at)[: len(_JOBS) - _MAX_JOBS]:
            _JOBS.pop(jid, None)


def create_job(owner_id: int) -> BatchJob:
    _gc()
    job = BatchJob(id=uuid.uuid4().hex[:16], owner_id=owner_id)
    _JOBS[job.id] = job
    return job


def get_job(job_id: str) -> BatchJob | None:
    return _JOBS.get(job_id)


def _rows_from_file(raw: bytes, filename: str) -> tuple[list[dict], dict | None]:
    name = filename.lower()
    if name.endswith(".pdf"):
        extraction = extract_chunks_from_pdf(raw, max_chunks=settings.MAX_BATCH_ROWS)
        summary = extraction["summary"]
        rows = [{"text": c["text"], "source_ref": c["source_ref"]} for c in extraction["chunks"]]
        summary["chunks_extracted"] = len(rows)
        return rows, summary
    if name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(raw))
        text_col = next(
            (c for c in ["text", "Text", "article", "content", "headline"] if c in df.columns),
            None,
        )
        if text_col is None:
            raise ValueError(
                "CSV must contain a 'text' (or 'article'/'content'/'headline') column."
            )
        df = df.dropna(subset=[text_col]).head(settings.MAX_BATCH_ROWS)
        rows = [
            {"text": str(r[text_col]), "source_ref": None}
            for _, r in df.iterrows()
            if len(str(r[text_col]).strip()) >= 20
        ]
        return rows, {}
    raise ValueError("Please upload a .csv or .pdf file.")


async def run_batch_job(job: BatchJob, raw: bytes, filename: str, mode: str) -> None:
    """Drives one job to completion, publishing progress after every row so
    a subscribed WebSocket streams a live count."""
    try:
        rows, extraction_summary = await asyncio.to_thread(_rows_from_file, raw, filename)
    except (PDFExtractError, ValueError) as exc:
        job.state, job.error = "error", str(exc)
        job.publish()
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("batch job %s: file parse failed", job.id)
        job.state, job.error = "error", f"Could not read that file: {exc}"
        job.publish()
        return

    job.total = len(rows)
    job.state = "running"
    job.publish()

    results: list[dict] = []
    fake_count = real_count = skipped = 0
    combined_parts: list[str] = []
    combined_chars = 0
    max_combined = settings.GROQ_MAX_CONTEXT_CHARS

    for row in rows:
        text = row["text"]
        try:
            res = await asyncio.to_thread(run_prediction, text, mode)
        except ValueError:
            skipped += 1
            job.processed += 1
            job.publish()
            continue

        if res["label"] == "fake":
            fake_count += 1
        else:
            real_count += 1
        results.append({
            "text_excerpt": text[:160],
            "label": res["label"],
            "confidence": res["confidence"],
            "confidence_band": res.get("confidence_band", "moderate"),
            "source_ref": row["source_ref"],
            "signal_words": res["signal_words"],
        })
        if combined_chars < max_combined:
            combined_parts.append(text)
            combined_chars += len(text)

        job.processed += 1
        job.publish()

    if extraction_summary is not None:
        extraction_summary["chunks_extracted"] = len(rows)
        extraction_summary["chunks_skipped_at_classification"] = skipped

    # Persist predictions in one shot off the event loop.
    await asyncio.to_thread(_persist, job.owner_id, filename, results)

    job.result = {
        "results": results,
        "total": len(results),
        "fake_count": fake_count,
        "real_count": real_count,
        "extraction_summary": extraction_summary,
        "combined_text": "\n\n".join(combined_parts)[:max_combined],
    }
    job.state = "complete"
    job.publish()


def _persist(owner_id: int, filename: str, results: list[dict]) -> None:
    db = SessionLocal()
    try:
        for r in results:
            db.add(Prediction(
                owner_id=owner_id,
                source_type="batch",
                source_ref=r["source_ref"] or filename,
                input_excerpt=r["text_excerpt"][:300],
                label=r["label"],
                confidence=r["confidence"],
                mode="classic",
            ))
        db.commit()
    except Exception:
        logger.exception("batch persist failed")
        db.rollback()
    finally:
        db.close()
