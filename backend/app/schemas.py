import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

from app.config import settings

_MAX_TEXT = settings.MAX_TEXT_CHARS


# ---------- Auth ----------

class UserCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = Field(default=None, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # access-token lifetime in seconds
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=512)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=512)


# ---------- Shared verdict pieces ----------

class SignalWord(BaseModel):
    word: str
    weight: float
    direction: Literal["real", "fake"]


class SourceCredibility(BaseModel):
    domain: str
    tier: Literal["high", "mixed", "low", "satire", "state"]
    label: str
    blurb: str


class Citation(BaseModel):
    """A retrieved RAG passage used to ground the verdict / answer."""
    id: str
    title: str
    source: str
    snippet: str
    score: float


# ---------- Prediction ----------

class PredictRequest(BaseModel):
    text: str = Field(min_length=20, max_length=_MAX_TEXT, description="Article text or headline")
    mode: Literal["classic", "advanced"] = "classic"


class PredictURLRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    mode: Literal["classic", "advanced"] = "classic"


class PredictResponse(BaseModel):
    label: Literal["real", "fake"]
    confidence: float
    confidence_band: Literal["high", "moderate", "low"] = "moderate"
    probabilities: dict
    mode: str
    modality: Literal["text", "url", "image", "audio", "batch"] = "text"
    signal_words: list[SignalWord]
    source_title: Optional[str] = None
    source_credibility: Optional[SourceCredibility] = None
    citations: list[Citation] = []
    analyzed_text: str = ""
    # For image/audio: what the vision model saw / what was transcribed.
    extracted_text: Optional[str] = None
    transcript: Optional[str] = None
    media_observations: Optional[str] = None
    verdict_source: Literal["llm", "classic_fallback"] = "classic_fallback"
    llm_reasoning: Optional[str] = None


class PredictionOut(BaseModel):
    id: int
    source_type: str
    source_ref: Optional[str]
    input_excerpt: str
    label: str
    confidence: float
    mode: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# ---------- Batch ----------

class BatchResultRow(BaseModel):
    text_excerpt: str
    label: str
    confidence: float
    confidence_band: Literal["high", "moderate", "low"] = "moderate"
    source_ref: Optional[str] = None
    signal_words: list[SignalWord] = []


class BatchResponse(BaseModel):
    results: list[BatchResultRow]
    total: int
    fake_count: int
    real_count: int
    combined_text: str = ""
    extraction_summary: Optional[dict] = None


class BatchJobStatus(BaseModel):
    job_id: str
    state: Literal["pending", "running", "complete", "error"]
    processed: int
    total: int
    error: Optional[str] = None
    result: Optional[BatchResponse] = None


# ---------- Analytics ----------

class AnalyticsSummary(BaseModel):
    total_predictions: int
    fake_count: int
    real_count: int
    fake_ratio: float
    average_confidence: float
    by_day: list[dict]
    by_mode: dict
    by_modality: dict
    model_metrics: dict


# ---------- Summarizer + Chatbot ----------

class SummarizeRequest(BaseModel):
    text: str = Field(min_length=20, max_length=_MAX_TEXT)
    length: Literal["short", "detailed"] = "short"


class SummarizeResponse(BaseModel):
    summary: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class ChatRequest(BaseModel):
    context: str = Field(min_length=20, max_length=_MAX_TEXT, description="The text being discussed")
    question: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default=[], max_length=40)
    use_rag: bool = True


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = []


# ---------- RAG ----------

class RagSearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    k: int = Field(default=5, ge=1, le=20)


class RagSearchResponse(BaseModel):
    results: list[Citation]


class RagStatus(BaseModel):
    enabled: bool
    ready: bool
    total_chunks: int
    media_literacy_docs: int
    fact_check_entries: int
    built_at: Optional[str] = None
