import logging
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import SECRET_FROM_ENV, settings
from app.database import Base, engine
from app.logging_config import configure_logging
from app.middleware import RateLimitMiddleware, RequestContextMiddleware
from app.routers import analytics, assist, auth, batch_jobs, history, predict, rag

configure_logging(settings.LOG_LEVEL)
logger = logging.getLogger("app")


def _ocr_available() -> bool:
    if settings.TESSERACT_CMD:
        return bool(shutil.which(settings.TESSERACT_CMD) or settings.TESSERACT_CMD)
    return shutil.which("tesseract") is not None


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("%s v%s starting (env=%s)", settings.APP_NAME, settings.APP_VERSION, settings.ENV)

    if settings.DB_CREATE_ALL:
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("DB schema ensured via create_all (DB_CREATE_ALL=true).")
        except Exception:
            logger.exception("create_all failed — is the database reachable? (%s)", _safe_db_url())
    else:
        logger.info("DB_CREATE_ALL=false — expecting `alembic upgrade head` to have run.")

    logger.info("Groq: %s", "configured" if settings.GROQ_API_KEY else "NOT configured (local model only)")
    logger.info("Tesseract OCR: %s", "available" if _ocr_available() else "NOT available (scanned PDFs skipped)")

    if not SECRET_FROM_ENV:
        msg = ("SECRET_KEY is a per-process random value — every restart invalidates all "
               "issued JWTs. Set SECRET_KEY in the environment or backend/.env.")
        logger.error(msg) if settings.is_production else logger.warning(msg)
    if settings.is_production and "*" in settings.cors_origins_list:
        logger.error("CORS_ORIGINS contains '*' in production — lock this down.")

    try:
        from app.ml.inference import ModelBundle

        ModelBundle.load()
        logger.info("ML artifacts loaded.")
    except Exception:
        logger.exception("Could not preload ML artifacts — /api/predict will error until fixed.")

    if settings.RAG_ENABLED:
        try:
            from app.rag import rag_status

            logger.info("RAG index: %s", rag_status())
        except Exception:
            logger.exception("RAG index unavailable this run.")

    yield
    logger.info("Shutting down.")


def _safe_db_url() -> str:
    url = settings.DATABASE_URL
    if "@" in url:
        return url.split("@", 1)[0].rsplit(":", 1)[0] + ":***@" + url.split("@", 1)[1]
    return url


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multimodal misinformation analysis — text, URL, image, and audio — with RAG-grounded LLM reasoning.",
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
)

app.include_router(auth.router)
app.include_router(predict.router)
app.include_router(batch_jobs.router)
app.include_router(history.router)
app.include_router(analytics.router)
app.include_router(assist.router)
app.include_router(rag.router)


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": getattr(request.state, "request_id", None)},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def _validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors()[0].get("msg", "Invalid request.") if exc.errors() else "Invalid request.",
            "errors": exc.errors(),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error. If this keeps happening, quote the request id below.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.get("/api/health", tags=["health"])
def health_check():
    from app.ml.inference import ModelBundle
    from app.rag import rag_status

    try:
        models_ready = ModelBundle.load() is not None
    except Exception:
        models_ready = False

    rag = rag_status()
    return {
        "status": "ok" if models_ready else "degraded",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.ENV,
        "models_loaded": models_ready,
        "groq_configured": bool(settings.GROQ_API_KEY),
        "ocr_available": _ocr_available(),
        "rag_ready": rag["ready"],
        "rag_chunks": rag["total_chunks"],
    }
