"""Background ingestion: poll configured feeds, normalize, dedupe, enrich, score, correlate."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.correlation import correlate_indicator, maybe_raise_alert
from app.enrichment import enrich_indicator
from app.models import Feed, Indicator, IndicatorSource
from app.normalize import fingerprint, normalize_value
from app.realtime import publish
from app.search_index import index_indicator


DEMO_PULLS = {
    "abuseipdb": [("185.220.101.47", "ip", "malicious", 97)],
    "otx": [("91.219.237.244", "ip", "malicious", 80)],
    "urlhaus": [("https://login-office365-secure.net/owa/auth", "url", "malicious", 90)],
    "threatfox": [("update-microsoft-cdn.net", "domain", "malicious", 84)],
}


def ingest_samples(db: Session, feed: Feed) -> int:
    count = 0
    samples = DEMO_PULLS.get(feed.feed_type, [])
    for value, typ, verdict, conf in samples:
        value, typ = normalize_value(value, typ)
        fp = fingerprint(value, typ)
        ind = db.query(Indicator).filter(Indicator.fingerprint == fp).first()
        if not ind:
            ind = Indicator(value=value, type=typ, fingerprint=fp, is_demo=True, status="active")
            db.add(ind)
            db.flush()
        else:
            ind.last_seen = datetime.now(timezone.utc)
        db.add(IndicatorSource(indicator_id=ind.id, feed_id=feed.id, source_name=feed.name, confidence=conf, verdict=verdict))
        events = correlate_indicator(db, ind)
        enrich_indicator(ind, db)
        maybe_raise_alert(db, ind, events)
        index_indicator(ind)
        count += 1
    feed.last_poll_at = datetime.now(timezone.utc)
    feed.indicators_received += len(samples)
    feed.status = "healthy"
    return count


def poll_feed(db: Session, feed: Feed) -> int:
    n = ingest_samples(db, feed)
    db.commit()
    if n:
        publish("system.health", {"ingestion": "ok", "count": n, "feed": feed.name})
    return n


def poll_all(db: Session) -> int:
    count = 0
    feeds = db.query(Feed).filter(Feed.enabled.is_(True)).all()
    for feed in feeds:
        count += ingest_samples(db, feed)
    db.commit()
    if count:
        publish("system.health", {"ingestion": "ok", "count": count})
    return count
