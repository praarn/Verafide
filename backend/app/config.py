import os
import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Fake News Detection API"
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    MAX_BATCH_ROWS: int = 200

    # Groq (OpenAI-compatible) API for the summarizer + chatbot features.
    # Get a free key at https://console.groq.com/keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    # Groq's free/on-demand tier caps requests at 12,000 tokens/minute — a
    # single oversized request gets rejected outright (HTTP 413), not
    # truncated. ~28,000 characters (~7,000 tokens) leaves headroom for the
    # system prompt, conversation history, and the response itself. This is
    # the SINGLE place this number is defined — both the batch document
    # builder (predict.py) and the summarize/chat endpoints (assist.py)
    # read it from here, so they can't drift out of sync with each other
    # again. If you're on a paid Groq tier with a higher TPM limit, raise
    # this via the env var.
    GROQ_MAX_CONTEXT_CHARS: int = int(os.getenv("GROQ_MAX_CONTEXT_CHARS", "28000"))

    # Optional: explicit path to the Tesseract OCR binary (needed on Windows
    # if it's not on PATH). Leave empty to use whatever's on PATH.
    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
