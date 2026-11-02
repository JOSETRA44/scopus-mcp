"""Flat, tabular projections of the nested dicts the tools layer returns.

Every command produces two things: ``data`` (the full nested payload, what the
MCP server hands an LLM) and ``rows`` (this module's output — the flat list that
feeds ``table``/``csv``/``md``/``jsonl`` and the envelope's ``rows`` key).

Each projector emits a *fixed* set of keys so a CSV header stays stable whether
the harvest is buffered or streamed row by row.
"""

from __future__ import annotations

from typing import Any, Callable

Row = dict[str, Any]


def _pick(source: dict, fields: list[str]) -> Row:
    return {f: source.get(f) for f in fields}


# ── Per-row projectors (also used by the streaming `--all` path) ────────────

PAPER_FIELDS = [
    "scopus_id",
    "title",
    "first_author",
    "publication",
    "year",
    "cited_by_count",
    "doi",
    "open_access",
]


def project_paper(paper: dict) -> Row:
    row = _pick(paper, PAPER_FIELDS)
    row["year"] = (paper.get("cover_date") or "")[:4] or None
    row["open_access"] = paper.get("open_access")
    count = paper.get("cited_by_count")
    row["cited_by_count"] = int(count) if count is not None else None
    return row


AUTHOR_ROW_FIELDS = [
    "author_id",
    "name",
    "affiliation",
    "country",
    "document_count",
    "orcid",
]


def project_author(author: dict) -> Row:
    return _pick(author, AUTHOR_ROW_FIELDS)


AFFILIATION_ROW_FIELDS = [
    "affiliation_id",
    "name",
    "city",
    "country",
    "document_count",
]


def project_affiliation(affiliation: dict) -> Row:
    return _pick(affiliation, AFFILIATION_ROW_FIELDS)


# ── Whole-result projectors ────────────────────────────────────────────────

ABSTRACT_FIELDS = [
    "scopus_id",
    "title",
    "publication",
    "cover_date",
    "cited_by_count",
    "doi",
    "open_access",
    "authors",
    "keywords",
]


def rows_abstract(result: dict) -> list[Row]:
    row = _pick(result, ABSTRACT_FIELDS)
    row["authors"] = "; ".join(a.get("name", "") for a in result.get("authors") or [])
    row["keywords"] = "; ".join(result.get("keywords") or [])
    return [row]


AUTHOR_PROFILE_FIELDS = [
    "author_id",
    "name",
    "h_index",
    "document_count",
    "cited_by_count",
    "institution",
    "country",
    "orcid",
]


def rows_author(result: dict) -> list[Row]:
    row = _pick(result, AUTHOR_PROFILE_FIELDS)
    affiliation = result.get("affiliation") or {}
    row["institution"] = affiliation.get("institution")
    row["country"] = affiliation.get("country")
    return [row]


CITATION_COUNT_FIELDS = ["scopus_id", "doi", "cited_by_count", "self_citation_count"]


def rows_citation_count(result: dict) -> list[Row]:
    return [_pick(result, CITATION_COUNT_FIELDS)]


CITATIONS_FIELDS = ["year", "citations"]


def rows_citations(result: dict) -> list[Row]:
    return [
        {"year": year, "citations": count}
        for year, count in (result.get("citations_by_year") or {}).items()
    ]


CHECK_FIELDS = ["capability", "status"]


def rows_check(result: dict) -> list[Row]:
    return [
        {"capability": name, "status": status}
        for name, status in (result.get("capabilities") or {}).items()
    ]


CACHE_FIELDS = ["key", "value"]


def rows_cache(result: dict) -> list[Row]:
    return [{"key": k, "value": v} for k, v in result.items()]


def _listing(key: str, projector: Callable[[dict], Row]) -> Callable[[dict], list[Row]]:
    def rows_from(result: dict) -> list[Row]:
        return [projector(item) for item in result.get(key) or []]

    return rows_from


rows_search = _listing("papers", project_paper)
rows_search_authors = _listing("authors", project_author)
rows_search_affiliations = _listing("affiliations", project_affiliation)


# ── Envelope meta ──────────────────────────────────────────────────────────

def search_meta(result: dict) -> dict[str, Any]:
    """Pagination facts Scopus reports alongside a result page."""
    return {
        "query": result.get("query"),
        "total_results": result.get("total_results"),
        "start_index": result.get("start_index"),
        "items_per_page": result.get("items_per_page"),
        "next_start": result.get("next_start"),
        "truncated": result.get("truncated"),
        "stop_reason": result.get("stop_reason"),
    }


def total_meta(result: dict) -> dict[str, Any]:
    return search_meta(result)


def no_meta(result: dict) -> dict[str, Any]:
    return {}
