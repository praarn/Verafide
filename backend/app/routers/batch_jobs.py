"""Job-based batch review with a WebSocket progress stream.

Flow:
  1. POST /api/batch/jobs (multipart file)         -> {job_id}
  2. WS   /api/batch/jobs/{job_id}/ws?token=<jwt>  -> streams status snapshots
                                                      until state is terminal
  3. GET  /api/batch/jobs/{job_id}                 -> poll fallback (no WS)

The WebSocket is the "genuinely useful" case: a scanned PDF can take a
minute of OCR + classification, and a live processed/total count is much
better UX than a spinner.
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.jobs import create_job, get_job, run_batch_job
from app.models import User
from app.schemas import BatchJobStatus
from app.security import decode_access_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/batch", tags=["batch"])

# Hold strong references to in-flight job tasks — asyncio only keeps a weak
# reference, so without this the GC can cancel a job mid-run.
_BG_TASKS: set = set()


@router.post("/jobs", response_model=BatchJobStatus, status_code=202)
async def start_batch_job(
    file: UploadFile = File(...),
    mode: str = "classic",
    user: User = Depends(get_current_user),
):
    name = (file.filename or "").lower()
    if not name.endswith((".csv", ".pdf")):
        raise HTTPException(status_code=422, detail="Please upload a .csv or .pdf file.")
    raw = await file.read()
    if len(raw) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 25 MB.")

    job = create_job(owner_id=user.id)
    task = asyncio.create_task(run_batch_job(job, raw, file.filename or "upload", mode))
    _BG_TASKS.add(task)
    task.add_done_callback(_BG_TASKS.discard)
    return BatchJobStatus(**job.snapshot())


@router.get("/jobs/{job_id}", response_model=BatchJobStatus)
def get_batch_job(job_id: str, user: User = Depends(get_current_user)):
    job = get_job(job_id)
    if job is None or job.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found.")
    return BatchJobStatus(**job.snapshot())


def _user_from_token(token: str | None, db: Session) -> User | None:
    if not token:
        return None
    email = decode_access_token(token)
    if not email:
        return None
    return db.query(User).filter(User.email == email).first()


@router.websocket("/jobs/{job_id}/ws")
async def batch_job_ws(
    websocket: WebSocket,
    job_id: str,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    # Browsers can't set an Authorization header on a WebSocket, so the
    # access token comes in as a query param instead.
    user = _user_from_token(token, db)
    job = get_job(job_id)
    if user is None or job is None or job.owner_id != user.id:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    queue = job.subscribe()
    try:
        await websocket.send_json(job.snapshot())  # immediate current state
        if job.state in ("complete", "error"):
            return
        while True:
            try:
                snap = await asyncio.wait_for(queue.get(), timeout=90)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "keepalive"})
                continue
            await websocket.send_json(snap)
            if snap["state"] in ("complete", "error"):
                return
    except WebSocketDisconnect:
        pass
    finally:
        job.unsubscribe(queue)
