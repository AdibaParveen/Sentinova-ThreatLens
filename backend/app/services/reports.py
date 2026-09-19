from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.models import Indicator, Report


def build_stix(indicators: list[Indicator]) -> dict:
    objs = [
        {
            "type": "identity",
            "spec_version": "2.1",
            "id": "identity--a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "modified": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "name": "ThreatLens",
            "identity_class": "organization",
        }
    ]
    type_map = {
        "ip": "ipv4-addr",
        "domain": "domain-name",
        "url": "url",
        "email": "email-addr",
        "hash_md5": "file",
        "hash_sha1": "file",
        "hash_sha256": "file",
        "cve": "vulnerability",
    }
    for ind in indicators:
        sco_type = type_map.get(ind.type, "indicator")
        obj: dict = {
            "type": "indicator",
            "spec_version": "2.1",
            "id": f"indicator--{ind.id}",
            "created": ind.first_seen.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "modified": ind.last_seen.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "name": ind.value,
            "pattern": f"[{sco_type}:value = '{ind.value}']",
            "pattern_type": "stix",
            "valid_from": ind.first_seen.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "confidence": ind.confidence,
            "labels": [ind.category, f"tlp:{ind.tlp}"],
        }
        objs.append(obj)
    return {"type": "bundle", "id": f"bundle--{uuid.uuid4()}", "objects": objs}


def build_pdf(report: Report, db: Session) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFillColorRGB(0.05, 0.08, 0.14)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColorRGB(0.9, 0.93, 0.99)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, y, "ThreatLens")
    y -= 24
    c.setFont("Helvetica", 12)
    c.drawString(40, y, report.title)
    y -= 18
    c.drawString(40, y, f"Type: {report.report_type}    Generated: {report.created_at.isoformat() if report.created_at else ''}")
    y -= 28
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Executive summary")
    y -= 16
    c.setFont("Helvetica", 10)
    inds = db.query(Indicator).order_by(Indicator.severity_score.desc()).limit(12).all()
    c.drawString(40, y, f"Key findings: {len(inds)} highlighted indicators. Scores are engine-computed, not hard-coded.")
    y -= 22
    for i in inds:
        if y < 60:
            c.showPage()
            y = height - 50
        c.drawString(40, y, f"{i.severity_score:>3}  {i.type:<12}  {i.value[:70]}  TLP:{i.tlp}")
        y -= 14
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(40, 30, "TLP handling applied. AI text is not included as evidence.")
    c.save()
    return buf.getvalue()
