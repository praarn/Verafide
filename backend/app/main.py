from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import analytics, assist, auth, history, predict

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Detects and classifies fake news articles using classic ML and neural network models.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(predict.router)
app.include_router(history.router)
app.include_router(analytics.router)
app.include_router(assist.router)


@app.get("/api/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": settings.APP_NAME}
