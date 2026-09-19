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
    low = compute_severity(source_reputation=10, confidence=10, last_seen=datetime.now(timezone.utc), internal_sightings=0, indicator_type="email", enrichment={})
    high = compute_severity(
        source_reputation=95,
        confidence=95,
        last_seen=datetime.now(timezone.utc),
        internal_sightings=5,
        indicator_type="hash_sha256",
        enrichment={"malicious_sources": 8, "total_sources": 9, "abuse_confidence": 92, "detection_ratio": 0.9},
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
