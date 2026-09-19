from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def uuid_pk() -> uuid.UUID:
    return uuid.uuid4()


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    organization: Mapped[str] = mapped_column(String(255), default="")
    job_title: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(64), default="soc_analyst", index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, active, locked, disabled
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    profile_picture: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    preferences: Mapped[Optional["UserPreference"]] = relationship(back_populates="user", uselist=False)
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user")


class EmailToken(Base):
    __tablename__ = "email_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    purpose: Mapped[str] = mapped_column(String(32))  # verify, reset, email_change
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    extra: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    refresh_jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_agent: Mapped[str] = mapped_column(String(512), default="")
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="sessions")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    theme: Mapped[str] = mapped_column(String(16), default="dark")
    density: Mapped[str] = mapped_column(String(16), default="comfortable")
    default_dashboard: Mapped[str] = mapped_column(String(32), default="soc")
    refresh_interval: Mapped[int] = mapped_column(Integer, default=15)
    visible_widgets: Mapped[dict] = mapped_column(JSONB, default=dict)
    saved_layouts: Mapped[dict] = mapped_column(JSONB, default=dict)
    default_filters: Mapped[dict] = mapped_column(JSONB, default=dict)
    notifications: Mapped[dict] = mapped_column(JSONB, default=dict)

    user: Mapped["User"] = relationship(back_populates="preferences")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(128))
    prefix: Mapped[str] = mapped_column(String(12), index=True)
    key_hash: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Webhook(Base):
    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(128))
    url: Mapped[str] = mapped_column(String(1024))
    events: Mapped[list] = mapped_column(JSONB, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    secret_prefix: Mapped[str] = mapped_column(String(8), default="")
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Feed(Base):
    __tablename__ = "feeds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    provider: Mapped[str] = mapped_column(String(128))
    feed_type: Mapped[str] = mapped_column(String(64))  # otx, abuseipdb, urlhaus, ...
    status: Mapped[str] = mapped_column(String(32), default="healthy")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    poll_interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    last_poll_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_poll_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    indicators_received: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)


class Indicator(Base):
    __tablename__ = "indicators"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_indicator_fingerprint"),
        Index("ix_indicators_queue", "status", "severity_score"),
        Index("ix_indicators_value_type", "value", "type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    value: Mapped[str] = mapped_column(Text, index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    severity_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    confidence: Mapped[int] = mapped_column(Integer, default=50)
    tlp: Mapped[str] = mapped_column(String(16), default="amber")
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    country: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    category: Mapped[str] = mapped_column(String(64), default="unknown")
    malware_family: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    sources: Mapped[list["IndicatorSource"]] = relationship(back_populates="indicator", cascade="all, delete-orphan")
    enrichments: Mapped[list["Enrichment"]] = relationship(back_populates="indicator", cascade="all, delete-orphan")


class IndicatorSource(Base):
    __tablename__ = "indicator_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    indicator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("indicators.id"), index=True)
    feed_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("feeds.id"), nullable=True)
    source_name: Mapped[str] = mapped_column(String(128))
    confidence: Mapped[int] = mapped_column(Integer, default=50)
    verdict: Mapped[str] = mapped_column(String(32), default="suspicious")
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    raw: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    indicator: Mapped["Indicator"] = relationship(back_populates="sources")


class Enrichment(Base):
    __tablename__ = "enrichments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    indicator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("indicators.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    indicator: Mapped["Indicator"] = relationship(back_populates="enrichments")


class IndicatorRelationship(Base):
    __tablename__ = "indicator_relationships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("indicators.id"), index=True)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("indicators.id"), index=True)
    rel_type: Mapped[str] = mapped_column(String(64))  # resolves-to, communicates, drops


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(64), unique=True)


class IndicatorTag(Base):
    __tablename__ = "indicator_tags"

    indicator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("indicators.id"), primary_key=True)
    tag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True)


class AttackTechnique(Base):
    __tablename__ = "attack_techniques"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # T1071.001
    name: Mapped[str] = mapped_column(String(255))
    tactic: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")


class IndicatorTechnique(Base):
    __tablename__ = "indicator_techniques"

    indicator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("indicators.id"), primary_key=True)
    technique_id: Mapped[str] = mapped_column(String(16), ForeignKey("attack_techniques.id"), primary_key=True)


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    event_type: Mapped[str] = mapped_column(String(64))
    source_host: Mapped[str] = mapped_column(String(255), default="")
    dest_host: Mapped[str] = mapped_column(String(255), default="")
    user_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    indicator_value: Mapped[str] = mapped_column(Text, index=True)
    indicator_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("indicators.id"), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    raw: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(128))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    min_severity: Mapped[int] = mapped_column(Integer, default=50)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    source: Mapped[str] = mapped_column(String(128), default="correlation")
    category: Mapped[str] = mapped_column(String(64), default="ioc_match")
    indicator_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("indicators.id"), nullable=True)
    assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("alert_rules.id"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(16), default="high")
    status: Mapped[str] = mapped_column(String(32), default="open")
    assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)


class IncidentAlert(Base):
    __tablename__ = "incident_alerts"
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), primary_key=True)
    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alerts.id"), primary_key=True)


class IncidentIndicator(Base):
    __tablename__ = "incident_indicators"
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), primary_key=True)
    indicator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("indicators.id"), primary_key=True)


class IncidentTimeline(Base):
    __tablename__ = "incident_timeline"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ContainmentItem(Base):
    __tablename__ = "containment_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), index=True)
    label: Mapped[str] = mapped_column(String(255))
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SavedHunt(Base):
    __tablename__ = "saved_hunts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    query: Mapped[dict] = mapped_column(JSONB, default=dict)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    title: Mapped[str] = mapped_column(String(255))
    report_type: Mapped[str] = mapped_column(String(32))
    format: Mapped[str] = mapped_column(String(16), default="pdf")
    status: Mapped[str] = mapped_column(String(32), default="ready")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    scheduled_cron: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    user_name: Mapped[str] = mapped_column(String(255), default="system")
    role: Mapped[str] = mapped_column(String(64), default="")
    action: Mapped[str] = mapped_column(String(64), index=True)
    resource: Mapped[str] = mapped_column(String(64), default="")
    resource_id: Mapped[str] = mapped_column(String(64), default="")
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    correlation_id: Mapped[str] = mapped_column(String(64), index=True)
    result: Mapped[str] = mapped_column(String(16), default="SUCCESS")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    ntype: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, default="")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    link: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
