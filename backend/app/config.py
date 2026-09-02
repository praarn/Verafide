import os
import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Verafide API"
    APP_VERSION: str = "2.0.0"
    # "development" | "production" — only affects how loudly startup complains
    # about insecure defaults (ephemeral SECRET_KEY, wildcard CORS, etc.).
    ENV: str = os.getenv("ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Whether SECRET_KEY was supplied explicitly (see SECRET_FROM_ENV below).
    # A random per-process fallback means every restart invalidates all
    # issued JWTs. Startup logs a warning (error in production).
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    # Short-lived access token; the refresh token (below) is the long-lived
    # credential and is rotated + revocable via the refresh_tokens table.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))

    # PostgreSQL by default. Tests point this at SQLite (see tests/conftest.py).
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://verafide:verafide@localhost:5432/verafide"
    )
    # Run Base.metadata.create_all() on startup. Convenient for local dev;
    # in Docker/CI the entrypoint runs `alembic upgrade head` instead and
    # this should be false so the two don't fight.
    DB_CREATE_ALL: bool = os.getenv("DB_CREATE_ALL", "true").lower() == "true"

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    MAX_BATCH_ROWS: int = 200

    # Hard ceiling on a single text/URL analysis payload (schemas + scraper).
    MAX_TEXT_CHARS: int = int(os.getenv("MAX_TEXT_CHARS", "60000"))
    # Upload ceilings for the multimodal endpoints.
    MAX_IMAGE_MB: float = float(os.getenv("MAX_IMAGE_MB", "8"))
    MAX_AUDIO_MB: float = float(os.getenv("MAX_AUDIO_MB", "25"))

    # --- Rate limiting (in-memory sliding window, per client) -------------
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    RATE_LIMIT_HEAVY_REQUESTS: int = int(os.getenv("RATE_LIMIT_HEAVY_REQUESTS", "20"))

    # --- Groq (OpenAI-compatible) ---------------------------------------
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    # Reasoning model for the LLM verdict + summarizer + chatbot. Groq
    # rotates its hosted model catalogue; check https://console.groq.com/docs/models
    # and set GROQ_MODEL in .env if this one is retired.
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    # Vision model for image analysis. Only used if the account has vision
    # access; analyze_image() falls back to local Tesseract OCR otherwise.
    GROQ_VISION_MODEL: str = os.getenv(
        "GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"
    )
    # Speech-to-text for the audio modality.
    GROQ_WHISPER_MODEL: str = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
    GROQ_MAX_CONTEXT_CHARS: int = int(os.getenv("GROQ_MAX_CONTEXT_CHARS", "28000"))

    # --- RAG -----------------------------------------------------------
    RAG_ENABLED: bool = os.getenv("RAG_ENABLED", "true").lower() == "true"
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "4"))
    # Minimum cosine similarity for a retrieved chunk to be used as context.
    RAG_MIN_SCORE: float = float(os.getenv("RAG_MIN_SCORE", "0.08"))

    # Optional: explicit path to the Tesseract OCR binary (Windows).
    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENV.strip().lower() in ("production", "prod")

    class Config:
        env_file = ".env"
        extra = "ignore"


def _secret_key_was_supplied() -> bool:
    """True if SECRET_KEY was set explicitly (real env var or a line in
    backend/.env), False if we fell back to a per-process random value."""
    if "SECRET_KEY" in os.environ:
        return True
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    try:
        with open(env_path, encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped.startswith("SECRET_KEY") and "=" in stripped:
                    return bool(stripped.split("=", 1)[1].strip())
    except OSError:
        pass
    return False


settings = Settings()

# Computed once at import; consumed by the startup diagnostics in app/main.py.
SECRET_FROM_ENV: bool = _secret_key_was_supplied()
