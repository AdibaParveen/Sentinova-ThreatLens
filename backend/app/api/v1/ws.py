from __future__ import annotations

import json
import asyncio
from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import current_user
from app.models import User
from app.security import parse_access
from app.realtime import CHANNEL

router = APIRouter()
settings = get_settings()


@router.websocket("/ws")
async def ws_gateway(ws: WebSocket):
    token = ws.query_params.get("token")
    data = parse_access(token or "")
    if not data:
        await ws.close(code=4401)
        return
    await ws.accept()
    try:
        r = aioredis.from_url(settings.redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(CHANNEL)
        await ws.send_json({"type": "hello", "at": datetime.now(timezone.utc).isoformat()})
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg.get("data"):
                try:
                    payload = json.loads(msg["data"])
                    await ws.send_json(payload)
                except Exception:
                    pass
            try:
                incoming = await asyncio.wait_for(ws.receive_text(), timeout=0.05)
                if incoming == "ping":
                    await ws.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        return
    except Exception:
        try:
            await ws.close()
        except Exception:
            pass
