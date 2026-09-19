from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import (
    Alert,
    AlertRule,
    AttackTechnique,
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
    SavedHunt,
    SecurityEvent,
    Tag,
    User,
    UserPreference,
)
from app.normalize import fingerprint, normalize_value
from app.scoring import compute_severity
from app.security import hash_password

DEMO_PASSWORD = "ThreatLens!Demo1"

TECHNIQUES = [
    ("T1071.001", "Web Protocols", "Command and Control"),
    ("T1566.002", "Spearphishing Link", "Initial Access"),
    ("T1059.001", "PowerShell", "Execution"),
    ("T1003.001", "LSASS Memory", "Credential Access"),
    ("T1027", "Obfuscated Files or Information", "Defense Evasion"),
    ("T1041", "Exfiltration Over C2 Channel", "Exfiltration"),
    ("T1190", "Exploit Public-Facing Application", "Initial Access"),
    ("T1055", "Process Injection", "Defense Evasion"),
    ("T1078", "Valid Accounts", "Persistence"),
    ("T1486", "Data Encrypted for Impact", "Impact"),
]

FEEDS = [
    ("AlienVault OTX", "AT&T Cybersecurity", "otx"),
    ("AbuseIPDB", "AbuseIPDB", "abuseipdb"),
    ("URLhaus", "abuse.ch", "urlhaus"),
    ("MalwareBazaar", "abuse.ch", "malwarebazaar"),
    ("ThreatFox", "abuse.ch", "threatfox"),
    ("Feodo Tracker", "abuse.ch", "feodo"),
    ("MITRE ATT&CK", "MITRE", "attack"),
    ("CISA KEV", "CISA", "cisa_kev"),
]

USERS = [
    ("admin@threatlens.local", "Adiba Parveen", "administrator", "Sentinova Security Systems", "Platform Administrator"),
    ("engineer@threatlens.local", "Kenji Sato", "security_engineer", "Sentinova Security Systems", "Detection Engineer"),
    ("responder@threatlens.local", "Daniel Okafor", "incident_responder", "Sentinova Security Systems", "IR Lead"),
    ("hunter@threatlens.local", "Mei Lin Tan", "threat_hunter", "Sentinova Security Systems", "Threat Hunter"),
    ("analyst@threatlens.local", "Priya Nair", "soc_analyst", "Sentinova Security Systems", "SOC Analyst"),
    ("exec@threatlens.local", "Rachel Adeyemi", "executive", "Sentinova Security Systems", "CISO"),
]


def seed(db: Session) -> None:
    if db.query(User).first():
        return
    now = datetime.now(timezone.utc)
    users = {}
    for email, name, role, org, title in USERS:
        u = User(
            email=email,
            full_name=name,
            password_hash=hash_password(DEMO_PASSWORD),
            organization=org,
            job_title=title,
            role=role,
            status="active",
            email_verified=True,
            is_demo=True,
            last_login_at=now - timedelta(hours=2),
        )
        db.add(u)
        db.flush()
        db.add(
            UserPreference(
                user_id=u.id,
                theme="dark",
                density="comfortable",
                default_dashboard="overview" if role == "executive" else ("soc" if role == "soc_analyst" else "overview"),
                notifications={
                    "critical_alerts": True,
                    "high_severity": True,
                    "new_incidents": True,
                    "incident_assignments": True,
                    "intel_updates": role != "executive",
                    "system": role in {"administrator", "security_engineer"},
                    "email": True,
                    "in_app": True,
                },
                visible_widgets={"risk": True, "queue": True, "map": True, "trends": True},
            )
        )
        users[role] = u

    for tid, name, tactic in TECHNIQUES:
        db.add(AttackTechnique(id=tid, name=name, tactic=tactic, description=name))

    feeds = {}
    for name, provider, ftype in FEEDS:
        f = Feed(
            name=name,
            provider=provider,
            feed_type=ftype,
            status="healthy",
            enabled=True,
            last_poll_at=now - timedelta(minutes=12),
            next_poll_at=now + timedelta(minutes=48),
            indicators_received=120 + len(name),
            is_demo=True,
        )
        db.add(f)
        db.flush()
        feeds[ftype] = f

    tags = {}
    for t in ["apt29", "cobalt-strike", "phishing", "c2", "ransomware", "tor-exit", "demo"]:
        tag = Tag(name=t)
        db.add(tag)
        db.flush()
        tags[t] = tag

    iocs = [
        {
            "value": "185.220.101.47",
            "type": "ip",
            "category": "c2",
            "tlp": "amber",
            "country": "DE",
            "city": "Frankfurt",
            "lat": 50.11,
            "lon": 8.68,
            "family": None,
            "sources": [("AlienVault OTX", 92, "malicious"), ("AbuseIPDB", 97, "malicious"), ("Feodo Tracker", 88, "malicious"), ("ThreatFox", 90, "malicious")],
            "tech": ["T1071.001", "T1041"],
            "tags": ["tor-exit", "c2", "demo"],
        },
        {
            "value": "login-office365-secure.net",
            "type": "domain",
            "category": "phishing",
            "tlp": "amber",
            "country": "US",
            "city": "Dallas",
            "lat": 32.78,
            "lon": -96.8,
            "sources": [("URLhaus", 85, "malicious"), ("AlienVault OTX", 70, "suspicious")],
            "tech": ["T1566.002"],
            "tags": ["phishing", "demo"],
        },
        {
            "value": "https://login-office365-secure.net/owa/auth",
            "type": "url",
            "category": "phishing",
            "tlp": "red",
            "country": "US",
            "city": "Dallas",
            "lat": 32.78,
            "lon": -96.8,
            "sources": [("URLhaus", 91, "malicious")],
            "tech": ["T1566.002"],
            "tags": ["phishing", "demo"],
        },
        {
            "value": "44d88612fea8a8f36de82e1278abb02f",
            "type": "hash_md5",
            "category": "malware",
            "tlp": "green",
            "family": "eicar-test",
            "sources": [("MalwareBazaar", 60, "suspicious")],
            "tech": ["T1027"],
            "tags": ["demo"],
        },
        {
            "value": "d6fcb4f0c0e1a3b8e7c1a9f4e2b6c8d0e1f2a3b4",
            "type": "hash_sha1",
            "category": "malware",
            "tlp": "amber",
            "family": "Beacon",
            "sources": [("MalwareBazaar", 88, "malicious"), ("ThreatFox", 80, "malicious")],
            "tech": ["T1055", "T1071.001"],
            "tags": ["cobalt-strike", "demo"],
        },
        {
            "value": "3b5d5c3712955042212316173ccf37be6f1e1da3d0c412747edf362374d33da6",
            "type": "hash_sha256",
            "category": "malware",
            "tlp": "amber",
            "family": "Cobalt Strike",
            "sources": [("MalwareBazaar", 95, "malicious"), ("VirusTotal cache", 93, "malicious")],
            "tech": ["T1059.001", "T1055"],
            "tags": ["cobalt-strike", "apt29", "demo"],
        },
        {
            "value": "billing@login-office365-secure.net",
            "type": "email",
            "category": "phishing",
            "tlp": "green",
            "sources": [("AlienVault OTX", 64, "suspicious")],
            "tech": ["T1566.002"],
            "tags": ["phishing", "demo"],
        },
        {
            "value": "CVE-2024-3400",
            "type": "cve",
            "category": "vulnerability",
            "tlp": "clear",
            "sources": [("CISA KEV", 99, "malicious")],
            "tech": ["T1190"],
            "tags": ["demo"],
        },
        {
            "value": "45.155.205.233",
            "type": "ip",
            "category": "scanning",
            "tlp": "green",
            "country": "RU",
            "city": "Moscow",
            "lat": 55.75,
            "lon": 37.62,
            "sources": [("AbuseIPDB", 78, "malicious")],
            "tech": ["T1190"],
            "tags": ["demo"],
        },
        {
            "value": "91.219.237.244",
            "type": "ip",
            "category": "c2",
            "tlp": "amber",
            "country": "NL",
            "city": "Amsterdam",
            "lat": 52.37,
            "lon": 4.89,
            "sources": [("ThreatFox", 86, "malicious"), ("Feodo Tracker", 72, "suspicious")],
            "tech": ["T1071.001"],
            "tags": ["c2", "demo"],
        },
        {
            "value": "update-microsoft-cdn.net",
            "type": "domain",
            "category": "c2",
            "tlp": "amber",
            "country": "NL",
            "city": "Amsterdam",
            "lat": 52.37,
            "lon": 4.89,
            "sources": [("AlienVault OTX", 81, "malicious")],
            "tech": ["T1071.001"],
            "tags": ["c2", "cobalt-strike", "demo"],
        },
        {
            "value": "103.27.124.82",
            "type": "ip",
            "category": "malware_host",
            "tlp": "green",
            "country": "SG",
            "city": "Singapore",
            "lat": 1.35,
            "lon": 103.82,
            "sources": [("AbuseIPDB", 55, "suspicious")],
            "tech": ["T1041"],
            "tags": ["demo"],
        },
    ]

    created: dict[str, Indicator] = {}
    for item in iocs:
        value, typ = normalize_value(item["value"], item["type"])
        fp = fingerprint(value, typ)
        last = now - timedelta(minutes=8 if value.startswith("185.220") else 180)
        first = last - timedelta(days=12)
        src_avg = sum(s[1] for s in item["sources"]) / len(item["sources"])
        ind = Indicator(
            value=value,
            type=typ,
            fingerprint=fp,
            confidence=int(src_avg),
            tlp=item["tlp"],
            status="active",
            first_seen=first,
            last_seen=last,
            country=item.get("country"),
            city=item.get("city"),
            lat=item.get("lat"),
            lon=item.get("lon"),
            category=item["category"],
            malware_family=item.get("family"),
            is_demo=True,
        )
        db.add(ind)
        db.flush()
        for name, conf, verdict in item["sources"]:
            db.add(
                IndicatorSource(
                    indicator_id=ind.id,
                    source_name=name,
                    confidence=conf,
                    verdict=verdict,
                    reported_at=last,
                )
            )
        for tn in item.get("tags", []):
            db.add(IndicatorTag(indicator_id=ind.id, tag_id=tags[tn].id))
        for tech in item.get("tech", []):
            db.add(IndicatorTechnique(indicator_id=ind.id, technique_id=tech))
        created[value] = ind

    # relationships for hunting graph
    rels = [
        ("185.220.101.47", "update-microsoft-cdn.net", "communicates"),
        ("update-microsoft-cdn.net", "91.219.237.244", "resolves-to"),
        ("login-office365-secure.net", "https://login-office365-secure.net/owa/auth", "hosts"),
        ("https://login-office365-secure.net/owa/auth", "billing@login-office365-secure.net", "delivers"),
        ("3b5d5c3712955042212316173ccf37be6f1e1da3d0c412747edf362374d33da6", "update-microsoft-cdn.net", "communicates"),
        ("3b5d5c3712955042212316173ccf37be6f1e1da3d0c412747edf362374d33da6", "185.220.101.47", "connects-to"),
    ]
    for a, b, rt in rels:
        if a in created and b in created:
            db.add(IndicatorRelationship(source_id=created[a].id, target_id=created[b].id, rel_type=rt))

    events = [
        ("authentication_success", "vpn-gw-01", "185.220.101.47", "j.okonkwo", created["185.220.101.47"].id, now - timedelta(minutes=22)),
        ("dns_query", "ws-finance-14", "update-microsoft-cdn.net", "m.chen", created["update-microsoft-cdn.net"].id, now - timedelta(hours=3)),
        ("http_post", "ws-finance-14", "185.220.101.47", "m.chen", created["185.220.101.47"].id, now - timedelta(minutes=18)),
        ("email_received", "mx-01", "login-office365-secure.net", "finance", created["login-office365-secure.net"].id, now - timedelta(days=1)),
        ("process_create", "ws-finance-14", "3b5d5c3712955042212316173ccf37be6f1e1da3d0c412747edf362374d33da6", "m.chen", created["3b5d5c3712955042212316173ccf37be6f1e1da3d0c412747edf362374d33da6"].id, now - timedelta(hours=4)),
    ]
    for et, host, val, uname, iid, when in events:
        db.add(
            SecurityEvent(
                event_type=et,
                source_host=host,
                dest_host=val,
                user_name=uname,
                indicator_value=val,
                indicator_id=iid,
                occurred_at=when,
                raw={"demo": True, "host": host},
                is_demo=True,
            )
        )

    for ind in created.values():
        sight = 1 if ind.value in {"185.220.101.47", "update-microsoft-cdn.net"} else 0
        if ind.value == "185.220.101.47":
            sight = 3
        ind.severity_score = compute_severity(
            source_reputation=ind.confidence,
            confidence=ind.confidence,
            last_seen=ind.last_seen,
            internal_sightings=sight,
            indicator_type=ind.type,
            enrichment={
                "malicious_sources": max(1, len(ind.sources) - 0),
                "total_sources": max(1, len(list(ind.sources)) if False else 3),
                "abuse_confidence": ind.confidence,
                "detection_ratio": 0.8 if "hash" in ind.type else 0.2,
            },
        )

    db.add(AlertRule(name="High severity IOC", min_severity=50, enabled=True))
    db.add(AlertRule(name="Critical with internal sighting", min_severity=75, enabled=True))
    db.flush()

    analyst = users["soc_analyst"]
    alerts = []
    for val in ["185.220.101.47", "login-office365-secure.net", "45.155.205.233", "CVE-2024-3400", "3b5d5c3712955042212316173ccf37be6f1e1da3d0c412747edf362374d33da6"]:
        ind = created[val]
        from app.scoring import severity_label

        a = Alert(
            title=f"{severity_label(ind.severity_score).upper()} {ind.type}: {ind.value}",
            severity=severity_label(ind.severity_score),
            status="new" if val == "185.220.101.47" else "acknowledged",
            source="correlation",
            category=ind.category,
            indicator_id=ind.id,
            assignee_id=None if val == "185.220.101.47" else analyst.id,
            is_demo=True,
        )
        db.add(a)
        db.flush()
        alerts.append(a)

    inc = Incident(
        title="Possible Cobalt Strike C2 via Tor exit and finance workstation",
        severity="critical",
        status="open",
        assignee_id=users["incident_responder"].id,
        is_demo=True,
    )
    db.add(inc)
    db.flush()
    db.add(IncidentAlert(incident_id=inc.id, alert_id=alerts[-1].id))
    db.add(IncidentIndicator(incident_id=inc.id, indicator_id=created["3b5d5c3712955042212316173ccf37be6f1e1da3d0c412747edf362374d33da6"].id))
    db.add(
        IncidentTimeline(
            incident_id=inc.id,
            event_type="incident_creation",
            message="Incident opened from malware hash correlation on ws-finance-14",
            actor_id=users["incident_responder"].id,
        )
    )
    for label in [
        "Validate indicator",
        "Identify affected assets",
        "Review internal sightings",
        "Investigate related infrastructure",
        "Document evidence",
        "Escalate if required",
        "Close incident",
    ]:
        db.add(ContainmentItem(incident_id=inc.id, label=label, done=label.startswith("Validate")))

    db.add(
        SavedHunt(
            owner_id=users["threat_hunter"].id,
            name="Cobalt Strike C2 pivot",
            description="Beacon hashes communicating with suspicious domains",
            query={"q": "cobalt", "type": "domain", "technique": "T1071.001"},
            tags=["cobalt-strike", "c2"],
        )
    )
    db.commit()
