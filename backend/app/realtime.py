from __future__ import annotations

import json

import redis

from app.config import get_settings

settings = get_settings()
CHANNEL = "threatlens.events"


def publish(event_type: str, payload: dict) -> None:
    try:
        r = redis.from_url(settings.redis_url)
        r.publish(CHANNEL, json.dumps({"type": event_type, "payload": payload}))
    except Exception:
        pass
