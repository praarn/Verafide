from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.deps import get_current_user
from app.models import User
from app.schemas import ChatRequest, ChatResponse, SummarizeRequest, SummarizeResponse
from app.services.groq_client import GroqError, chat_completion

router = APIRouter(prefix="/api/assist", tags=["assist"])

# History retention for chat: each prior turn adds to the token count on
# every subsequent request, so a long conversation about a large document
# could creep back toward Groq's rate limit even with the context itself
# capped. Keeping only the last few turns, each trimmed to a reasonable
# length, bounds that growth.
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
    "Answer the user's questions using ONLY the article/text provided as context below. "
    "If the answer isn't contained in the text, say so honestly rather than guessing or "
    "using outside knowledge. Be concise and factual, and avoid stating a definitive "
    "real/fake verdict yourself — that's a separate model's job; you're here to help the "
    "user understand the content itself."
)


@router.post("/summarize", response_model=SummarizeResponse)
def summarize(payload: SummarizeRequest, user: User = Depends(get_current_user)):
    text = payload.text[:settings.GROQ_MAX_CONTEXT_CHARS]
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
    context = payload.context[:settings.GROQ_MAX_CONTEXT_CHARS]
    messages = [
        {"role": "system", "content": f"{CHAT_SYSTEM_PROMPT}\n\nARTICLE/TEXT:\n{context}"},
    ]
    # Replay prior turns so the model has conversational memory (the API
    # itself is stateless) — trimmed so a long conversation can't slowly
    # creep the request back over the rate limit.
    for turn in payload.history[-MAX_HISTORY_TURNS:]:
        messages.append({"role": turn.role, "content": turn.content[:MAX_HISTORY_MESSAGE_CHARS]})
    messages.append({"role": "user", "content": payload.question})

    try:
        answer = chat_completion(messages=messages, temperature=0.3, max_tokens=600)
    except GroqError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return ChatResponse(answer=answer)
