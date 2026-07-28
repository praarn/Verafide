import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    predictions = relationship("Prediction", back_populates="owner", cascade="all, delete-orphan")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_type = Column(String, default="text")  # text | url | batch
    source_ref = Column(String, nullable=True)  # e.g. the URL, or batch filename
    input_excerpt = Column(Text, nullable=False)
    label = Column(String, nullable=False)  # fake | real
    confidence = Column(Float, nullable=False)
    mode = Column(String, default="classic")  # classic | advanced
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="predictions")
