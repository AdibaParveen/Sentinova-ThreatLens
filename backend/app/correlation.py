from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Alert, AlertRule, Indicator, SecurityEvent
from app.realtime import publish
from app.scoring import severity_label


def correlate_indicator(db: Session, indicator: Indicator) -> list[SecurityEvent]:
    events = (
        db.query(SecurityEvent)
        .filter(SecurityEvent.indicator_value == indicator.value)
        .all()
    )
    for ev in events:
        ev.indicator_id = indicator.id
    return events


def maybe_raise_alert(db: Session, indicator: Indicator, events: list[SecurityEvent]) -> Alert | None:
    rules = db.query(AlertRule).filter(AlertRule.enabled.is_(True)).all()
    matching = None
    for rule in rules:
        if indicator.severity_score < rule.min_severity:
            continue
        if rule.category and rule.category != indicator.category:
            continue
        matching = rule
        break
    if matching is None and (indicator.severity_score >= 50 or events):
        matching = True
    if not matching:
        return None
    existing = (
        db.query(Alert)
        .filter(Alert.indicator_id == indicator.id, Alert.status.in_(["new", "acknowledged", "in_progress"]))
        .first()
    )
    if existing:
        return existing
    label = severity_label(indicator.severity_score)
    title = f"{label.upper()} {indicator.type}: {indicator.value}"
    if events:
        title += " — internal sighting"
    alert = Alert(
        title=title,
        severity=label,
        status="new",
        source="correlation",
        category=indicator.category,
        indicator_id=indicator.id,
        rule_id=matching.id if matching is not True else None,
        is_demo=indicator.is_demo,
    )
    db.add(alert)
    db.flush()
    publish("alerts.stream", {"id": str(alert.id), "title": alert.title, "severity": alert.severity, "status": alert.status})
    if indicator.severity_score >= 75:
        publish("indicators.high_severity", {"id": str(indicator.id), "value": indicator.value, "score": indicator.severity_score})
    return alert
