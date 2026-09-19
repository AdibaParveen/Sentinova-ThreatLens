ROLES = (
    "administrator",
    "security_engineer",
    "incident_responder",
    "threat_hunter",
    "soc_analyst",
    "executive",
)

# Privilege roles that may enable TOTP MFA (optional but supported).
PRIVILEGED_ROLES = {"administrator", "security_engineer"}

PERMISSIONS = {
    "dashboards.view": set(ROLES),
    "dashboards.executive": {
        "administrator",
        "security_engineer",
        "executive",
        "incident_responder",
        "soc_analyst",
        "threat_hunter",
    },
    "dashboards.soc": {
        "administrator",
        "security_engineer",
        "incident_responder",
        "threat_hunter",
        "soc_analyst",
    },
    "dashboards.incidents": {
        "administrator",
        "incident_responder",
        "soc_analyst",
        "threat_hunter",
        "security_engineer",
    },
    "dashboards.hunting": {
        "administrator",
        "threat_hunter",
        "security_engineer",
        "incident_responder",
        "soc_analyst",
    },
    "intelligence.search": {
        "administrator",
        "security_engineer",
        "incident_responder",
        "threat_hunter",
        "soc_analyst",
    },
    "indicators.read": {
        "administrator",
        "security_engineer",
        "incident_responder",
        "threat_hunter",
        "soc_analyst",
    },
    "indicators.write": {
        "administrator",
        "security_engineer",
        "incident_responder",
        "soc_analyst",
    },
    "indicators.enrich": {
        "administrator",
        "security_engineer",
        "incident_responder",
        "soc_analyst",
        "threat_hunter",
    },
    "indicators.tag": {
        "administrator",
        "security_engineer",
        "incident_responder",
        "soc_analyst",
        "threat_hunter",
    },
    "alerts.read": {
        "administrator",
        "security_engineer",
        "incident_responder",
        "threat_hunter",
        "soc_analyst",
    },
    "alerts.manage": {
        "administrator",
        "incident_responder",
        "soc_analyst",
    },
    "alerts.limited": {"security_engineer", "threat_hunter"},
    "incidents.read": {
        "administrator",
        "incident_responder",
        "soc_analyst",
        "threat_hunter",
        "security_engineer",
    },
    "incidents.manage": {"administrator", "incident_responder"},
    "incidents.escalate": {"administrator", "incident_responder", "soc_analyst"},
    "hunts.manage": {
        "administrator",
        "security_engineer",
        "incident_responder",
        "threat_hunter",
    },
    "reports.generate": set(ROLES),
    "feeds.manage": {"administrator", "security_engineer"},
    "integrations.manage": {"administrator", "security_engineer"},
    "users.manage": {"administrator"},
    "audit.view": {"administrator", "security_engineer", "incident_responder"},
    "audit.full": {"administrator"},
    "health.view": {"administrator", "security_engineer"},
    "settings.platform": {"administrator"},
    "export.intelligence": {
        "administrator",
        "security_engineer",
        "incident_responder",
        "threat_hunter",
    },
}

NAV_ITEMS = [
    {"id": "overview", "label": "Overview", "href": "/overview", "perm": "dashboards.executive"},
    {"id": "soc", "label": "SOC Analyst", "href": "/soc", "perm": "dashboards.soc"},
    {"id": "incidents", "label": "Incidents", "href": "/incidents", "perm": "dashboards.incidents"},
    {"id": "hunting", "label": "Threat Hunting", "href": "/hunting", "perm": "dashboards.hunting"},
    {"id": "indicators", "label": "Indicators", "href": "/indicators", "perm": "indicators.read"},
    {"id": "alerts", "label": "Alerts", "href": "/alerts", "perm": "alerts.read"},
    {"id": "intel", "label": "Threat Intelligence", "href": "/intel", "perm": "indicators.read"},
    {"id": "map", "label": "Threat Map", "href": "/map", "perm": "dashboards.view"},
    {"id": "reports", "label": "Reports", "href": "/reports", "perm": "reports.generate"},
    {"id": "integrations", "label": "Integrations", "href": "/integrations", "perm": "integrations.manage"},
    {"id": "feeds", "label": "Feeds", "href": "feeds", "perm": "feeds.manage"},
    {"id": "audit", "label": "Audit Logs", "href": "/audit", "perm": "audit.view"},
    {"id": "health", "label": "System Health", "href": "/health", "perm": "health.view"},
    {"id": "settings", "label": "Settings", "href": "/settings/profile", "perm": "dashboards.view"},
]


def has_permission(role: str, permission: str) -> bool:
    allowed = PERMISSIONS.get(permission)
    if not allowed:
        return False
    return role in allowed


def navigation_for(role: str) -> list[dict]:
    items = []
    for item in NAV_ITEMS:
        href = item["href"]
        if href == "feeds":
            href = "/feeds"
        if has_permission(role, item["perm"]):
            items.append({**item, "href": href})
    return items
