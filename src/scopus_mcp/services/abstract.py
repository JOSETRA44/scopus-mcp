from .provenance import with_provenance
import asyncio
import urllib.parse
from typing import Literal

from ..client import ScopusClient
from ..exceptions import ScopusAPIError, ScopusAuthError
from ..formatters import format_abstract
from .validation import identifier as validate_identifier

IdentifierType = Literal["scopus_id", "doi", "eid", "pubmed_id"]

ABSTRACT_ACCESS_NOTE = (
    "Returned metadata only (view=META). Abstract text, full author list, "
    "and keywords depend on your Elsevier access entitlement. "
    "Use scopus check to inspect endpoint access; an institutional token (SCOPUS_INST_TOKEN) may be required."
)


def _abstract_path(identifier_type: IdentifierType, identifier: str) -> str:
    clean = validate_identifier(identifier, identifier_type)

    path_map: dict[str, str] = {
        "scopus_id": f"/content/abstract/scopus_id/{clean}",
        "doi": f"/content/abstract/doi/{urllib.parse.quote(clean, safe='')}",
        "eid": f"/content/abstract/eid/{clean}",
        "pubmed_id": f"/content/abstract/pubmed_id/{clean}",
    }
    return path_map[identifier_type]


async def do_get_abstract(client: ScopusClient, identifier_type: IdentifierType, identifier: str) -> dict:
    """Fetch abstract details, falling back FULL -> META on access denial."""
    path = _abstract_path(identifier_type, identifier)
    try:
        raw = await client.request(path, params={"view": "FULL"})
        return with_provenance(format_abstract(raw), client)
    except ScopusAuthError as exc:
        if exc.status_code == 401:
            raise
        # Metadata access may be available even when FULL access is denied.
        raw = await client.request(path, params={"view": "META"})
        result = format_abstract(raw)
        result["access_note"] = ABSTRACT_ACCESS_NOTE
        return with_provenance(result, client)


async def do_get_abstracts(
    client: ScopusClient, identifier_type: IdentifierType, identifiers: list[str],
    concurrency: int = 3,
) -> dict:
    """Fetch a bounded batch, retaining input order and per-record failures."""
    if not 1 <= len(identifiers) <= 25:
        raise ValueError("Provide between 1 and 25 identifiers.")
    if not 1 <= concurrency <= 5:
        raise ValueError("concurrency must be between 1 and 5.")
    semaphore = asyncio.Semaphore(concurrency)

    async def fetch(value: str) -> dict:
        async with semaphore:
            try:
                data = await do_get_abstract(client, identifier_type, value)
                return {"identifier": value, "ok": True, "data": data}
            except (ScopusAPIError, ValueError) as exc:
                return {"identifier": value, "ok": False, "error": str(exc)}

    results = await asyncio.gather(*(fetch(value) for value in identifiers))
    succeeded = sum(item["ok"] for item in results)
    return {"results": results, "succeeded": succeeded, "failed": len(results) - succeeded}

