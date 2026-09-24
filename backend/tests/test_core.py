from datetime import datetime, timezone

from app.normalize import detect_type, fingerprint, normalize_value
from app.rbac import has_permission
from app.scoring import compute_severity, severity_label


def test_normalize_ip_and_domain():
    v, t = normalize_value("185.220.101.47")
    assert t == "ip" and v == "185.220.101.47"
    v, t = normalize_value("Login-Office365-Secure.NET.")
    assert t == "domain" and v == "login-office365-secure.net"


def test_dedup_fingerprint_stable():
    a = fingerprint("Example.COM.", "domain")
    b = fingerprint("example.com", "domain")
    assert a == b


def test_detect_hash_and_cve():
    assert detect_type("44d88612fea8a8f36de82e1278abb02f") == "hash_md5"
    assert detect_type("CVE-2024-3400") == "cve"


def test_severity_bounds_and_labels():
    low = compute_severity(
    source_reputation=10,
    confidence=10,
    last_seen=datetime(
        2025,
        1,
        1,
        tzinfo=timezone.utc,
    ),
    internal_sightings=0,
    indicator_type="email",
    enrichment={},
)
    high = compute_severity(
        source_reputation=95,
        confidence=95,
        last_seen=datetime.now(timezone.utc),
        internal_sightings=5,
        indicator_type="hash_sha256",
        enrichment={
            "malicious_sources": 8,
            "total_sources": 9,
            "abuse_confidence": 92,
            "detection_ratio": 0.9,
        },
    )
    assert 0 <= low <= 24
    assert high >= 75
    assert severity_label(high) == "critical"


def test_rbac_matrix():
    assert has_permission("administrator", "users.manage")
    assert not has_permission("soc_analyst", "users.manage")
    assert not has_permission("executive", "alerts.manage")
    assert has_permission("soc_analyst", "alerts.manage")
    assert has_permission("threat_hunter", "hunts.manage")
    assert not has_permission("executive", "indicators.write")


def test_password_policy():
    from app.security import password_errors

    assert password_errors("short")
    assert password_errors("Password123")
    assert password_errors("password123!")
    assert not password_errors("ThreatLens!Demo1")


def test_correlation_matches_value():
    class FakeQ:
        def __init__(self, rows):
            self.rows = rows

        def filter(self, *a, **k):
            return self

        def all(self):
            return self.rows

    class FakeDB:
        def query(self, model):
            from app.models import SecurityEvent

            if model is SecurityEvent:
                ev = SecurityEvent(event_type="dns_query", indicator_value="185.220.101.47")
                return FakeQ([ev])
            return FakeQ([])

    from app.correlation import correlate_indicator
    from app.models import Indicator

    ind = Indicator(value="185.220.101.47", type="ip", fingerprint="x")
    events = correlate_indicator(FakeDB(), ind)
    assert events and events[0].indicator_id == ind.id
