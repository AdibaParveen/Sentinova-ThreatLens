from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Notification, User
from app.rbac import has_permission
from app.realtime import publish


def notify_users(
    db: Session,
    *,
    ntype: str,
    title: str,
    body: str,
    link: str | None = None,
    permission: str | None = None,
    user_ids: list | None = None,
) -> None:
    q = db.query(User).filter(User.status == "active")
    users = q.all()
    for u in users:
        if user_ids and u.id not in user_ids:
            continue
        if permission and not has_permission(u.role, permission):
            continue
        prefs = u.preferences
        if prefs and prefs.notifications:
            mapping = {
                "critical_alert": "critical_alerts",
                "high_severity": "high_severity",
                "incident_assignment": "incident_assignments",
                "incident_update": "new_incidents",
                "feed_failure": "system",
                "system": "system",
            }
            key = mapping.get(ntype)
            if key and prefs.notifications.get(key) is False:
                continue
            if prefs.notifications.get("in_app") is False:
                continue
        db.add(Notification(user_id=u.id, ntype=ntype, title=title, body=body, link=link))
        publish("notifications", {"user_id": str(u.id), "title": title, "type": ntype})
