from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pyotp
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()

PASSWORD_RULES = [
    "At least 12 characters",
    "At least one uppercase letter",
    "At least one lowercase letter",
    "At least one number",
    "At least one symbol",
]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def password_errors(password: str) -> list[str]:
    errors = []
    if len(password) < 12:
        errors.append("Password must be at least 12 characters")
    if not any(c.isupper() for c in password):
        errors.append("Password must include an uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("Password must include a lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("Password must include a number")
    if not any(not c.isalnum() for c in password):
        errors.append("Password must include a symbol")
    return errors


def create_token(subject: str, secret: str, minutes: int | None = None, days: int | None = None, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    if days is not None:
        exp = now + timedelta(days=days)
    else:
        exp = now + timedelta(minutes=minutes or 15)
    payload: dict[str, Any] = {"sub": subject, "iat": int(now.timestamp()), "exp": int(exp.timestamp()), "jti": secrets.token_hex(16)}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> dict[str, Any]:
    return jwt.decode(token, secret, algorithms=["HS256"])


def access_token(user_id: str, role: str) -> str:
    return create_token(user_id, settings.jwt_secret, minutes=settings.jwt_access_minutes, extra={"role": role, "typ": "access"})


def refresh_token(user_id: str, jti: str | None = None) -> str:
    extra = {"typ": "refresh"}
    if jti:
        extra["jti"] = jti
    return create_token(user_id, settings.jwt_refresh_secret, days=settings.jwt_refresh_days, extra=extra)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def random_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def totp_uri(email: str, secret: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="ThreatLens")


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def parse_access(token: str) -> Optional[dict[str, Any]]:
    try:
        data = decode_token(token, settings.jwt_secret)
        if data.get("typ") != "access":
            return None
        return data
    except JWTError:
        return None
