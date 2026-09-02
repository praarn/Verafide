import logging

from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.deps import get_current_user
from app.models import User
from app.rag import retrieve
from app.schemas import (
    ChatRequest,
    ChatResponse,
    Citation,
    SummarizeRequest,
    SummarizeResponse,
)
from app.services.groq_client import GroqError, chat_completion

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/assist", tags=["assist"])

MAX_HISTORY_TURNS = 6
MAX_HISTORY_MESSAGE_CHARS = 1000

SUMMARY_SYSTEM_PROMPT = (
    "You are a neutral news summarization assistant embedded in a fake-news-detection "
    "tool called Verafide. Summarize ONLY what is stated in the given text — do not add "
    "outside facts, opinions, or speculation. If the text is too short or unclear to "
    "summarize meaningfully, say so plainly instead of inventing content."
)

CHAT_SYSTEM_PROMPT = (
    "You are a helpful assistant embedded in a fake-news-detection tool called Verafide. "
    "Answer the user's questions using the article/text provided as context. You may also "
    "use the REFERENCE NOTES (media-literacy guidance) when they help explain a technique "
    "or pattern, citing them by number. If the answer isn't in the context or references, "
    "say so honestly rather than guessing. Be concise and factual, and avoid stating a "
    "definitive real/fake verdict yourself — that's a separate model's job."
)


@router.post("/summarize", response_model=SummarizeResponse)
def summarize(payload: SummarizeRequest, user: User = Depends(get_current_user)):
    text = payload.text[: settings.GROQ_MAX_CONTEXT_CHARS]
    length_instruction = (
        "Summarize in 2-3 short sentences."
        if payload.length == "short"
        else "Summarize in 5-8 sentences, including a short bullet list of the key facts or claims."
    )
    try:
        summary = chat_completion(
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": f"{length_instruction}\n\nTEXT:\n{text}"},
            ],
            temperature=0.2,
            max_tokens=500,
        )
    except GroqError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return SummarizeResponse(summary=summary)


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, user: User = Depends(get_current_user)):
    context = payload.context[: settings.GROQ_MAX_CONTEXT_CHARS]

    passages = []
    if payload.use_rag and settings.RAG_ENABLED:
        try:
            passages = retrieve(f"{payload.question}\n{context[:1000]}")
        except Exception:
            logger.exception("RAG retrieval failed in chat; continuing without references")

    system = f"{CHAT_SYSTEM_PROMPT}\n\nARTICLE/TEXT:\n{context}"
    if passages:
        refs = "\n".join(f"[{i}] ({p['title']}) {p['snippet']}" for i, p in enumerate(passages, 1))
        system += f"\n\nREFERENCE NOTES:\n{refs}"

    messages = [{"role": "system", "content": system}]
    for turn in payload.history[-MAX_HISTORY_TURNS:]:
        messages.append({"role": turn.role, "content": turn.content[:MAX_HISTORY_MESSAGE_CHARS]})
    messages.append({"role": "user", "content": payload.question})

    try:
        answer = chat_completion(messages=messages, temperature=0.3, max_tokens=600)
    except GroqError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return ChatResponse(answer=answer, citations=[Citation(**p) for p in passages])
