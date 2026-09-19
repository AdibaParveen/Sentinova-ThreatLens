from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import get_settings

settings = get_settings()


def generate_triage(detail: dict[str, Any]) -> dict[str, Any]:
    """Evidence-bound triage summary. Does not invent intelligence."""
    sources = detail.get("sources") or []
    events = detail.get("internal_events") or []
    attack = detail.get("attack") or []
    enrich = detail.get("enrichment") or {}
    used = []
    if sources:
        used.append("indicator_sources")
    if events:
        used.append("security_events")
    if attack:
        used.append("attack_techniques")
    if enrich:
        used.append("enrichment")
    used.append("severity_score")

    malicious = sum(1 for s in sources if s.get("verdict") == "malicious")
    total = len(sources)
    why = []
    if total:
        why.append(f"This {detail.get('type')} has been reported by {total} threat intelligence source(s)")
        if malicious:
            why.append(f"{malicious}/{total} sources classified it as malicious")
        else:
            why.append("Insufficient evidence available for a majority-malicious consensus.")
    else:
        why.append("Insufficient evidence available from reporting sources.")
    if events:
        why.append(f"It has {len(events)} internal sighting(s) in security telemetry.")
    else:
        why.append("No confirmed internal sightings are present in current telemetry.")
    if attack:
        why.append("Mapped ATT&CK techniques: " + ", ".join(f"{t['id']} ({t['name']})" for t in attack))
    else:
        why.append("Insufficient evidence available for ATT&CK mapping.")

    steps = [
        "Validate the indicator value against original feed provenance.",
        "Review internal sightings and affected assets.",
        "Pivot through related infrastructure in Threat Hunting.",
    ]
    if events:
        steps.append("Interview or inspect hosts listed in internal correlation events.")
    else:
        steps.append("Search SIEM/EDR independently; platform telemetry currently shows no match.")

    local = {
        "why": " ".join(why),
        "evidence": {
            "sources_malicious": f"{malicious}/{total}" if total else "Insufficient evidence available.",
            "abuse_confidence": enrich.get("abuse_confidence", "Insufficient evidence available."),
            "severity": f"{detail.get('severity_score')}/100",
            "internal_sightings": len(events),
            "attack": [t["id"] for t in attack] or "Insufficient evidence available.",
        },
        "steps": steps,
        "data_used": used,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "AI-generated — verify against source evidence",
    }

    if settings.ai_api_key:
        prompt = (
            "You are a SOC analyst assistant. Use ONLY the JSON evidence. "
            "If a field is missing say 'Insufficient evidence available.' Do not invent IOCs, actors, or events.\n"
            + str({k: detail.get(k) for k in ("value", "type", "severity_score", "confidence", "sources", "internal_events", "attack", "enrichment")})
        )
        try:
            with httpx.Client(timeout=20) as client:
                r = client.post(
                    f"{settings.ai_api_base}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.ai_api_key}"},
                    json={
                        "model": settings.ai_model,
                        "messages": [
                            {"role": "system", "content": "Return concise analyst prose. No invented intelligence."},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.1,
                    },
                )
                if r.status_code == 200:
                    local["why"] = r.json()["choices"][0]["message"]["content"]
                    local["model"] = settings.ai_model
        except Exception:
            local["model"] = "deterministic-evidence-summarizer"
    else:
        local["model"] = "deterministic-evidence-summarizer"
    return local
