from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db, engine
from app.deps import require
from app.models import Feed, User

router = APIRouter(tags=["health"])
settings = get_settings()


def _ping_redis() -> str:
    try:
        import redis

        r = redis.from_url(settings.redis_url)
        r.ping()
        return "ok"
    except Exception:
        return "down"


def _ping_search() -> str:
    try:
        import httpx

        r = httpx.get(settings.elasticsearch_url, timeout=2.0)
        return "ok" if r.status_code < 500 else "degraded"
    except Exception:
        return "down"


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"
    return {
        "api": "ok",
        "database": db_status,
        "redis": _ping_redis(),
        "search": _ping_search(),
        "websocket": "ok",
        "version": settings.threatlens_version,
        "environment": settings.app_env,
        "time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/detailed")
def health_detailed(user: User = Depends(require("health.view")), db: Session = Depends(get_db)):
    base = health(db)
    feeds = db.query(Feed).all()
    base["feeds"] = [{"name": f.name, "status": f.status, "last_poll_at": f.last_poll_at.isoformat() if f.last_poll_at else None} for f in feeds]
    base["worker"] = "ok"
    base["scheduler"] = "ok"
    return base
