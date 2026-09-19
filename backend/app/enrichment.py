from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
import redis

from app.config import get_settings
from app.models import Enrichment, Indicator, IndicatorSource
from app.scoring import compute_severity

settings = get_settings()
_redis = None


def redis_client():
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _cache_get(key: str):
    try:
        import json

        raw = redis_client().get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _cache_set(key: str, value: dict, ttl: int = 3600):
    try:
        import json

        redis_client().setex(key, ttl, json.dumps(value))
    except Exception:
        pass


def geo_for_ip(ip: str) -> dict[str, Any]:
    cached = _cache_get(f"geo:{ip}")
    if cached:
        return cached
    # Offline-safe demo mapping plus optional live lookup
    demo = {
        "185.220.101.47": {"country": "DE", "city": "Frankfurt", "isp": "Zwiebelfreunde e.V.", "asn": "AS60729", "org": "Tor exit", "lat": 50.11, "lon": 8.68},
        "45.155.205.233": {"country": "RU", "city": "Moscow", "isp": "Selectel", "asn": "AS49505", "org": "Bulletproof hosting", "lat": 55.75, "lon": 37.62},
        "91.219.237.244": {"country": "NL", "city": "Amsterdam", "isp": "Serverius", "asn": "AS50673", "org": "Hosting", "lat": 52.37, "lon": 4.89},
        "103.27.124.82": {"country": "SG", "city": "Singapore", "isp": "Leaseweb", "asn": "AS133752", "org": "Cloud", "lat": 1.35, "lon": 103.82},
        "8.8.8.8": {"country": "US", "city": "Mountain View", "isp": "Google", "asn": "AS15169", "org": "Google LLC", "lat": 37.39, "lon": -122.08},
    }
    data = demo.get(ip, {"country": "US", "city": "Ashburn", "isp": "Unknown", "asn": "AS0", "org": "Unregistered", "lat": 39.04, "lon": -77.49})
    try:
        with httpx.Client(timeout=3.0) as client:
            r = client.get(f"https://ipapi.co/{ip}/json/")
            if r.status_code == 200:
                j = r.json()
                if not j.get("error"):
                    data = {
                        "country": j.get("country_code") or data["country"],
                        "city": j.get("city") or data["city"],
                        "isp": j.get("org") or data["isp"],
                        "asn": j.get("asn") or data["asn"],
                        "org": j.get("org") or data["org"],
                        "lat": j.get("latitude") or data["lat"],
                        "lon": j.get("longitude") or data["lon"],
                    }
    except Exception:
        pass
    _cache_set(f"geo:{ip}", data, 86400)
    return data


def enrich_indicator(indicator: Indicator, db) -> dict[str, Any]:
    sources = list(indicator.sources)
    malicious = sum(1 for s in sources if s.verdict == "malicious")
    suspicious = sum(1 for s in sources if s.verdict == "suspicious")
    total = max(len(sources), 1)
    abuse = int(round(100 * (malicious + 0.5 * suspicious) / total))
    payload: dict[str, Any] = {
        "malicious_sources": malicious,
        "suspicious_sources": suspicious,
        "total_sources": total,
        "abuse_confidence": abuse,
        "verdict": "malicious" if malicious >= max(1, total // 2) else ("suspicious" if suspicious else "unknown"),
        "source_names": [s.source_name for s in sources],
    }
    if indicator.type == "ip":
        payload["geo"] = geo_for_ip(indicator.value)
        indicator.country = payload["geo"].get("country")
        indicator.city = payload["geo"].get("city")
        indicator.lat = payload["geo"].get("lat")
        indicator.lon = payload["geo"].get("lon")
    if indicator.type.startswith("hash_"):
        payload["detection_ratio"] = min(1.0, (malicious + 0.4) / 8)
        payload["engines"] = [
            {"name": "Microsoft", "result": "Trojan:Win32/CobaltStrike"},
            {"name": "Kaspersky", "result": "HEUR:Trojan.Win32.Generic"},
            {"name": "CrowdStrike", "result": "malicious_confidence_100"},
            {"name": "Sophos", "result": "Mal/Generic-S"},
        ]
        payload["malware_family"] = indicator.malware_family or "Cobalt Strike"
        payload["first_seen"] = indicator.first_seen.isoformat()
        payload["last_seen"] = indicator.last_seen.isoformat()
    if indicator.type in {"domain", "url"}:
        payload["phishing"] = indicator.category in {"phishing", "credential_harvest"}
        payload["registration"] = {"registrar": "NameCheap", "created": "2026-08-12", "age_days": 38}
        payload["related_ips"] = []
    avg_rep = sum(s.confidence for s in sources) / total if sources else indicator.confidence
    sightings = 0
    from app.models import SecurityEvent

    sightings = db.query(SecurityEvent).filter(SecurityEvent.indicator_id == indicator.id).count()
    indicator.confidence = int(avg_rep)
    indicator.severity_score = compute_severity(
        source_reputation=avg_rep,
        confidence=indicator.confidence,
        last_seen=indicator.last_seen,
        internal_sightings=sightings,
        indicator_type=indicator.type,
        enrichment=payload,
    )
    rec = Enrichment(indicator_id=indicator.id, provider="threatlens-aggregate", payload=payload)
    db.add(rec)
    db.add(indicator)
    db.flush()
    return payload
