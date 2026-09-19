from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.config import get_settings
from app.db import get_db
from app.deps import client_ip, correlation_id, current_user
from app.emailer import reset_email, verification_email
from app.models import EmailToken, User, UserPreference, UserSession
from app.rbac import PRIVILEGED_ROLES, navigation_for
from app.security import (
    PASSWORD_RULES,
    access_token,
    hash_token,
    password_errors,
    hash_password,
    random_token,
    refresh_token,
    totp_uri,
    verify_password,
    verify_totp,
    decode_token,
)
from app.config import get_settings as gs
import pyotp

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str
    confirm_password: str
    organization: str = ""
    job_title: str = ""


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False
    totp: str | None = None


class ResetRequest(BaseModel):
    email: EmailStr


class ResetConfirm(BaseModel):
    token: str
    password: str
    confirm_password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


def _lock_message(user: User) -> None:
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=423, detail={"error_code": "LOCKED", "message": "Account temporarily locked after repeated failed sign-ins. Try again later."})


@router.get("/password-rules")
def password_rules():
    return {"rules": PASSWORD_RULES}


@router.post("/register")
def register(payload: RegisterIn, request: Request, db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    if payload.password != payload.confirm_password:
        raise HTTPException(400, detail={"error_code": "PASSWORD_MISMATCH", "message": "Passwords do not match"})
    errs = password_errors(payload.password)
    if errs:
        raise HTTPException(400, detail={"error_code": "WEAK_PASSWORD", "message": "; ".join(errs)})
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(409, detail={"error_code": "EMAIL_EXISTS", "message": "An account with this email already exists"})
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        organization=payload.organization,
        job_title=payload.job_title,
        role="soc_analyst",
        status="pending",
        email_verified=False,
        is_demo=False,
    )
    db.add(user)
    db.flush()
    db.add(UserPreference(user_id=user.id, notifications={"critical_alerts": True, "high_severity": True, "email": True, "in_app": True}))
    raw = random_token()
    db.add(
        EmailToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            purpose="verify",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
    )
    write_audit(db, action="USER_REGISTER", user=user, resource="user", resource_id=str(user.id), ip=client_ip(request), correlation_id=cid)
    db.commit()
    link = f"{settings.app_url}/verify-email?token={raw}"
    try:
        verification_email(user.email, user.full_name, link)
    except Exception:
        if settings.demo_mode:
            # Mailhog/SMTP optional in local demos
            pass
        else:
            raise
    return {"status": "verification_sent", "message": "Check your email to verify your account."}


@router.post("/verify-email")
def verify_email(token: str, request: Request, db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    rec = db.query(EmailToken).filter(EmailToken.token_hash == hash_token(token), EmailToken.purpose == "verify").first()
    if not rec:
        raise HTTPException(400, detail={"error_code": "INVALID_TOKEN", "message": "Verification link is invalid"})
    if rec.used_at:
        return {"status": "already_verified"}
    if rec.expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, detail={"error_code": "EXPIRED", "message": "Verification link expired"})
    user = db.get(User, rec.user_id)
    user.email_verified = True
    user.status = "active"
    rec.used_at = datetime.now(timezone.utc)
    write_audit(db, action="EMAIL_VERIFIED", user=user, resource="user", resource_id=str(user.id), ip=client_ip(request), correlation_id=cid)
    db.commit()
    return {"status": "verified"}


@router.post("/resend-verification")
def resend(payload: ResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    # Always generic
    if user and not user.email_verified:
        raw = random_token()
        db.add(EmailToken(user_id=user.id, token_hash=hash_token(raw), purpose="verify", expires_at=datetime.now(timezone.utc) + timedelta(hours=24)))
        db.commit()
        try:
            verification_email(user.email, user.full_name, f"{settings.app_url}/verify-email?token={raw}")
        except Exception:
            pass
    return {"status": "ok", "message": "If the account needs verification, a new email has been sent."}


@router.post("/login")
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    ip = client_ip(request)
    if not user:
        write_audit(db, action="LOGIN_FAILURE", resource="auth", ip=ip, correlation_id=cid, result="FAILURE", metadata={"reason": "unknown_user"})
        db.commit()
        raise HTTPException(401, detail={"error_code": "INVALID_CREDENTIALS", "message": "Invalid email or password"})
    _lock_message(user)
    if not verify_password(payload.password, user.password_hash):
        user.failed_logins += 1
        if user.failed_logins >= 5:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=min(30, 2 ** (user.failed_logins - 5)))
            user.status = "locked" if user.failed_logins >= 8 else user.status
        write_audit(db, action="LOGIN_FAILURE", user=user, resource="auth", ip=ip, correlation_id=cid, result="FAILURE")
        db.commit()
        raise HTTPException(401, detail={"error_code": "INVALID_CREDENTIALS", "message": "Invalid email or password"})
    if not user.email_verified:
        raise HTTPException(403, detail={"error_code": "EMAIL_UNVERIFIED", "message": "Verify your email before signing in"})
    if user.status not in {"active", "locked"}:
        raise HTTPException(403, detail={"error_code": "INACTIVE", "message": "Account is not active"})
    if user.status == "locked":
        _lock_message(user)
    if user.mfa_enabled:
        if not payload.totp:
            return {"mfa_required": True}
        if not user.mfa_secret or not verify_totp(user.mfa_secret, payload.totp):
            raise HTTPException(401, detail={"error_code": "MFA_INVALID", "message": "Invalid authenticator code"})
    user.failed_logins = 0
    user.locked_until = None
    user.status = "active"
    user.last_login_at = datetime.now(timezone.utc)
    days = 30 if payload.remember_me else settings.jwt_refresh_days
    raw_refresh = refresh_token(str(user.id))
    decoded = decode_token(raw_refresh, settings.jwt_refresh_secret)
    session = UserSession(
        user_id=user.id,
        refresh_jti=decoded["jti"],
        user_agent=request.headers.get("user-agent", "")[:512],
        ip_address=ip,
        expires_at=datetime.now(timezone.utc) + timedelta(days=days),
    )
    db.add(session)
    write_audit(db, action="LOGIN_SUCCESS", user=user, resource="auth", ip=ip, correlation_id=cid)
    db.commit()
    return {
        "access_token": access_token(str(user.id), user.role),
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_minutes * 60,
        "user": serialize_user(user),
        "navigation": navigation_for(user.role),
    }


class RefreshIn(BaseModel):
    refresh_token: str


@router.post("/refresh")
def refresh(payload: RefreshIn, db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token, settings.jwt_refresh_secret)
    except Exception:
        raise HTTPException(401, detail={"error_code": "INVALID_REFRESH", "message": "Session expired"})
    sess = db.query(UserSession).filter(UserSession.refresh_jti == data["jti"], UserSession.revoked_at.is_(None)).first()
    if not sess or sess.expires_at < datetime.now(timezone.utc):
        raise HTTPException(401, detail={"error_code": "INVALID_REFRESH", "message": "Session expired"})
    user = db.get(User, sess.user_id)
    return {"access_token": access_token(str(user.id), user.role), "expires_in": settings.jwt_access_minutes * 60}


@router.post("/logout")
def logout(payload: RefreshIn, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user), cid: str = Depends(correlation_id)):
    try:
        data = decode_token(payload.refresh_token, settings.jwt_refresh_secret)
        sess = db.query(UserSession).filter(UserSession.refresh_jti == data["jti"]).first()
        if sess:
            sess.revoked_at = datetime.now(timezone.utc)
    except Exception:
        pass
    write_audit(db, action="LOGOUT", user=user, resource="auth", ip=client_ip(request), correlation_id=cid)
    db.commit()
    return {"status": "ok"}


@router.post("/forgot-password")
def forgot(payload: ResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user:
        raw = random_token()
        db.add(EmailToken(user_id=user.id, token_hash=hash_token(raw), purpose="reset", expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
        db.commit()
        try:
            reset_email(user.email, user.full_name, f"{settings.app_url}/reset-password?token={raw}")
        except Exception:
            pass
    return {"status": "ok", "message": "If an account exists for that email, a reset link has been sent."}


@router.post("/reset-password")
def reset(payload: ResetConfirm, request: Request, db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    if payload.password != payload.confirm_password:
        raise HTTPException(400, detail={"error_code": "PASSWORD_MISMATCH", "message": "Passwords do not match"})
    errs = password_errors(payload.password)
    if errs:
        raise HTTPException(400, detail={"error_code": "WEAK_PASSWORD", "message": "; ".join(errs)})
    rec = db.query(EmailToken).filter(EmailToken.token_hash == hash_token(payload.token), EmailToken.purpose == "reset").first()
    if not rec or rec.used_at or rec.expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, detail={"error_code": "INVALID_TOKEN", "message": "Reset link is invalid or expired"})
    user = db.get(User, rec.user_id)
    user.password_hash = hash_password(payload.password)
    rec.used_at = datetime.now(timezone.utc)
    for s in db.query(UserSession).filter(UserSession.user_id == user.id, UserSession.revoked_at.is_(None)):
        s.revoked_at = datetime.now(timezone.utc)
    write_audit(db, action="PASSWORD_RESET", user=user, resource="user", resource_id=str(user.id), ip=client_ip(request), correlation_id=cid)
    db.commit()
    return {"status": "reset"}


@router.post("/mfa/setup")
def mfa_setup(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role not in PRIVILEGED_ROLES and user.role != "administrator":
        # still allow optional MFA for any user
        pass
    secret = pyotp.random_base32()
    user.mfa_secret = secret
    db.commit()
    return {"secret": secret, "otpauth_url": totp_uri(user.email, secret)}


class MfaConfirm(BaseModel):
    code: str


@router.post("/mfa/enable")
def mfa_enable(payload: MfaConfirm, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    if not user.mfa_secret or not verify_totp(user.mfa_secret, payload.code):
        raise HTTPException(400, detail={"error_code": "MFA_INVALID", "message": "Invalid authenticator code"})
    user.mfa_enabled = True
    write_audit(db, action="MFA_ENABLED", user=user, resource="user", resource_id=str(user.id), ip=client_ip(request), correlation_id=cid)
    db.commit()
    return {"mfa_enabled": True}


@router.post("/mfa/disable")
def mfa_disable(payload: MfaConfirm, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    if not user.mfa_secret or not verify_totp(user.mfa_secret, payload.code):
        raise HTTPException(400, detail={"error_code": "MFA_INVALID", "message": "Invalid authenticator code"})
    user.mfa_enabled = False
    user.mfa_secret = None
    write_audit(db, action="MFA_DISABLED", user=user, resource="user", resource_id=str(user.id), ip=client_ip(request), correlation_id=cid)
    db.commit()
    return {"mfa_enabled": False}


def serialize_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "organization": user.organization,
        "job_title": user.job_title,
        "role": user.role,
        "status": user.status,
        "email_verified": user.email_verified,
        "mfa_enabled": user.mfa_enabled,
        "profile_picture": user.profile_picture,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "is_demo": user.is_demo,
    }
