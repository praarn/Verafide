import datetime
import hashlib
import secrets

import bcrypt
from jose import JWTError, jwt

from app.config import settings

_MAX_PASSWORD_BYTES = 72


def _utcnow() -> datetime.datetime:
    # Naive UTC for JWT `exp` (python-jose encodes it as a timestamp) and
    # for DB datetime comparisons — see app/models.py._utcnow.
    return datetime.datetime.utcnow()


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
    except ValueError:
        return False


# --- Access tokens (short-lived JWT) ----------------------------------

def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    expire = _utcnow() + datetime.timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": _utcnow(),
        "jti": secrets.token_urlsafe(8),  # unique per token even within the same second
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Returns the subject (email) for a valid, non-expired ACCESS token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
    if payload.get("type") not in (None, "access"):
        return None  # refuse a refresh token used as a bearer credential
    return payload.get("sub")


# --- Refresh tokens (opaque random string, hashed at rest) -----------

def generate_refresh_token() -> str:
    """Opaque, not a JWT — it's only ever validated against its stored hash,
    so it carries no forgeable claims."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime.datetime:
    return _utcnow() + datetime.timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
