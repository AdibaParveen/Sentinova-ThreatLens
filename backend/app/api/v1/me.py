from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.api.v1.auth import serialize_user
from app.db import get_db
from app.deps import client_ip, correlation_id, current_user, require
from app.models import ApiKey, AuditLog, Notification, User, UserPreference, UserSession, Webhook
from app.rbac import navigation_for
from app.security import hash_password, hash_token, password_errors, random_token, verify_password

router = APIRouter(tags=["me"])


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    prefs = db.get(UserPreference, user.id)
    return {
        "user": serialize_user(user),
        "preferences": None
        if not prefs
        else {
            "theme": prefs.theme,
            "density": prefs.density,
            "default_dashboard": prefs.default_dashboard,
            "refresh_interval": prefs.refresh_interval,
            "visible_widgets": prefs.visible_widgets,
            "saved_layouts": prefs.saved_layouts,
            "default_filters": prefs.default_filters,
            "notifications": prefs.notifications,
        },
        "navigation": navigation_for(user.role),
    }


class ProfileIn(BaseModel):
    full_name: str | None = None
    job_title: str | None = None
    organization: str | None = None
    profile_picture: str | None = None


@router.patch("/me")
def update_me(payload: ProfileIn, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    if payload.full_name:
        user.full_name = payload.full_name
    if payload.job_title is not None:
        user.job_title = payload.job_title
    if payload.organization is not None:
        user.organization = payload.organization
    if payload.profile_picture is not None:
        user.profile_picture = payload.profile_picture
    write_audit(db, action="PROFILE_UPDATE", user=user, resource="user", resource_id=str(user.id), ip=client_ip(request), correlation_id=cid)
    db.commit()
    return serialize_user(user)


class PrefsIn(BaseModel):
    theme: str | None = None
    density: str | None = None
    default_dashboard: str | None = None
    refresh_interval: int | None = None
    visible_widgets: dict | None = None
    saved_layouts: dict | None = None
    default_filters: dict | None = None
    notifications: dict | None = None


@router.patch("/me/preferences")
def update_prefs(payload: PrefsIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    prefs = db.get(UserPreference, user.id)
    if not prefs:
        prefs = UserPreference(user_id=user.id)
        db.add(prefs)
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(prefs, k, v)
    db.commit()
    return {"status": "ok"}


class PasswordIn(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


@router.post("/me/password")
def change_password(payload: PasswordIn, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(400, detail={"error_code": "PASSWORD_MISMATCH", "message": "Passwords do not match"})
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(400, detail={"error_code": "INVALID_PASSWORD", "message": "Current password is incorrect"})
    errs = password_errors(payload.new_password)
    if errs:
        raise HTTPException(400, detail={"error_code": "WEAK_PASSWORD", "message": "; ".join(errs)})
    user.password_hash = hash_password(payload.new_password)
    write_audit(db, action="PASSWORD_CHANGE", user=user, resource="user", resource_id=str(user.id), ip=client_ip(request), correlation_id=cid)
    db.commit()
    return {"status": "ok"}


@router.get("/me/sessions")
def sessions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(UserSession).filter(UserSession.user_id == user.id).order_by(UserSession.created_at.desc()).all()
    return [
        {
            "id": str(s.id),
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "created_at": s.created_at.isoformat(),
            "last_seen_at": s.last_seen_at.isoformat() if s.last_seen_at else None,
            "revoked": bool(s.revoked_at),
        }
        for s in rows
    ]


@router.post("/me/sessions/revoke-others")
def revoke_others(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    now = datetime.now(timezone.utc)
    for s in db.query(UserSession).filter(UserSession.user_id == user.id, UserSession.revoked_at.is_(None)):
        s.revoked_at = now
    write_audit(db, action="SESSIONS_REVOKE_OTHERS", user=user, resource="session", ip=client_ip(request), correlation_id=cid)
    db.commit()
    return {"status": "ok"}


@router.get("/me/activity")
def activity(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(AuditLog).filter(AuditLog.user_id == user.id).order_by(AuditLog.timestamp.desc()).limit(50).all()
    return [_audit(r) for r in rows]


@router.get("/me/export")
def export_me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    prefs = db.get(UserPreference, user.id)
    return {
        "profile": serialize_user(user),
        "preferences": prefs.notifications if prefs else {},
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(50).all()
    unread = db.query(Notification).filter(Notification.user_id == user.id, Notification.read.is_(False)).count()
    return {
        "unread": unread,
        "items": [
            {
                "id": str(n.id),
                "type": n.ntype,
                "title": n.title,
                "body": n.body,
                "read": n.read,
                "created_at": n.created_at.isoformat(),
                "link": n.link,
            }
            for n in rows
        ],
    }


@router.post("/notifications/{nid}/read")
def read_note(nid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, nid)
    if n and n.user_id == user.id:
        n.read = True
        db.commit()
    return {"status": "ok"}


@router.post("/api-keys")
def create_key(request: Request, user: User = Depends(require("integrations.manage")), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    raw = "tl_" + random_token(24)
    rec = ApiKey(user_id=user.id, name="Integration key", prefix=raw[:10], key_hash=hash_token(raw))
    db.add(rec)
    write_audit(db, action="API_KEY_CREATE", user=user, resource="api_key", resource_id=str(rec.id), ip=client_ip(request), correlation_id=cid)
    db.commit()
    return {"id": str(rec.id), "prefix": rec.prefix, "secret": raw, "warning": "This secret is shown once"}


@router.get("/api-keys")
def list_keys(user: User = Depends(require("integrations.manage")), db: Session = Depends(get_db)):
    rows = db.query(ApiKey).filter(ApiKey.user_id == user.id).all()
    return [{"id": str(k.id), "name": k.name, "prefix": k.prefix, "created_at": k.created_at.isoformat(), "revoked": bool(k.revoked_at)} for k in rows]


def _audit(r: AuditLog) -> dict:
    return {
        "id": str(r.id),
        "timestamp": r.timestamp.isoformat(),
        "user": r.user_name,
        "role": r.role,
        "action": r.action,
        "resource": r.resource,
        "resource_id": r.resource_id,
        "ip_address": r.ip_address,
        "correlation_id": r.correlation_id,
        "result": r.result,
        "metadata": r.metadata_json,
    }
