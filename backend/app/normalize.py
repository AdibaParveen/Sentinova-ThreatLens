"""Canonical IOC normalization and deterministic fingerprinting for deduplication."""

from __future__ import annotations


import hashlib
import ipaddress
import re
from urllib.parse import urlparse, urlunparse

IOC_TYPES = ("ip", "domain", "url", "hash_md5", "hash_sha1", "hash_sha256", "email", "cve")

MD5_RE = re.compile(r"^[a-fA-F0-9]{32}$")
SHA1_RE = re.compile(r"^[a-fA-F0-9]{40}$")
SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.I)
DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})+$")


def detect_type(value: str) -> str | None:
    v = value.strip()
    if not v:
        return None
    try:
        ipaddress.ip_address(v)
        return "ip"
    except ValueError:
        pass
    if CVE_RE.match(v):
        return "cve"
    if MD5_RE.match(v):
        return "hash_md5"
    if SHA1_RE.match(v):
        return "hash_sha1"
    if SHA256_RE.match(v):
        return "hash_sha256"
    if EMAIL_RE.match(v):
        return "email"
    if v.lower().startswith(("http://", "https://")):
        return "url"
    if DOMAIN_RE.match(v):
        return "domain"
    return None


def normalize_value(value: str, ioc_type: str | None = None) -> tuple[str, str]:
    raw = value.strip()

# DNS fully-qualified domain names may end with a trailing dot.
# Remove it before IOC type detection.
    detection_value = raw.rstrip(".")

    detected = ioc_type or detect_type(detection_value)
    if not detected:
        raise ValueError("Unable to determine indicator type")
    if detected == "ip":
        ip = ipaddress.ip_address(raw)
        return str(ip), "ip"
    if detected == "domain":
        return raw.lower().rstrip("."), "domain"
    if detected == "url":
        parsed = urlparse(raw)
        scheme = (parsed.scheme or "http").lower()
        netloc = parsed.netloc.lower()
        path = parsed.path or "/"
        # Drop fragments; keep query (often part of phishing URLs)
        canon = urlunparse((scheme, netloc, path, "", parsed.query, ""))
        return canon, "url"
    if detected.startswith("hash_"):
        return raw.lower(), detected
    if detected == "email":
        return raw.lower(), "email"
    if detected == "cve":
        return raw.upper(), "cve"
    return raw, detected


def fingerprint(value: str, ioc_type: str) -> str:
    canon, typ = normalize_value(value, ioc_type)
    payload = f"{typ}|{canon}".encode()
    return hashlib.sha256(payload).hexdigest()
