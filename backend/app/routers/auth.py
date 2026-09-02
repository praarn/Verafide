import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import RefreshToken, User
from app.schemas import LogoutRequest, RefreshRequest, TokenPair, UserCreate, UserLogin, UserOut
from app.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

_ACCESS_TTL_SECONDS = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def _utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow()  # naive UTC — see app/models.py


def _issue_pair(db: Session, user: User, request: Request | None) -> TokenPair:
    raw_refresh = generate_refresh_token()
    row = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh),
        expires_at=refresh_token_expiry(),
        user_agent=(request.headers.get("user-agent", "")[:300] if request else None),
    )
    db.add(row)
    db.commit()
    return TokenPair(
        access_token=create_access_token(subject=user.email),
        refresh_token=raw_refresh,
        expires_in=_ACCESS_TTL_SECONDS,
        user=UserOut.model_validate(user),
    )


def _prune_user_tokens(db: Session, user_id: int, keep: int = 10) -> None:
    """Bound the table: drop expired rows, then trim to the newest `keep`."""
    now = _utcnow()
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id, RefreshToken.expires_at < now
    ).delete()
    live = (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
        .order_by(RefreshToken.created_at.desc())
        .offset(keep)
        .all()
    )
    for tok in live:
        tok.revoked = True
    db.commit()


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_pair(db, user, request)


@router.post("/login", response_model=TokenPair)
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    _prune_user_tokens(db, user.id)
    return _issue_pair(db, user, request)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    """Rotating refresh: the presented token is consumed (revoked) and a new
    pair issued. Re-using an already-revoked token is rejected and, as a
    reuse-detection measure, revokes every other live token for that user."""
    token_hash = hash_refresh_token(payload.refresh_token)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    if row is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")
    if row.revoked:
        logger.warning("refresh-token reuse detected for user_id=%s; revoking all sessions", row.user_id)
        db.query(RefreshToken).filter(
            RefreshToken.user_id == row.user_id, RefreshToken.revoked.is_(False)
        ).update({"revoked": True})
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token already used. Please sign in again.")
    if row.expires_at < _utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired. Please sign in again.")

    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists.")

    row.revoked = True
    db.commit()
    return _issue_pair(db, user, request)


@router.post("/logout", status_code=204)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    row = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == hash_refresh_token(payload.refresh_token))
        .first()
    )
    if row and not row.revoked:
        row.revoked = True
        db.commit()
    return None


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
