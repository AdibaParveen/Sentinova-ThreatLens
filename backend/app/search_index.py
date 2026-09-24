"""Best-effort OpenSearch indexing. PostgreSQL remains the source of truth."""

from __future__ import annotations

from app.config import get_settings
from app.models import Indicator

INDEX = "threatlens-indicators"
settings = get_settings()


def _client():
    try:
        from opensearchpy import OpenSearch

        return OpenSearch(settings.elasticsearch_url, timeout=3, max_retries=1)
    except Exception:
        return None


def index_indicator(ind: Indicator) -> None:
    client = _client()
    if not client:
        return
    try:
        client.index(
            index=INDEX,
            id=str(ind.id),
            body={
                "value": ind.value,
                "type": ind.type,
                "severity_score": ind.severity_score,
                "status": ind.status,
                "category": ind.category,
                "tlp": ind.tlp,
                "country": ind.country,
            },
            refresh=False,
        )
    except Exception:
        return


def search_indicators(q: str, size: int = 15) -> list[str]:
    client = _client()
    if not client or not q:
        return []
    try:
        res = client.search(
            index=INDEX,
            body={"query": {"multi_match": {"query": q, "fields": ["value^3", "category", "type"]}}, "size": size},
        )
        return [hit["_id"] for hit in res.get("hits", {}).get("hits", [])]
    except Exception:
        return []
