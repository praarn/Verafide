import logging

from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models import User
from app.rag import rag_status, retrieve
from app.schemas import Citation, RagSearchRequest, RagSearchResponse, RagStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.get("/status", response_model=RagStatus)
def status():
    return RagStatus(**rag_status())


@router.post("/search", response_model=RagSearchResponse)
def search(payload: RagSearchRequest, user: User = Depends(get_current_user)):
    hits = retrieve(payload.query, k=payload.k)
    return RagSearchResponse(results=[Citation(**h) for h in hits])
