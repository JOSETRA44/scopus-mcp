"""Bounded citation exploration and descriptive corpus analysis.

Upstream contracts:
https://dev.elsevier.com/documentation/AbstractRetrievalAPI.wadl
https://dev.elsevier.com/payloads/retrieval/abstractRetrievalResp.json
https://dev.elsevier.com/sc_abstract_retrieval_views.html
REFEID is access-controlled: https://dev.elsevier.com/release_notes.html
"""
from collections import Counter
from datetime import datetime, timezone
import re
from typing import Any

from ..client import ScopusClient
from ..exceptions import ScopusAPIError
from .abstract import IdentifierType, _abstract_path
from .search import do_scopus_search, iter_scopus_search
from .validation import identifier as validate_identifier


def _get(value: Any, *keys: str) -> Any:
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _text(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("$")
    if value is None or isinstance(value, (dict, list)):
        return None
    return str(value).strip() or None


def _list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return value
    raise ScopusAPIError("Scopus returned malformed reference metadata.")


def _total(value: Any) -> int | None:
    if value is None:
        return None
    try:
        result = int(value)
        if result < 0:
            raise ValueError
        return result
    except (TypeError, ValueError) as exc:
        raise ScopusAPIError("Scopus returned an invalid reference count.") from exc


def _reference(entry: dict) -> dict:
    if not isinstance(entry, dict):
        raise ScopusAPIError("Scopus returned a malformed reference entry.")
    info = entry.get("ref-info", entry)
    if not isinstance(info, dict):
        raise ScopusAPIError("Scopus returned malformed ref-info.")
    identifiers = {}
    for item in _list(_get(info, "refd-itemidlist", "itemid")):
        if isinstance(item, dict) and item.get("@idtype"):
            identifiers[str(item["@idtype"]).upper()] = _text(item)
    title = _text(_get(info, "ref-title", "ref-titletext")) or _text(info.get("title"))
    names = []
    for author in _list(_get(info, "ref-authors", "author") or _get(info, "author-list", "author")):
        if not isinstance(author, dict):
            continue
        name = _text(author.get("ce:indexed-name")) or ", ".join(filter(None, [
            _text(author.get("ce:surname")),
            _text(author.get("ce:given-name")) or _text(author.get("ce:initials")),
        ]))
        if name and name not in names:
            names.append(name)
    result = {
        "position": _text(entry.get("@id")),
        "scopus_id": _text(info.get("scopus-id")) or identifiers.get("SGR"),
        "doi": _text(info.get("ce:doi")) or identifiers.get("DOI"),
        "title": title,
        "authors": names,
        "publication": _text(info.get("ref-sourcetitle")) or _text(info.get("sourcetitle")),
        "publication_year": _text(_get(info, "ref-publicationyear", "@first")),
        "cover_date": _text(info.get("prism:coverDate")),
        "text": _text(entry.get("ref-fulltext")) or _text(info.get("ref-text")),
        "resolution_status": _text(info.get("type")),
    }
    if not any(result[k] for k in ("scopus_id", "doi", "title", "publication", "authors", "text")):
        raise ScopusAPIError("Scopus returned a reference without usable bibliographic metadata.")
    return result


def _container(raw: dict) -> tuple[dict | None, str]:
    root = raw.get("abstracts-retrieval-response")
    if not isinstance(root, dict):
        raise ScopusAPIError("Scopus returned no abstract record for reference retrieval.")
    if isinstance(root.get("references"), dict):
        return root["references"], "REF"
    bibliography = _get(root, "item", "bibrecord", "tail", "bibliography")
    return (bibliography, "FULL") if isinstance(bibliography, dict) else (None, "REF")


async def do_get_references(
    client: ScopusClient, identifier: str, identifier_type: IdentifierType = "scopus_id",
    count: int = 25, start: int = 0,
) -> dict:
    """One page of references; unavailable metadata is never an empty bibliography."""
    if not 1 <= count <= 100 or start < 0:
        raise ValueError("Reference count must be 1–100 and start must be nonnegative.")
    path = _abstract_path(identifier_type, identifier)
    raw = await client.request(path, {"view": "REF", "refcount": count, "startref": start})
    container, view = _container(raw)
    if container is None:
        # FULL can contain the original bibliography when resolved REF data is
        # absent. Authentication failures are intentionally not retried here.
        raw = await client.request(path, {"view": "FULL"})
        container, view = _container(raw)
    if container is None:
        raise ScopusAPIError("Reference metadata is unavailable for this record or entitlement; this does not mean the paper has no references.")
    total = _total(container.get("@total-references", container.get("@refcount")))
    entries = _list(container.get("reference"))
    if not entries and total != 0 and (total is None or start < total):
        raise ScopusAPIError("Scopus reported no reference entries, but did not confirm an empty bibliography. Access or resolution may be incomplete.")
    if view == "FULL":
        entries = entries[start:start + count]
    elif len(entries) > count:
        entries = entries[:count]
    references = [_reference(entry) for entry in entries]
    next_offset = start + len(references)
    truncated = next_offset < total if total is not None else None
    return {
        "identifier": validate_identifier(identifier, identifier_type), "identifier_type": identifier_type,
        "references": references, "showing": len(references), "total_references": total,
        "start_index": start,
        "next_start": next_offset if references and (truncated or total is None) else None,
        "truncated": truncated, "view": view, "source": "scopus",
        "retrieved_at": getattr(client, "retrieved_at", None),
        "limitations": ["Only references exposed by Elsevier for this record and access entitlement are returned. Unresolved references may lack identifiers or titles.",
                         "A null total or truncated value means completeness is unknown."],
    }


async def do_get_citing_documents(client: ScopusClient, scopus_id: str, count: int = 10, start: int = 0) -> dict:
    clean = validate_identifier(scopus_id, "scopus_id")
    result = await do_scopus_search(client, f"REFEID(2-s2.0-{clean})", count=count, start=start)
    result.update(source="scopus", cited_scopus_id=clean, retrieved_at=getattr(client, "retrieved_at", None),
                  limitations=["REFEID requires an Elsevier entitlement; an API key alone may not permit this search.",
                               "Results describe citations indexed by Scopus, not every citation worldwide."])
    return result


async def do_analyze_results(client: ScopusClient, query: str, max_rows: int = 100, start: int = 0,
                             view: str = "STANDARD") -> dict:
    if not 1 <= max_rows <= 5000:
        raise ValueError("max_rows must be between 1 and 5000.")
    year_counts: Counter[str] = Counter()
    publication_counts: Counter[str] = Counter()
    affiliation_counts: Counter[str] = Counter()
    affiliation_names: dict[str, str | None] = {}
    unknown = {"year": 0, "publication": 0, "affiliation": 0}
    harvest: dict = {}
    count = 0
    started_at = datetime.now(timezone.utc).isoformat()
    async for paper in iter_scopus_search(client, query, max_rows=max_rows, start=start, view=view, harvest=harvest):
        count += 1
        date = str(paper.get("cover_date") or "")
        year = date[:4] if re.match(r"^\d{4}(?:-|$)", date) else None
        if year:
            year_counts[year] += 1
        else:
            unknown["year"] += 1
        publication = _text(paper.get("publication"))
        if publication:
            publication_counts[publication] += 1
        else:
            unknown["publication"] += 1
        affiliations = set()
        for affiliation in paper.get("affiliations") or []:
            if not isinstance(affiliation, dict):
                continue
            name = _text(affiliation.get("name"))
            ident = _text(affiliation.get("affiliation_id"))
            key = f"id:{ident}" if ident else f"name:{name}" if name else None
            if key:
                affiliations.add(key)
                affiliation_names[key] = name
        if not affiliations:
            unknown["affiliation"] += 1
        affiliation_counts.update(affiliations)
    return {
        "query": query.strip(), "source": "scopus", "view": view,
        "corpus_size": count, "requested_max_rows": max_rows, **harvest,
        "by_year": dict(sorted(year_counts.items())),
        "by_publication": dict(publication_counts.most_common()),
        "by_affiliation": [{"key": key, "name": affiliation_names[key], "documents": n}
                           for key, n in affiliation_counts.most_common()],
        "unknown": unknown,
        "started_at": started_at, "completed_at": datetime.now(timezone.utc).isoformat(),
        "retrieved_at": min(harvest["retrieval_times"]) if harvest.get("retrieval_times") else None,
        "limitations": [
            "Descriptive counts apply only to the retrieved corpus, in API result order; a truncated corpus is not a random sample or a global estimate.",
            "Year uses cover_date and publication groups exact source-title strings, including non-journal sources.",
            "Affiliations count each distinct institution once per document. One paper may count toward multiple institutions; unknown counts mark papers without usable affiliation metadata.",
            "STANDARD and COMPLETE views expose different metadata according to entitlement. Missing metadata is unknown, not zero activity.",
        ],
    }
