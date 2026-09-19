from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1 import auth, health, intel, me, ws
from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.seed import seed

settings = get_settings()


class SecurityHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cid = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        request.state.correlation_id = cid
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'"
        if settings.cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title="ThreatLens API",
        version=settings.threatlens_version,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(SecurityHeaders)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        cid = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=500,
            content={"error_code": "INTERNAL", "message": "An unexpected error occurred", "correlation_id": cid},
        )

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(me.router, prefix="/api/v1")
    app.include_router(intel.router, prefix="/api/v1")
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(ws.router, prefix="/api/v1")

    @app.on_event("startup")
    def _startup():
        Base.metadata.create_all(bind=engine)
        if settings.seed_on_start:
            db = SessionLocal()
            try:
                seed(db)
            finally:
                db.close()

    return app


app = create_app()
