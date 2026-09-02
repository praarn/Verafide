import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow() -> datetime.datetime:
    # Naive UTC — matches how SQLAlchemy's DateTime column round-trips on
    # both SQLite and (tz-naive) PostgreSQL, so comparisons never hit the
    # "can't compare offset-naive and offset-aware" TypeError.
    return datetime.datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), unique=True, index=True, nullable=False)
    full_name = Column(String(200), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    predictions = relationship("Prediction", back_populates="owner", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # text | url | batch | image | audio
    source_type = Column(String(20), default="text")
    source_ref = Column(String(2048), nullable=True)  # URL, batch filename, or upload name
    input_excerpt = Column(Text, nullable=False)
    label = Column(String(10), nullable=False)  # fake | real
    confidence = Column(Float, nullable=False)
    mode = Column(String(20), default="classic")  # classic | advanced
    created_at = Column(DateTime, default=_utcnow, index=True)

    owner = relationship("User", back_populates="predictions")


class RefreshToken(Base):
    """One row per issued refresh token. We store only a SHA-256 hash of the
    token, never the token itself. Rotation: on /auth/refresh the presented
    token's row is marked revoked and a fresh one is issued, so a stolen
    refresh token is usable at most until the legitimate client refreshes
    (which then invalidates the thief's copy and can be detected)."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    user_agent = Column(String(300), nullable=True)

    user = relationship("User", back_populates="refresh_tokens")
