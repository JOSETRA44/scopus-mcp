from .provenance import with_provenance
from typing import Any, AsyncIterator, Callable

from ..client import ScopusClient
from ..formatters import (
    format_affiliation_search_results,
    format_author_search_results,
    format_search_results,
)
from .validation import search_input

AUTHOR_SEARCH_INST_NOTE = (
    "Elsevier denied author search access. Check your API key and endpoint entitlement "
    "with scopus check; an institutional token (SCOPUS_INST_TOKEN) or approved network may be required."
)
AFFILIATION_SEARCH_INST_NOTE = (
    "Elsevier denied affiliation search access. Check your API key and endpoint entitlement "
    "with scopus check; an institutional token (SCOPUS_INST_TOKEN) or approved network may be required."
)

# Conservative offset limits used by this client. Larger/cursor harvests need
# a separate entitlement-aware strategy; these are not universal API limits.
PAGE_MAX = 25
OFFSET_MAX = 5000


def _page_metadata(page: dict, start: int) -> dict:
    page["start_index"] = start
    next_start = start + page["showing"]
    more = next_start < page["total_results"]
    page["next_start"] = next_start if more and next_start < OFFSET_MAX and page["showing"] else None
    page["truncated"] = more
    page["complete_corpus"] = start == 0 and page["showing"] == page["total_results"]
    page["stop_reason"] = ("offset_limit" if next_start >= OFFSET_MAX else "page_limit") if more else "complete"
    if more and not page["showing"]:
        page["stop_reason"] = "empty_page"
    return page


async def do_scopus_search(
    client: ScopusClient,
    query: str,
    count: int = 10,
    start: int = 0,
    view: str = "STANDARD",
) -> dict:
    query = search_input(query, count, start, view)
    raw = await client.request(
        "/content/search/scopus",
        params={"query": query, "count": count, "start": start, "view": view},
    )
    return with_provenance(_page_metadata(format_search_results(raw, query=query), start), client)


async def do_scopus_search_authors(client: ScopusClient, query: str, count: int = 10, start: int = 0) -> dict:
    query = search_input(query, count, start)
    raw = await client.request(
        "/content/search/author",
        params={"query": query, "count": count, "start": start},
    )
    return with_provenance(_page_metadata(format_author_search_results(raw, query=query), start), client)


async def do_scopus_search_affiliations(client: ScopusClient, query: str, count: int = 10, start: int = 0) -> dict:
    query = search_input(query, count, start)
    raw = await client.request(
        "/content/search/affiliation",
        params={"query": query, "count": count, "start": start},
    )
    return with_provenance(_page_metadata(format_affiliation_search_results(raw, query=query), start), client)


async def _paginate(
    client: ScopusClient,
    path: str,
    query: str,
    formatter: Callable[..., dict],
    rows_key: str,
    id_key: str,
    max_rows: int,
    start: int = 0,
    extra_params: dict[str, Any] | None = None,
    on_page: Callable[[int, int], None] | None = None,
    harvest: dict | None = None,
) -> AsyncIterator[dict]:
    """Walk a Scopus offset-paginated endpoint, yielding one row at a time.

    Shared by every `--all` capable search command. Deduplicates on ``id_key``
    because Scopus can shift a result between pages while a harvest is running.
    """
    query = search_input(query, 1, start, (extra_params or {}).get("view", "STANDARD"))
    if max_rows < 1:
        raise ValueError("max_rows must be positive.")
    total = 0
    seen: set[str] = set()
    duplicates = 0
    retrieval_times: set[str] = set()
    emitted = 0
    offset = start
    while emitted < max_rows and offset < OFFSET_MAX:
        count = min(PAGE_MAX, max_rows - emitted, OFFSET_MAX - offset)
        params: dict[str, Any] = {"query": query, "count": count, "start": offset}
        if extra_params:
            params.update(extra_params)
        page = formatter(await client.request(path, params=params), query=query)
        page_retrieved_at = getattr(client, "retrieved_at", None)
        if page_retrieved_at:
            retrieval_times.add(page_retrieved_at)
        rows = page.get(rows_key, [])
        total = int(page.get("total_results", 0))
        if not rows:
            break
        for row in rows:
            ident = str(row.get(id_key, ""))
            if ident and ident in seen:
                duplicates += 1
                continue
            if ident:
                seen.add(ident)
            row["retrieved_at"] = page_retrieved_at
            row["source"] = "scopus"
            yield row
            emitted += 1
            if emitted >= max_rows:
                break
        offset += len(rows)
        if on_page is not None:
            on_page(emitted, total)
        if total and offset >= total:
            break

    if harvest is not None:
        truncated = offset < total
        reason = "complete"
        if truncated:
            reason = "offset_limit" if offset >= OFFSET_MAX else "max_rows" if emitted >= max_rows else "empty_page"
        harvest.update(total_results=total, truncated=truncated, stop_reason=reason,
                       next_start=offset if truncated and offset < OFFSET_MAX else None,
                       start_index=start, duplicate_count=duplicates,
                       complete_corpus=start == 0 and emitted == total and not truncated,
                       retrieval_times=sorted(retrieval_times))


def iter_scopus_search(
    client: ScopusClient,
    query: str,
    max_rows: int = 1000,
    start: int = 0,
    view: str = "STANDARD",
    on_page: Callable[[int, int], None] | None = None,
    harvest: dict | None = None,
) -> AsyncIterator[dict]:
    """Stream every paper matching ``query``, up to ``max_rows``."""
    return _paginate(
        client,
        "/content/search/scopus",
        query,
        format_search_results,
        rows_key="papers",
        id_key="scopus_id",
        max_rows=max_rows,
        start=start,
        extra_params={"view": view},
        on_page=on_page,
        harvest=harvest,
    )


def iter_scopus_search_authors(
    client: ScopusClient,
    query: str,
    max_rows: int = 1000,
    start: int = 0,
    on_page: Callable[[int, int], None] | None = None,
    harvest: dict | None = None,
) -> AsyncIterator[dict]:
    """Stream every author profile matching ``query``, up to ``max_rows``."""
    return _paginate(
        client,
        "/content/search/author",
        query,
        format_author_search_results,
        rows_key="authors",
        id_key="author_id",
        max_rows=max_rows,
        start=start,
        on_page=on_page,
        harvest=harvest,
    )


def iter_scopus_search_affiliations(
    client: ScopusClient,
    query: str,
    max_rows: int = 1000,
    start: int = 0,
    on_page: Callable[[int, int], None] | None = None,
    harvest: dict | None = None,
) -> AsyncIterator[dict]:
    """Stream every affiliation record matching ``query``, up to ``max_rows``."""
    return _paginate(
        client,
        "/content/search/affiliation",
        query,
        format_affiliation_search_results,
        rows_key="affiliations",
        id_key="affiliation_id",
        max_rows=max_rows,
        start=start,
        on_page=on_page,
        harvest=harvest,
    )

