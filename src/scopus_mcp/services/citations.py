from .provenance import with_provenance
from datetime import datetime, timezone
from .validation import identifier

from ..client import ScopusClient
from ..formatters import format_citation_count, format_citations_overview

CITATIONS_INST_NOTE = (
    "Elsevier denied citation endpoint access. Check your API key and endpoint entitlement "
    "with scopus check; an institutional token (SCOPUS_INST_TOKEN) or approved network may be required. "
    "Tip: the cited_by_count field in scopus_search and scopus_get_abstract "
    "may provide citation totals if your search or abstract entitlement allows it."
)


async def do_get_citation_count(
    client: ScopusClient,
    scopus_id: str | None = None,
    doi: str | None = None,
) -> dict:
    if bool(scopus_id) == bool(doi):
        raise ValueError("Provide exactly one of: scopus_id or doi.")

    params: dict = {}
    if scopus_id:
        params["scopus_id"] = identifier(scopus_id, "scopus_id")
    elif doi:
        params["doi"] = identifier(doi, "doi")

    raw = await client.request("/content/abstract/citation-count", params=params)
    return with_provenance(format_citation_count(raw), client)


async def do_get_citations_overview(
    client: ScopusClient,
    scopus_id: str,
    start_year: int = 2000,
    end_year: int | None = None,
) -> dict:
    current_year = datetime.now(timezone.utc).year
    end_year = current_year if end_year is None else end_year
    if start_year < 1960 or end_year > current_year:
        raise ValueError("Citation years must be between 1960 and the current year.")
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year.")

    raw = await client.request(
        "/content/abstract/citations",
        params={
            "scopus_id": identifier(scopus_id, "scopus_id"),
            "date": f"{start_year}-{end_year}",
            "httpAccept": "application/json",
        },
    )
    return with_provenance(format_citations_overview(raw), client)

