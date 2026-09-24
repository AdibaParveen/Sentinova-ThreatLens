from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1 import auth, health, intel, me, ws
from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.rate_limit import limiter
from app.seed import seed

settings = get_settings()


def build_csp() -> str:
    """
    Build a restrictive CSP for API responses.

    The frontend has its own CSP in next.config.ts. This backend CSP
    provides defense-in-depth for API/document responses.
    """
    origins = [
        origin.strip().rstrip("/")
        for origin in settings.cors_origins.split(",")
        if origin.strip()
    ]

    connect_sources = ["'self'"]

    for origin in origins:
        connect_sources.append(origin)

        if origin.startswith("https://"):
            connect_sources.append(origin.replace("https://", "wss://", 1))
        elif origin.startswith("http://"):
            connect_sources.append(origin.replace("http://", "ws://", 1))

    return (
        "default-src 'self'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "form-action 'self'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        f"connect-src {' '.join(connect_sources)}"
    )


class SecurityHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = (
            request.headers.get("x-correlation-id")
            or str(uuid.uuid4())
        )

        request.state.correlation_id = correlation_id

        response = await call_next(request)

        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Content-Security-Policy"] = build_csp()

        # Only send HSTS when HTTPS is actually being used.
        if settings.cookie_secure:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title="ThreatLens API",
        version=settings.threatlens_version,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.state.limiter = limiter

    app.add_exception_handler(
        RateLimitExceeded,
        lambda request, exc: JSONResponse(
            status_code=429,
            content={
                "error_code": "RATE_LIMITED",
                "message": "Too many requests. Wait and retry.",
            },
        ),
    )

    origins = [
        origin.strip()
        for origin in settings.cors_origins.split(",")
        if origin.strip()
    ]

    app.add_middleware(SecurityHeaders)
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Correlation-ID",
        ],
    )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        correlation_id = getattr(
            request.state,
            "correlation_id",
            str(uuid.uuid4()),
        )

        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL",
                "message": "An unexpected error occurred",
                "correlation_id": correlation_id,
            },
        )

    # API routers
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