from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.rbac import has_permission
from app.security import parse_access

bearer = HTTPBearer(auto_error=False)


def correlation_id(x_correlation_id: Annotated[Optional[str], Header()] = None) -> str:
    return x_correlation_id or str(uuid.uuid4())


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def current_user(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer)],
    db: Session = Depends(get_db),
) -> User:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error_code": "UNAUTHENTICATED", "message": "Sign in required"})
    data = parse_access(creds.credentials)
    if not data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error_code": "TOKEN_EXPIRED", "message": "Session expired"})
    user = db.get(User, uuid.UUID(data["sub"]))
    if not user or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error_code": "ACCOUNT_INACTIVE", "message": "Account is not active"})
    return user


def require(permission: str):
    def checker(user: User = Depends(current_user)) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error_code": "FORBIDDEN", "message": "Insufficient permissions"})
        return user

    return checker
