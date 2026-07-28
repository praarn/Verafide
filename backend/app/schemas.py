import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------

class UserCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Prediction ----------

class PredictRequest(BaseModel):
    text: str = Field(min_length=20, description="Article text or headline to analyze")
    mode: Literal["classic", "advanced"] = "classic"


class PredictURLRequest(BaseModel):
    url: str
    mode: Literal["classic", "advanced"] = "classic"


class SignalWord(BaseModel):
    word: str
    weight: float
    direction: Literal["real", "fake"]


class PredictResponse(BaseModel):
    label: Literal["real", "fake"]
    confidence: float
    probabilities: dict
    mode: str
    signal_words: list[SignalWord]
    source_title: Optional[str] = None
    analyzed_text: str = ""
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


class BatchResultRow(BaseModel):
    text_excerpt: str
    label: str
    confidence: float
    source_ref: Optional[str] = None
    signal_words: list[SignalWord] = []


class BatchResponse(BaseModel):
    results: list[BatchResultRow]
    total: int
    fake_count: int
    real_count: int
    combined_text: str = ""
    extraction_summary: Optional[dict] = None


class AnalyticsSummary(BaseModel):
    total_predictions: int
    fake_count: int
    real_count: int
    fake_ratio: float
    average_confidence: float
    by_day: list[dict]
    by_mode: dict
    model_metrics: dict


# ---------- Summarizer + Chatbot (Groq-powered) ----------

class SummarizeRequest(BaseModel):
    text: str = Field(min_length=20)
    length: Literal["short", "detailed"] = "short"


class SummarizeResponse(BaseModel):
    summary: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    context: str = Field(min_length=20, description="The article/text being discussed")
    question: str = Field(min_length=1)
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    answer: str
