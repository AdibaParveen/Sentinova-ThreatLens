from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.correlation import correlate_indicator, maybe_raise_alert
from app.db import get_db
from app.deps import client_ip, correlation_id, current_user, require
from app.enrichment import enrich_indicator
from app.models import (
    Alert,
    AttackTechnique,
    AuditLog,
    ContainmentItem,
    Feed,
    Incident,
    IncidentAlert,
    IncidentIndicator,
    IncidentTimeline,
    Indicator,
    IndicatorRelationship,
    IndicatorSource,
    IndicatorTag,
    IndicatorTechnique,
    Report,
    SavedHunt,
    SecurityEvent,
    Tag,
    User,
)
from app.normalize import fingerprint, normalize_value
from app.realtime import publish
from app.scoring import score_breakdown, severity_label
from app.services.ai_triage import generate_triage
from app.services.reports import build_pdf, build_stix

router = APIRouter(tags=["intelligence"])


def ind_out(db: Session, ind: Indicator, include_detail: bool = False) -> dict:
    tags = (
        db.query(Tag.name)
        .join(IndicatorTag, IndicatorTag.tag_id == Tag.id)
        .filter(IndicatorTag.indicator_id == ind.id)
        .all()
    )
    data = {
        "id": str(ind.id),
        "value": ind.value,
        "type": ind.type,
        "severity_score": ind.severity_score,
        "severity": severity_label(ind.severity_score),
        "confidence": ind.confidence,
        "tlp": ind.tlp,
        "status": ind.status,
        "first_seen": ind.first_seen.isoformat() if ind.first_seen else None,
        "last_seen": ind.last_seen.isoformat() if ind.last_seen else None,
        "country": ind.country,
        "city": ind.city,
        "lat": ind.lat,
        "lon": ind.lon,
        "category": ind.category,
        "malware_family": ind.malware_family,
        "notes": ind.notes,
        "tags": [t[0] for t in tags],
        "is_demo": ind.is_demo,
    }
    if include_detail:
        sources = db.query(IndicatorSource).filter(IndicatorSource.indicator_id == ind.id).all()
        techs = (
            db.query(AttackTechnique)
            .join(IndicatorTechnique, IndicatorTechnique.technique_id == AttackTechnique.id)
            .filter(IndicatorTechnique.indicator_id == ind.id)
            .all()
        )
        rels = db.query(IndicatorRelationship).filter(
            or_(IndicatorRelationship.source_id == ind.id, IndicatorRelationship.target_id == ind.id)
        ).all()
        events = db.query(SecurityEvent).filter(SecurityEvent.indicator_id == ind.id).order_by(SecurityEvent.occurred_at.desc()).all()
        enrich = ind.enrichments[-1].payload if ind.enrichments else {}
        data.update(
            {
                "sources": [
                    {"name": s.source_name, "confidence": s.confidence, "verdict": s.verdict, "reported_at": s.reported_at.isoformat()}
                    for s in sources
                ],
                "attack": [{"id": t.id, "name": t.name, "tactic": t.tactic} for t in techs],
                "relationships": [
                    {"id": str(r.id), "source_id": str(r.source_id), "target_id": str(r.target_id), "type": r.rel_type}
                    for r in rels
                ],
                "internal_events": [
                    {
                        "id": str(e.id),
                        "type": e.event_type,
                        "source_host": e.source_host,
                        "user": e.user_name,
                        "occurred_at": e.occurred_at.isoformat(),
                    }
                    for e in events
                ],
                "enrichment": enrich,
                "score_breakdown": score_breakdown(
                    source_reputation=ind.confidence,
                    confidence=ind.confidence,
                    last_seen=ind.last_seen,
                    internal_sightings=len(events),
                    indicator_type=ind.type,
                    enrichment=enrich,
                ),
            }
        )
    return data


@router.get("/indicators")
def list_indicators(
    q: str | None = None,
    type: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    tlp: str | None = None,
    page: int = 1,
    page_size: int = 25,
    user: User = Depends(require("indicators.read")),
    db: Session = Depends(get_db),
):
    query = db.query(Indicator)
    if q:
        query = query.filter(or_(Indicator.value.ilike(f"%{q}%"), Indicator.category.ilike(f"%{q}%")))
    if type:
        query = query.filter(Indicator.type == type)
    if status:
        query = query.filter(Indicator.status == status)
    if tlp:
        query = query.filter(Indicator.tlp == tlp)
    if severity:
        mapping = {"low": (0, 24), "medium": (25, 49), "high": (50, 74), "critical": (75, 100)}
        lo, hi = mapping.get(severity, (0, 100))
        query = query.filter(Indicator.severity_score.between(lo, hi))
    total = query.count()
    rows = query.order_by(Indicator.severity_score.desc(), Indicator.last_seen.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "items": [ind_out(db, i) for i in rows]}


@router.get("/indicators/{iid}")
def get_indicator(iid: UUID, user: User = Depends(require("indicators.read")), db: Session = Depends(get_db)):
    ind = db.get(Indicator, iid)
    if not ind:
        raise HTTPException(404, detail={"error_code": "NOT_FOUND", "message": "Indicator not found"})
    return ind_out(db, ind, include_detail=True)


class IndicatorIn(BaseModel):
    value: str
    type: str | None = None
    tlp: str = "amber"
    tags: list[str] = []
    notes: str | None = None
    attack: list[str] = []


@router.post("/indicators")
def create_indicator(payload: IndicatorIn, request: Request, user: User = Depends(require("indicators.write")), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    value, typ = normalize_value(payload.value, payload.type)
    fp = fingerprint(value, typ)
    existing = db.query(Indicator).filter(Indicator.fingerprint == fp).first()
    if existing:
        existing.last_seen = datetime.now(timezone.utc)
        db.add(IndicatorSource(indicator_id=existing.id, source_name="manual", confidence=70, verdict="suspicious"))
        write_audit(db, action="INDICATOR_DEDUPE", user=user, resource="indicator", resource_id=str(existing.id), ip=client_ip(request), correlation_id=cid)
        db.commit()
        return ind_out(db, existing, True)
    ind = Indicator(value=value, type=typ, fingerprint=fp, tlp=payload.tlp, notes=payload.notes, is_demo=False, status="active")
    db.add(ind)
    db.flush()
    db.add(IndicatorSource(indicator_id=ind.id, source_name="manual", confidence=70, verdict="suspicious"))
    for tname in payload.tags:
        tag = db.query(Tag).filter(Tag.name == tname).first() or Tag(name=tname)
        db.add(tag)
        db.flush()
        db.add(IndicatorTag(indicator_id=ind.id, tag_id=tag.id))
    for tid in payload.attack:
        if db.get(AttackTechnique, tid):
            db.add(IndicatorTechnique(indicator_id=ind.id, technique_id=tid))
    events = correlate_indicator(db, ind)
    enrich_indicator(ind, db)
    maybe_raise_alert(db, ind, events)
    write_audit(db, action="INDICATOR_CREATE", user=user, resource="indicator", resource_id=str(ind.id), ip=client_ip(request), correlation_id=cid)
    db.commit()
    return ind_out(db, ind, True)


class IndicatorPatch(BaseModel):
    status: str | None = None
    tlp: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    attack: list[str] | None = None


@router.patch("/indicators/{iid}")
def patch_indicator(iid: UUID, payload: IndicatorPatch, request: Request, user: User = Depends(require("indicators.write")), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    ind = db.get(Indicator, iid)
    if not ind:
        raise HTTPException(404, detail={"error_code": "NOT_FOUND", "message": "Indicator not found"})
    if payload.status:
        ind.status = payload.status
    if payload.tlp:
        ind.tlp = payload.tlp
    if payload.notes is not None:
        ind.notes = payload.notes
    write_audit(db, action="INDICATOR_UPDATE", user=user, resource="indicator", resource_id=str(ind.id), ip=client_ip(request), correlation_id=cid, metadata=payload.model_dump(exclude_none=True))
    db.commit()
    return ind_out(db, ind, True)


@router.post("/indicators/{iid}/enrich")
def enrich(iid: UUID, request: Request, user: User = Depends(require("indicators.enrich")), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    ind = db.get(Indicator, iid)
    if not ind:
        raise HTTPException(404, detail={"error_code": "NOT_FOUND", "message": "Indicator not found"})
    payload = enrich_indicator(ind, db)
    events = correlate_indicator(db, ind)
    maybe_raise_alert(db, ind, events)
    write_audit(db, action="ENRICH_INDICATOR", user=user, resource="indicator", resource_id=str(ind.id), ip=client_ip(request), correlation_id=cid)
    db.commit()
    publish("indicators.high_severity", {"id": str(ind.id), "value": ind.value, "score": ind.severity_score}) if ind.severity_score >= 75 else None
    return {"enrichment": payload, "indicator": ind_out(db, ind, True)}


@router.post("/indicators/{iid}/ai-triage")
def ai_triage(iid: UUID, request: Request, user: User = Depends(require("indicators.enrich")), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    ind = db.get(Indicator, iid)
    if not ind:
        raise HTTPException(404, detail={"error_code": "NOT_FOUND", "message": "Indicator not found"})
    detail = ind_out(db, ind, True)
    summary = generate_triage(detail)
    write_audit(db, action="AI_TRIAGE", user=user, resource="indicator", resource_id=str(ind.id), ip=client_ip(request), correlation_id=cid)
    db.commit()
    return summary


@router.get("/alerts")
def list_alerts(
    severity: str | None = None,
    status: str | None = None,
    source: str | None = None,
    category: str | None = None,
    assignee: str | None = None,
    type: str | None = None,
    page: int = 1,
    page_size: int = 25,
    mine: bool = False,
    user: User = Depends(require("alerts.read")),
    db: Session = Depends(get_db),
):
    q = db.query(Alert)
    if severity:
        q = q.filter(Alert.severity == severity)
    if status:
        q = q.filter(Alert.status == status)
    if source:
        q = q.filter(Alert.source == source)
    if category:
        q = q.filter(Alert.category == category)
    if mine:
        q = q.filter(Alert.assignee_id == user.id)
    if assignee:
        q = q.filter(Alert.assignee_id == assignee)
    total = q.count()
    rows = q.order_by(Alert.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for a in rows:
        ind = db.get(Indicator, a.indicator_id) if a.indicator_id else None
        items.append(alert_out(a, ind, user, db))
    items.sort(key=lambda x: x.get("severity_score", 0), reverse=True)
    return {"total": total, "items": items}


def alert_out(a: Alert, ind: Indicator | None, user: User, db: Session) -> dict:
    assignee = db.get(User, a.assignee_id) if a.assignee_id else None
    return {
        "id": str(a.id),
        "title": a.title,
        "severity": a.severity,
        "severity_score": ind.severity_score if ind else 0,
        "status": a.status,
        "source": a.source,
        "category": a.category,
        "created_at": a.created_at.isoformat(),
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        "assignee": {"id": str(assignee.id), "name": assignee.full_name} if assignee else None,
        "indicator": ind_out(db, ind) if ind else None,
        "notes": a.notes,
    }


class AlertPatch(BaseModel):
    status: str | None = None
    assignee_id: str | None = None
    notes: str | None = None


@router.patch("/alerts/{aid}")
def patch_alert(aid: UUID, payload: AlertPatch, request: Request, user: User = Depends(require("alerts.manage")), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    a = db.get(Alert, aid)
    if not a:
        raise HTTPException(404, detail={"error_code": "NOT_FOUND", "message": "Alert not found"})
    if payload.status:
        allowed = {"new", "acknowledged", "in_progress", "resolved", "closed"}
        if payload.status not in allowed:
            raise HTTPException(400, detail={"error_code": "INVALID_STATUS", "message": "Invalid lifecycle state"})
        a.status = payload.status
    if payload.assignee_id:
        a.assignee_id = payload.assignee_id
    if payload.notes is not None:
        a.notes = (a.notes or "") + f"\n[{user.full_name}] {payload.notes}"
    write_audit(db, action="ALERT_UPDATE", user=user, resource="alert", resource_id=str(a.id), ip=client_ip(request), correlation_id=cid, metadata=payload.model_dump(exclude_none=True))
    publish("alerts.stream", {"id": str(a.id), "status": a.status, "title": a.title, "severity": a.severity})
    db.commit()
    ind = db.get(Indicator, a.indicator_id) if a.indicator_id else None
    return alert_out(a, ind, user, db)


@router.post("/alerts/{aid}/escalate")
def escalate_alert(aid: UUID, request: Request, user: User = Depends(require("incidents.escalate")), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    a = db.get(Alert, aid)
    if not a:
        raise HTTPException(404, detail={"error_code": "NOT_FOUND", "message": "Alert not found"})
    ind = db.get(Indicator, a.indicator_id) if a.indicator_id else None
    inc = Incident(
        title=f"Incident from alert: {a.title}",
        severity=a.severity,
        status="open",
        assignee_id=user.id,
        is_demo=False,
    )
    db.add(inc)
    db.flush()
    db.add(IncidentAlert(incident_id=inc.id, alert_id=a.id))
    if ind:
        db.add(IncidentIndicator(incident_id=inc.id, indicator_id=ind.id))
    db.add(IncidentTimeline(incident_id=inc.id, event_type="incident_creation", message=f"Escalated from alert {a.id}", actor_id=user.id))
    db.add(IncidentTimeline(incident_id=inc.id, event_type="alert_generated", message=a.title, actor_id=user.id))
    for label in [
        "Validate indicator",
        "Identify affected assets",
        "Review internal sightings",
        "Investigate related infrastructure",
        "Document evidence",
        "Escalate if required",
        "Close incident",
    ]:
        db.add(ContainmentItem(incident_id=inc.id, label=label, done=False))
    a.status = "in_progress"
    write_audit(db, action="ALERT_ESCALATE", user=user, resource="incident", resource_id=str(inc.id), ip=client_ip(request), correlation_id=cid)
    publish(f"incidents.{inc.id}", {"event": "created"})
    db.commit()
    return {"incident_id": str(inc.id)}


@router.get("/soc/counters")
def soc_counters(user: User = Depends(require("dashboards.soc")), db: Session = Depends(get_db)):
    return {
        "new_alerts": db.query(Alert).filter(Alert.status == "new").count(),
        "unassigned": db.query(Alert).filter(Alert.assignee_id.is_(None), Alert.status.in_(["new", "acknowledged", "in_progress"])).count(),
        "my_queue": db.query(Alert).filter(Alert.assignee_id == user.id, Alert.status.in_(["new", "acknowledged", "in_progress"])).count(),
        "critical_alerts": db.query(Alert).filter(Alert.severity == "critical", Alert.status != "closed").count(),
        "active_incidents": db.query(Incident).filter(Incident.status.in_(["open", "investigating"])).count(),
    }


@router.get("/incidents")
def list_incidents(user: User = Depends(require("incidents.read")), db: Session = Depends(get_db)):
    rows = db.query(Incident).order_by(Incident.updated_at.desc()).all()
    return {"items": [inc_out(db, i) for i in rows]}


@router.get("/incidents/{iid}")
def get_incident(iid: UUID, user: User = Depends(require("incidents.read")), db: Session = Depends(get_db)):
    inc = db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, detail={"error_code": "NOT_FOUND", "message": "Incident not found"})
    return inc_detail(db, inc)


def inc_out(db: Session, inc: Incident) -> dict:
    asg = db.get(User, inc.assignee_id) if inc.assignee_id else None
    return {
        "id": str(inc.id),
        "title": inc.title,
        "severity": inc.severity,
        "status": inc.status,
        "assignee": asg.full_name if asg else None,
        "created_at": inc.created_at.isoformat(),
        "updated_at": inc.updated_at.isoformat() if inc.updated_at else None,
    }


def inc_detail(db: Session, inc: Incident) -> dict:
    timeline = db.query(IncidentTimeline).filter(IncidentTimeline.incident_id == inc.id).order_by(IncidentTimeline.created_at.asc()).all()
    checks = db.query(ContainmentItem).filter(ContainmentItem.incident_id == inc.id).all()
    iids = [r.indicator_id for r in db.query(IncidentIndicator).filter(IncidentIndicator.incident_id == inc.id)]
    aids = [r.alert_id for r in db.query(IncidentAlert).filter(IncidentAlert.incident_id == inc.id)]
    return {
        **inc_out(db, inc),
        "timeline": [
            {"id": str(t.id), "type": t.event_type, "message": t.message, "created_at": t.created_at.isoformat()}
            for t in timeline
        ],
        "checklist": [{"id": str(c.id), "label": c.label, "done": c.done} for c in checks],
        "indicators": [ind_out(db, db.get(Indicator, i)) for i in iids if db.get(Indicator, i)],
        "alerts": [str(a) for a in aids],
    }


class TimelineIn(BaseModel):
    message: str
    event_type: str = "analyst_note"


@router.post("/incidents/{iid}/timeline")
def add_timeline(iid: UUID, payload: TimelineIn, request: Request, user: User = Depends(require("incidents.manage")), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    inc = db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, detail={"error_code": "NOT_FOUND", "message": "Incident not found"})
    rec = IncidentTimeline(incident_id=inc.id, event_type=payload.event_type, message=payload.message, actor_id=user.id)
    db.add(rec)
    write_audit(db, action="INCIDENT_NOTE", user=user, resource="incident", resource_id=str(inc.id), ip=client_ip(request), correlation_id=cid)
    publish(f"incidents.{inc.id}", {"event": "timeline"})
    db.commit()
    return inc_detail(db, inc)


class CheckIn(BaseModel):
    done: bool


@router.patch("/incidents/{iid}/checklist/{cid}")
def patch_check(iid: UUID, cid: UUID, payload: CheckIn, user: User = Depends(require("incidents.manage")), db: Session = Depends(get_db)):
    item = db.get(ContainmentItem, cid)
    if not item or item.incident_id != iid:
        raise HTTPException(404, detail={"error_code": "NOT_FOUND", "message": "Item not found"})
    item.done = payload.done
    db.commit()
    return {"id": str(item.id), "done": item.done}


@router.get("/graph")
def graph(seed: str | None = None, user: User = Depends(require("dashboards.hunting")), db: Session = Depends(get_db)):
    inds = db.query(Indicator).all()
    rels = db.query(IndicatorRelationship).all()
    nodes = [{"id": str(i.id), "label": i.value, "type": i.type, "severity": i.severity_score} for i in inds]
    edges = [{"source": str(r.source_id), "target": str(r.target_id), "type": r.rel_type} for r in rels]
    return {"nodes": nodes, "edges": edges}


@router.get("/hunts")
def hunts(user: User = Depends(require("hunts.manage")), db: Session = Depends(get_db)):
    rows = db.query(SavedHunt).order_by(SavedHunt.created_at.desc()).all()
    return {"items": [{"id": str(h.id), "name": h.name, "description": h.description, "query": h.query, "tags": h.tags} for h in rows]}


class HuntIn(BaseModel):
    name: str
    description: str = ""
    query: dict = {}
    tags: list[str] = []


@router.post("/hunts")
def save_hunt(payload: HuntIn, request: Request, user: User = Depends(require("hunts.manage")), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    h = SavedHunt(owner_id=user.id, **payload.model_dump())
    db.add(h)
    write_audit(db, action="HUNT_SAVE", user=user, resource="hunt", ip=client_ip(request), correlation_id=cid)
    db.commit()
    return {"id": str(h.id)}


@router.delete("/hunts/{hid}")
def delete_hunt(hid: UUID, request: Request, user: User = Depends(require("hunts.manage")), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    h = db.get(SavedHunt, hid)
    if h:
        db.delete(h)
        write_audit(db, action="HUNT_DELETE", user=user, resource="hunt", resource_id=str(hid), ip=client_ip(request), correlation_id=cid)
        db.commit()
    return {"status": "ok"}


@router.get("/search")
def search(q: str = "", user: User = Depends(require("intelligence.search")), db: Session = Depends(get_db)):
    ql = f"%{q}%"
    inds = db.query(Indicator).filter(or_(Indicator.value.ilike(ql), Indicator.category.ilike(ql))).limit(15).all()
    alerts = db.query(Alert).filter(Alert.title.ilike(ql)).limit(10).all()
    incs = db.query(Incident).filter(Incident.title.ilike(ql)).limit(10).all()
    events = db.query(SecurityEvent).filter(or_(SecurityEvent.indicator_value.ilike(ql), SecurityEvent.source_host.ilike(ql))).limit(10).all()
    techs = db.query(AttackTechnique).filter(or_(AttackTechnique.id.ilike(ql), AttackTechnique.name.ilike(ql))).limit(10).all()
    tags = db.query(Tag).filter(Tag.name.ilike(ql)).limit(10).all()
    return {
        "indicators": [ind_out(db, i) for i in inds],
        "alerts": [{"id": str(a.id), "title": a.title, "severity": a.severity} for a in alerts],
        "incidents": [{"id": str(i.id), "title": i.title, "severity": i.severity} for i in incs],
        "events": [{"id": str(e.id), "type": e.event_type, "value": e.indicator_value} for e in events],
        "techniques": [{"id": t.id, "name": t.name, "tactic": t.tactic} for t in techs],
        "tags": [t.name for t in tags],
    }


@router.get("/feeds")
def feeds(user: User = Depends(require("feeds.manage")), db: Session = Depends(get_db)):
    rows = db.query(Feed).all()
    return {
        "items": [
            {
                "id": str(f.id),
                "name": f.name,
                "provider": f.provider,
                "type": f.feed_type,
                "status": f.status,
                "enabled": f.enabled,
                "last_poll_at": f.last_poll_at.isoformat() if f.last_poll_at else None,
                "next_poll_at": f.next_poll_at.isoformat() if f.next_poll_at else None,
                "indicators_received": f.indicators_received,
                "error_count": f.error_count,
            }
            for f in rows
        ]
    }


class FeedPatch(BaseModel):
    enabled: bool | None = None
    poll_interval_minutes: int | None = None


@router.patch("/feeds/{fid}")
def patch_feed(fid: UUID, payload: FeedPatch, request: Request, user: User = Depends(require("feeds.manage")), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    f = db.get(Feed, fid)
    if not f:
        raise HTTPException(404, detail={"error_code": "NOT_FOUND", "message": "Feed not found"})
    if payload.enabled is not None:
        f.enabled = payload.enabled
    if payload.poll_interval_minutes:
        f.poll_interval_minutes = payload.poll_interval_minutes
    write_audit(db, action="FEED_UPDATE", user=user, resource="feed", resource_id=str(f.id), ip=client_ip(request), correlation_id=cid)
    db.commit()
    return {"id": str(f.id), "enabled": f.enabled}


@router.post("/feeds/{fid}/poll")
def poll_feed(fid: UUID, request: Request, user: User = Depends(require("feeds.manage")), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    f = db.get(Feed, fid)
    if not f:
        raise HTTPException(404, detail={"error_code": "NOT_FOUND", "message": "Feed not found"})
    f.last_poll_at = datetime.now(timezone.utc)
    f.status = "healthy"
    write_audit(db, action="FEED_POLL", user=user, resource="feed", resource_id=str(f.id), ip=client_ip(request), correlation_id=cid)
    db.commit()
    return {"status": "queued"}


@router.get("/audit")
def audit_logs(user: User = Depends(require("audit.view")), db: Session = Depends(get_db), q: str | None = None):
    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    if q:
        query = query.filter(or_(AuditLog.action.ilike(f"%{q}%"), AuditLog.user_name.ilike(f"%{q}%"), AuditLog.correlation_id.ilike(f"%{q}%")))
    rows = query.limit(200).all()
    return {
        "items": [
            {
                "id": str(r.id),
                "timestamp": r.timestamp.isoformat(),
                "user": r.user_name,
                "role": r.role,
                "action": r.action,
                "resource": r.resource,
                "resource_id": r.resource_id,
                "ip_address": r.ip_address,
                "correlation_id": r.correlation_id,
                "result": r.result,
                "metadata": r.metadata_json,
            }
            for r in rows
        ]
    }


@router.get("/dashboards/executive")
def exec_dash(user: User = Depends(require("dashboards.executive")), db: Session = Depends(get_db)):
    inds = db.query(Indicator).all()
    alerts = db.query(Alert).all()
    incs = db.query(Incident).all()
    crit = sum(1 for i in inds if i.severity_score >= 75)
    high = sum(1 for i in inds if 50 <= i.severity_score < 75)
    risk = 0
    if inds:
        risk = int(sum(i.severity_score for i in inds) / len(inds))
        if any(a.status == "new" and a.severity == "critical" for a in alerts):
            risk = min(100, risk + 8)
    cats = {}
    geos = {}
    sources = {}
    for i in inds:
        cats[i.category] = cats.get(i.category, 0) + 1
        if i.country:
            geos[i.country] = geos.get(i.country, 0) + 1
    for s in db.query(IndicatorSource).all():
        sources[s.source_name] = sources.get(s.source_name, 0) + 1
    resolved = sum(1 for a in alerts if a.status in {"resolved", "closed"})
    return {
        "risk_score": risk,
        "critical_indicators": crit,
        "high_indicators": high,
        "active_incidents": sum(1 for i in incs if i.status != "closed"),
        "open_alerts": sum(1 for a in alerts if a.status not in {"resolved", "closed"}),
        "categories": cats,
        "geographies": geos,
        "sources": sources,
        "alerts_received": len(alerts),
        "alerts_resolved": resolved,
        "severity_distribution": {
            "critical": crit,
            "high": high,
            "medium": sum(1 for i in inds if 25 <= i.severity_score < 50),
            "low": sum(1 for i in inds if i.severity_score < 25),
        },
        "map_points": [
            {"value": i.value, "lat": i.lat, "lon": i.lon, "country": i.country, "severity": i.severity_score, "type": i.type}
            for i in inds
            if i.lat and i.lon
        ],
    }


@router.get("/attack")
def attack_coverage(user: User = Depends(require("dashboards.hunting")), db: Session = Depends(get_db)):
    techs = db.query(AttackTechnique).all()
    mapped = {r.technique_id for r in db.query(IndicatorTechnique).all()}
    return {
        "techniques": [
            {"id": t.id, "name": t.name, "tactic": t.tactic, "covered": t.id in mapped}
            for t in techs
        ]
    }


class ReportIn(BaseModel):
    report_type: str = "executive"
    format: str = "pdf"
    title: str | None = None
    tlp_max: str = "red"


@router.post("/reports")
def create_report(payload: ReportIn, request: Request, user: User = Depends(require("reports.generate")), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    data = exec_dash(user, db) if False else None
    # rebuild executive snapshot
    from app.api.v1 import intel as _self  # noqa

    snap = {
        "type": payload.report_type,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": user.full_name,
        "tlp_max": payload.tlp_max,
    }
    rec = Report(title=payload.title or f"{payload.report_type.title()} report", report_type=payload.report_type, format=payload.format, created_by=user.id, payload=snap, status="ready")
    db.add(rec)
    write_audit(db, action="REPORT_GENERATE", user=user, resource="report", ip=client_ip(request), correlation_id=cid)
    db.commit()
    return {"id": str(rec.id), "status": "ready"}


@router.get("/reports")
def list_reports(user: User = Depends(require("reports.generate")), db: Session = Depends(get_db)):
    rows = db.query(Report).order_by(Report.created_at.desc()).all()
    return {"items": [{"id": str(r.id), "title": r.title, "type": r.report_type, "format": r.format, "created_at": r.created_at.isoformat(), "status": r.status} for r in rows]}


@router.get("/export/csv")
def export_csv(user: User = Depends(require("export.intelligence")), db: Session = Depends(get_db), tlp_max: str = "red"):
    order = ["clear", "green", "amber", "red"]
    allowed = order[: order.index(tlp_max) + 1] if tlp_max in order else order
    rows = db.query(Indicator).filter(Indicator.tlp.in_(allowed)).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["value", "type", "severity", "confidence", "tlp", "status", "first_seen", "last_seen"])
    for i in rows:
        w.writerow([i.value, i.type, i.severity_score, i.confidence, i.tlp, i.status, i.first_seen, i.last_seen])
    return PlainTextResponse(buf.getvalue(), media_type="text/csv")


@router.get("/export/stix")
def export_stix(user: User = Depends(require("export.intelligence")), db: Session = Depends(get_db), tlp_max: str = "red"):
    order = ["clear", "green", "amber", "red"]
    allowed = order[: order.index(tlp_max) + 1] if tlp_max in order else order
    rows = db.query(Indicator).filter(Indicator.tlp.in_(allowed)).all()
    return build_stix(rows)


@router.get("/reports/{rid}/pdf")
def report_pdf(rid: UUID, user: User = Depends(require("reports.generate")), db: Session = Depends(get_db)):
    rec = db.get(Report, rid)
    if not rec:
        raise HTTPException(404, detail={"error_code": "NOT_FOUND", "message": "Report not found"})
    pdf = build_pdf(rec, db)
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={rec.id}.pdf"})


@router.get("/users")
def users(user: User = Depends(require("users.manage")), db: Session = Depends(get_db)):
    rows = db.query(User).all()
    from app.api.v1.auth import serialize_user

    return {"items": [serialize_user(u) for u in rows]}


class RoleIn(BaseModel):
    role: str


@router.patch("/users/{uid}/role")
def set_role(uid: UUID, payload: RoleIn, request: Request, user: User = Depends(require("users.manage")), db: Session = Depends(get_db), cid: str = Depends(correlation_id)):
    target = db.get(User, uid)
    if not target:
        raise HTTPException(404, detail={"error_code": "NOT_FOUND", "message": "User not found"})
    target.role = payload.role
    write_audit(db, action="USER_ROLE_CHANGE", user=user, resource="user", resource_id=str(uid), ip=client_ip(request), correlation_id=cid, metadata={"role": payload.role})
    db.commit()
    return {"status": "ok"}
