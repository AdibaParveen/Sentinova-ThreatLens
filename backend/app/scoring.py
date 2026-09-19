"""Transparent 0–100 severity scoring. Unit-testable; never hard-code scores in the UI.

Weights (documented):
  source reputation   25%
  confidence          20%
  recency             15%
  internal sightings  20%
  indicator type      10%
  enrichment results  10%
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SEVERITY_LOW = (0, 24)
SEVERITY_MEDIUM = (25, 49)
SEVERITY_HIGH = (50, 74)
SEVERITY_CRITICAL = (75, 100)

TYPE_WEIGHT = {
    "ip": 0.70,
    "domain": 0.75,
    "url": 0.80,
    "hash_md5": 0.90,
    "hash_sha1": 0.92,
    "hash_sha256": 0.95,
    "email": 0.55,
    "cve": 0.85,
}


def severity_label(score: int) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def _clamp(n: float) -> int:
    return max(0, min(100, int(round(n))))


def recency_factor(last_seen: datetime | None, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    if last_seen is None:
        return 0.3
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    days = max(0.0, (now - last_seen).total_seconds() / 86400)
    if days <= 1:
        return 1.0
    if days <= 7:
        return 0.85
    if days <= 30:
        return 0.65
    if days <= 90:
        return 0.4
    return 0.2


def sightings_factor(count: int) -> float:
    if count <= 0:
        return 0.0
    if count == 1:
        return 0.45
    if count <= 3:
        return 0.75
    return 1.0


def enrichment_factor(enrichment: dict[str, Any] | None) -> float:
    if not enrichment:
        return 0.35
    malicious = float(enrichment.get("malicious_sources", 0) or 0)
    total = float(enrichment.get("total_sources", 0) or 0)
    abuse = float(enrichment.get("abuse_confidence", 0) or 0) / 100.0
    detections = float(enrichment.get("detection_ratio", 0) or 0)
    if total > 0:
        source_ratio = malicious / total
    else:
        source_ratio = 0.0
    return max(0.0, min(1.0, 0.45 * source_ratio + 0.35 * abuse + 0.20 * detections))


def compute_severity(
    *,
    source_reputation: float = 50.0,
    confidence: float = 50.0,
    last_seen: datetime | None = None,
    internal_sightings: int = 0,
    indicator_type: str = "ip",
    enrichment: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> int:
    """Return a 0–100 integer severity score from documented inputs."""
    src = max(0.0, min(100.0, source_reputation)) / 100.0
    conf = max(0.0, min(100.0, confidence)) / 100.0
    rec = recency_factor(last_seen, now)
    sight = sightings_factor(internal_sightings)
    typ = TYPE_WEIGHT.get(indicator_type, 0.6)
    enr = enrichment_factor(enrichment)
    raw = (
        25 * src
        + 20 * conf
        + 15 * rec
        + 20 * sight
        + 10 * typ
        + 10 * enr
    )
    return _clamp(raw)


def score_breakdown(
    *,
    source_reputation: float,
    confidence: float,
    last_seen: datetime | None,
    internal_sightings: int,
    indicator_type: str,
    enrichment: dict[str, Any] | None,
) -> dict[str, Any]:
    score = compute_severity(
        source_reputation=source_reputation,
        confidence=confidence,
        last_seen=last_seen,
        internal_sightings=internal_sightings,
        indicator_type=indicator_type,
        enrichment=enrichment,
    )
    return {
        "score": score,
        "label": severity_label(score),
        "components": {
            "source_reputation": source_reputation,
            "confidence": confidence,
            "recency": recency_factor(last_seen),
            "internal_sightings": internal_sightings,
            "indicator_type": indicator_type,
            "type_weight": TYPE_WEIGHT.get(indicator_type, 0.6),
            "enrichment": enrichment_factor(enrichment),
        },
        "weights": {
            "source_reputation": 0.25,
            "confidence": 0.20,
            "recency": 0.15,
            "internal_sightings": 0.20,
            "indicator_type": 0.10,
            "enrichment": 0.10,
        },
    }
