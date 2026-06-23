"""
Pure functions that transform raw Scopus API JSON into clean, AI-friendly dicts.
No side effects, no network calls — fully unit-testable with fixture data.
"""

from typing import Any


def _safe_get(obj: Any, *keys: str | int, default: Any = None) -> Any:
    """Safely traverse nested dicts/lists without raising KeyError/TypeError."""
    for key in keys:
        try:
            obj = obj[key]
        except (KeyError, IndexError, TypeError):
            return default
    return obj if obj is not None else default


def _strip_scopus_id(raw_id: str) -> str:
    """Convert 'SCOPUS_ID:85123456789' → '85123456789'."""
    return raw_id.split(":")[-1] if ":" in raw_id else raw_id


def _find_link(links: list[dict], rel: str) -> str | None:
    """Find href for a link with the given @ref value."""
    for link in links or []:
        if link.get("@ref") == rel:
            return link.get("@href")
    return None


def format_search_results(raw: dict[str, Any], query: str = "") -> dict[str, Any]:
    """Transform /content/search/scopus response into a flat, AI-friendly structure."""
    sr = _safe_get(raw, "search-results", default={})
    total = int(_safe_get(sr, "opensearch:totalResults", default=0))
    items_per_page = int(_safe_get(sr, "opensearch:itemsPerPage", default=0))
    start_index = int(_safe_get(sr, "opensearch:startIndex", default=0))

    entries = _safe_get(sr, "entry", default=[])
    if isinstance(entries, dict):
        entries = [entries]

    papers = []
    for e in entries:
        raw_id = _safe_get(e, "dc:identifier", default="")
        scopus_id = _strip_scopus_id(raw_id)
        links = _safe_get(e, "link", default=[])
        paper: dict[str, Any] = {
            "scopus_id": scopus_id,
            "eid": _safe_get(e, "eid", default=""),
            "title": _safe_get(e, "dc:title", default=""),
            "first_author": _safe_get(e, "dc:creator", default=""),
            "publication": _safe_get(e, "prism:publicationName", default=""),
            "cover_date": _safe_get(e, "prism:coverDate", default=""),
            "cited_by_count": int(_safe_get(e, "citedby-count", default=0)),
            "open_access": _safe_get(e, "openaccess", default="0") == "1",
            "scopus_url": _find_link(links, "scopus"),
        }
        doi = _safe_get(e, "prism:doi")
        if doi:
            paper["doi"] = doi
        volume = _safe_get(e, "prism:volume")
        if volume:
            paper["volume"] = volume
        issue = _safe_get(e, "prism:issueIdentifier")
        if issue:
            paper["issue"] = issue
        page_range = _safe_get(e, "prism:pageRange")
        if page_range:
            paper["page_range"] = page_range
        papers.append({k: v for k, v in paper.items() if v not in (None, "", [])})

    result: dict[str, Any] = {
        "total_results": total,
        "showing": len(papers),
        "start_index": start_index,
        "items_per_page": items_per_page,
        "papers": papers,
    }
    if query:
        result["query"] = query
    return result


def format_abstract(raw: dict[str, Any]) -> dict[str, Any]:
    """Transform /content/abstract/* response into a structured paper record."""
    root = _safe_get(raw, "abstracts-retrieval-response", default={})
    core = _safe_get(root, "coredata", default={})

    raw_id = _safe_get(core, "dc:identifier", default="")
    scopus_id = _strip_scopus_id(raw_id)

    # Authors
    authors_raw = _safe_get(root, "authors", "author", default=[])
    if isinstance(authors_raw, dict):
        authors_raw = [authors_raw]
    authors = []
    for a in authors_raw:
        surname = _safe_get(a, "ce:surname", default="")
        given = _safe_get(a, "ce:given-name", default="")
        initials = _safe_get(a, "ce:initials", default="")
        name = f"{surname}, {given or initials}".strip(", ")
        author_entry: dict[str, Any] = {
            "name": name,
            "scopus_author_id": _safe_get(a, "@auid", default=""),
        }
        affil_name = _safe_get(a, "affiliation", "ce:text")
        if affil_name:
            author_entry["affiliation"] = affil_name
        authors.append(author_entry)

    # Keywords
    kw_group = _safe_get(root, "authkeywords", "author-keyword", default=[])
    if isinstance(kw_group, dict):
        kw_group = [kw_group]
    keywords = [_safe_get(k, "$", default="") for k in kw_group if _safe_get(k, "$")]

    # Subject areas
    subj_areas_raw = _safe_get(root, "subject-areas", "subject-area", default=[])
    if isinstance(subj_areas_raw, dict):
        subj_areas_raw = [subj_areas_raw]
    subject_areas = [_safe_get(s, "$", default="") for s in subj_areas_raw if _safe_get(s, "$")]

    result: dict[str, Any] = {
        "scopus_id": scopus_id,
        "eid": _safe_get(core, "eid", default=""),
        "title": _safe_get(core, "dc:title", default=""),
        "abstract": _safe_get(core, "dc:description", default=""),
        "publication": _safe_get(core, "prism:publicationName", default=""),
        "cover_date": _safe_get(core, "prism:coverDate", default=""),
        "cited_by_count": int(_safe_get(core, "citedby-count", default=0)),
        "open_access": _safe_get(core, "openaccess", default="0") == "1",
        "authors": authors,
        "keywords": keywords,
        "subject_areas": subject_areas,
    }

    doi = _safe_get(core, "prism:doi")
    if doi:
        result["doi"] = doi
    pii = _safe_get(core, "pii")
    if pii:
        result["pii"] = pii
    pubmed_id = _safe_get(core, "pubmed-id")
    if pubmed_id:
        result["pubmed_id"] = str(pubmed_id)
    volume = _safe_get(core, "prism:volume")
    if volume:
        result["volume"] = volume
    issue = _safe_get(core, "prism:issueIdentifier")
    if issue:
        result["issue"] = issue
    page_range = _safe_get(core, "prism:pageRange")
    if page_range:
        result["page_range"] = page_range
    language = _safe_get(root, "language", "@xml:lang")
    if language:
        result["language"] = language

    return result


def format_author_profile(raw: dict[str, Any]) -> dict[str, Any]:
    """Transform /content/author/author_id/* response into an author profile."""
    root = _safe_get(raw, "author-retrieval-response")
    if isinstance(root, list):
        root = root[0] if root else {}

    core = _safe_get(root, "coredata", default={})
    metrics = _safe_get(root, "h-index", default=None)
    profile = _safe_get(root, "author-profile", default={})

    # Name
    pref_name = _safe_get(profile, "preferred-name", default={})
    surname = _safe_get(pref_name, "ce:surname", default="")
    given = _safe_get(pref_name, "ce:given-name", default="")
    initials = _safe_get(pref_name, "ce:initials", default="")

    # Current affiliation
    affil_raw = _safe_get(profile, "affiliation-current", "affiliation", default={})
    if isinstance(affil_raw, list):
        affil_raw = affil_raw[0] if affil_raw else {}
    affiliation = None
    if affil_raw:
        institution = _safe_get(affil_raw, "ip-doc", "afdispname") or _safe_get(affil_raw, "@affiliation-name", default="")
        country = _safe_get(affil_raw, "ip-doc", "address", "country") or _safe_get(affil_raw, "ip-doc", "@country", default="")
        city = _safe_get(affil_raw, "ip-doc", "address", "city", default=None)
        affiliation = {k: v for k, v in {"institution": institution, "country": country, "city": city}.items() if v}

    # Subject areas
    subj_areas_raw = _safe_get(root, "subject-areas", "subject-area", default=[])
    if isinstance(subj_areas_raw, dict):
        subj_areas_raw = [subj_areas_raw]
    subject_areas = [_safe_get(s, "$", default="") for s in subj_areas_raw if _safe_get(s, "$")]

    # Publication range
    pub_range_raw = _safe_get(profile, "publication-range", default={})
    pub_range = None
    if pub_range_raw:
        pub_range = {
            "start": _safe_get(pub_range_raw, "@start", default=""),
            "end": _safe_get(pub_range_raw, "@end", default=""),
        }

    result: dict[str, Any] = {
        "author_id": _safe_get(core, "dc:identifier", default="").replace("AUTHOR_ID:", ""),
        "name": f"{surname}, {given or initials}".strip(", "),
        "surname": surname,
        "given_name": given,
        "initials": initials,
        "h_index": int(metrics) if metrics is not None else None,
        "document_count": int(_safe_get(core, "document-count", default=0)),
        "cited_by_count": int(_safe_get(core, "cited-by-count", default=0)),
        "citation_count": int(_safe_get(core, "citation-count", default=0)),
        "subject_areas": subject_areas,
    }
    if affiliation:
        result["affiliation"] = affiliation
    if pub_range:
        result["publication_range"] = pub_range
    orcid = _safe_get(profile, "orcid")
    if orcid:
        result["orcid"] = orcid

    return result


def format_author_search_results(raw: dict[str, Any], query: str = "") -> dict[str, Any]:
    """Transform /content/search/author response."""
    sr = _safe_get(raw, "search-results", default={})
    total = int(_safe_get(sr, "opensearch:totalResults", default=0))
    entries = _safe_get(sr, "entry", default=[])
    if isinstance(entries, dict):
        entries = [entries]

    authors = []
    for e in entries:
        author: dict[str, Any] = {
            "author_id": _safe_get(e, "dc:identifier", default="").replace("AUTHOR_ID:", ""),
            "name": _safe_get(e, "preferred-name", "surname", default="") + ", " + (
                _safe_get(e, "preferred-name", "given-name") or _safe_get(e, "preferred-name", "initials", default="")
            ),
            "document_count": int(_safe_get(e, "document-count", default=0)),
        }
        affil_name = _safe_get(e, "affiliation-current", "affiliation-name")
        if affil_name:
            author["affiliation"] = affil_name
        country = _safe_get(e, "affiliation-current", "affiliation-country")
        if country:
            author["country"] = country
        orcid = _safe_get(e, "orcid")
        if orcid:
            author["orcid"] = orcid
        authors.append(author)

    result: dict[str, Any] = {
        "total_results": total,
        "showing": len(authors),
        "authors": authors,
    }
    if query:
        result["query"] = query
    return result


def format_affiliation_search_results(raw: dict[str, Any], query: str = "") -> dict[str, Any]:
    """Transform /content/search/affiliation response."""
    sr = _safe_get(raw, "search-results", default={})
    total = int(_safe_get(sr, "opensearch:totalResults", default=0))
    entries = _safe_get(sr, "entry", default=[])
    if isinstance(entries, dict):
        entries = [entries]

    affiliations = []
    for e in entries:
        links = _safe_get(e, "link", default=[])
        affil: dict[str, Any] = {
            "affiliation_id": _safe_get(e, "dc:identifier", default="").replace("AFFILIATION_ID:", ""),
            "name": _safe_get(e, "affiliation-name", default=""),
            "city": _safe_get(e, "city", default=""),
            "country": _safe_get(e, "country", default=""),
            "document_count": int(_safe_get(e, "document-count", default=0)),
        }
        scopus_url = _find_link(links, "scopus-affiliation")
        if scopus_url:
            affil["scopus_url"] = scopus_url
        affiliations.append({k: v for k, v in affil.items() if v not in (None, "", 0)})

    result: dict[str, Any] = {
        "total_results": total,
        "showing": len(affiliations),
        "affiliations": affiliations,
    }
    if query:
        result["query"] = query
    return result


def format_citation_count(raw: dict[str, Any]) -> dict[str, Any]:
    """Transform /content/abstract/citation-count response."""
    results = _safe_get(raw, "abstract-citations-response", "result", default=[])
    if isinstance(results, dict):
        results = [results]
    if not results:
        return {"error": "No citation data found"}

    first = results[0]
    return {
        "scopus_id": _safe_get(first, "scopus_id", default=""),
        "doi": _safe_get(first, "doi", default=None),
        "cited_by_count": int(_safe_get(first, "citationcount", default=0)),
        "self_citation_count": _safe_get(first, "selfcitationcount"),
    }


def format_citations_overview(raw: dict[str, Any]) -> dict[str, Any]:
    """Transform /content/abstract/citations response into yearly breakdown."""
    root = _safe_get(raw, "abstract-citations-response", default={})
    cite_info = _safe_get(root, "citeInfoMatrix", "citeInfoMatrixXML", "citationMatrix", default={})

    total = int(_safe_get(root, "citeInfoMatrix", "citeInfoMatrixXML", "citationMatrix", "citeCount", default=0))

    # Year-by-year columns
    col_headers = _safe_get(cite_info, "columnHeading", default=[])
    if isinstance(col_headers, dict):
        col_headers = [col_headers]
    years = [str(_safe_get(h, "$", default="")) for h in col_headers if _safe_get(h, "@type") == "YEAR"]

    row = _safe_get(cite_info, "citeCountHeader", default={})
    if isinstance(row, dict):
        row = [row]
    per_year: dict[str, int] = {}
    if row and years:
        counts_raw = _safe_get(row[0], "columnValue", default=[])
        if isinstance(counts_raw, (str, int)):
            counts_raw = [counts_raw]
        for year, count in zip(years, counts_raw):
            per_year[year] = int(count or 0)

    return {
        "total_citations": total,
        "citations_by_year": per_year,
    }
