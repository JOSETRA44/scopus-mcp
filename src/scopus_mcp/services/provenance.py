"""Attach retrieval provenance immediately after a request completes."""
from datetime import datetime, timezone

from ..client import ScopusClient


def with_provenance(result: dict, client: ScopusClient) -> dict:
    # Missing timestamps from third-party cache backends stay unknown.
    result["retrieved_at"] = getattr(client, "retrieved_at", None)
    result["served_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result["source"] = "scopus"
    if "total_results" in result:
        for key in ("papers", "authors", "affiliations"):
            for record in result.get(key, []):
                record["retrieved_at"] = result["retrieved_at"]
                record["source"] = "scopus"
    return result
