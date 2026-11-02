"""
Pure functions that transform raw Scopus API JSON into clean, AI-friendly dicts.
No side effects, no network calls — fully unit-testable with fixture data.
"""

from typing import Any

from .exceptions import ScopusAPIError, ScopusNotFoundError


def _safe_get(obj: Any, *keys: str | int, default: Any = None) -> Any:
    """Safely traverse nested dicts/lists without raising KeyError/TypeError."""
    for key in keys:
        try:
            obj = obj[key]
        except (KeyError, IndexError, TypeError):
            return default
    return obj if obj is not None else default


def _optional_count(value: Any) -> int | None:
    """Missing metrics remain unknown; malformed metrics are upstream errors."""
    if value is None or value == "":
        return None
    try:
        result = int(value)
        if result < 0:
            raise ValueError
        return result
    except (TypeError, ValueError) as exc:
        raise ScopusAPIError("Scopus returned an invalid numeric metric.") from exc


def _open_access(value: Any) -> bool | None:
    if value in ("1", 1, True):
        return True
    if value in ("0", 0, False):
        return False
    return None


def _search_entries(sr: dict) -> list[dict]:
    entries = sr.get("entry") or []
    if isinstance(entries, dict):
        entries = [entries]
    if not isinstance(entries, list):
        raise ScopusAPIError("Scopus returned malformed search entries.")
    result = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ScopusAPIError("Scopus returned a malformed search entry.")
        if "error" in entry:
            if (str(sr.get("opensearch:totalResults")) == "0"
                    and str(entry["error"]).strip().lower() == "result set was empty"):
                continue
            raise ScopusAPIError("Scopus returned an error in its search results.")
        result.append(entry)
    return result


def _search_root(raw: dict) -> dict:
    root = raw.get("search-results")
    if not isinstance(root, dict) or _optional_count(root.get("opensearch:totalResults")) is None:
        raise ScopusAPIError("Scopus returned an incomplete search response; result count is unknown.")
    return root


def _strip_scopus_id(raw_id: str) -> str:
    """Convert 'SCOPUS_ID:85123456789' → '85123456789'."""
    return raw_id.split(":")[-1] if ":" in raw_id else raw_id


def _find_link(links: list[dict], rel: str) -> str | None:
    """Find href for a link with the given @ref value."""
    if isinstance(links, dict):
        links = [links]
    for link in links or []:
        if link.get("@ref") == rel:
            return link.get("@href")
    return None


def format_search_results(raw: dict[str, Any], query: str = "") -> dict[str, Any]:
    """Transform /content/search/scopus response into a flat, AI-friendly structure."""
    sr = _search_root(raw)
    total = int(_safe_get(sr, "opensearch:totalResults", default=0))
    items_per_page = int(_safe_get(sr, "opensearch:itemsPerPage", default=0))
    start_index = int(_safe_get(sr, "opensearch:startIndex", default=0))

    entries = _search_entries(sr)

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
            "cited_by_count": _optional_count(_safe_get(e, "citedby-count")),
            "open_access": _open_access(_safe_get(e, "openaccess")),
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
        if e.get("prism:aggregationType"):
            paper["aggregation_type"] = e["prism:aggregationType"]
        if e.get("subtypeDescription"):
            paper["document_type"] = e["subtypeDescription"]
        author_list = e.get("author") or []
        if isinstance(author_list, dict):
            author_list = [author_list]
        if author_list:
            paper["authors"] = [
                {"name": author.get("authname") or author.get("indexed-name") or
                 ", ".join(filter(None, [author.get("surname"), author.get("given-name") or author.get("initials")])),
                 "scopus_author_id": author.get("authid")}
                for author in author_list if isinstance(author, dict)
            ]
        affiliation_list = e.get("affiliation") or []
        if isinstance(affiliation_list, dict):
            affiliation_list = [affiliation_list]
        if affiliation_list:
            paper["affiliations"] = [
                {"affiliation_id": affiliation.get("afid"), "name": affiliation.get("affilname"),
                 "city": affiliation.get("affiliation-city"), "country": affiliation.get("affiliation-country")}
                for affiliation in affiliation_list if isinstance(affiliation, dict)
            ]
        papers.append({k: v for k, v in paper.items() if v not in ("", [])})

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
    if not isinstance(core, dict) or not core:
        raise ScopusNotFoundError("No abstract record found in the Scopus response.")

    raw_id = _safe_get(core, "dc:identifier", default="")
    scopus_id = _strip_scopus_id(raw_id)

    # Authors — FULL view has root["authors"]["author"]; META view has coredata["dc:creator"]
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
    # META view fallback: dc:creator holds the author.
    # It may be a plain string ("Smith J.") or a rich dict {"author": [{...}]}.
    if not authors:
        creator = _safe_get(core, "dc:creator")
        if isinstance(creator, str) and creator:
            authors = [{"name": creator}]
        elif isinstance(creator, dict):
            author_list = creator.get("author", [])
            if isinstance(author_list, dict):
                author_list = [author_list]
            for a in (author_list or [])[:10]:
                surname = _safe_get(a, "ce:surname", default="")
                given = _safe_get(a, "ce:given-name", default="")
                initials = _safe_get(a, "ce:initials", default="")
                name = f"{surname}, {given or initials}".strip(", ")
                if not name:
                    continue
                author_entry: dict[str, Any] = {"name": name}
                auid = _safe_get(a, "@auid")
                if auid:
                    author_entry["scopus_author_id"] = auid
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
        "cited_by_count": _optional_count(_safe_get(core, "citedby-count")),
        "open_access": _open_access(_safe_get(core, "openaccess")),
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
    if core.get("prism:aggregationType"):
        result["aggregation_type"] = core["prism:aggregationType"]
    if core.get("subtypeDescription"):
        result["document_type"] = core["subtypeDescription"]

    # META view: affiliations are at root level (not under authors)
    if not result.get("authors") or all(not a.get("affiliation") for a in result.get("authors", [])):
        affil_list = _safe_get(root, "affiliation", default=[])
        if isinstance(affil_list, dict):
            affil_list = [affil_list]
        if affil_list:
            result["affiliations"] = [
                {
                    "name": _safe_get(a, "affilname", default=""),
                    "city": _safe_get(a, "affiliation-city"),
                    "country": _safe_get(a, "affiliation-country"),
                }
                for a in affil_list
                if _safe_get(a, "affilname")
            ]

    return result


def format_author_profile(raw: dict[str, Any]) -> dict[str, Any]:
    """Transform /content/author/author_id/* response into an author profile."""
    root = _safe_get(raw, "author-retrieval-response")
    if isinstance(root, list):
        root = root[0] if root else {}

    core = _safe_get(root, "coredata", default={})
    if not isinstance(core, dict) or not core:
        raise ScopusNotFoundError("No author record found in the Scopus response.")
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
        "h_index": _optional_count(metrics),
        "document_count": _optional_count(_safe_get(core, "document-count")),
        "cited_by_count": _optional_count(_safe_get(core, "cited-by-count")),
        "citation_count": _optional_count(_safe_get(core, "citation-count")),
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
    sr = _search_root(raw)
    total = int(_safe_get(sr, "opensearch:totalResults", default=0))
    entries = _search_entries(sr)

    authors = []
    for e in entries:
        author: dict[str, Any] = {
            "author_id": _safe_get(e, "dc:identifier", default="").replace("AUTHOR_ID:", ""),
            "name": _safe_get(e, "preferred-name", "surname", default="") + ", " + (
                _safe_get(e, "preferred-name", "given-name") or _safe_get(e, "preferred-name", "initials", default="")
            ),
            "document_count": _optional_count(_safe_get(e, "document-count")),
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
        "start_index": int(sr.get("opensearch:startIndex", 0)),
        "items_per_page": int(sr.get("opensearch:itemsPerPage", len(authors))),
    }
    if query:
        result["query"] = query
    return result


def format_affiliation_search_results(raw: dict[str, Any], query: str = "") -> dict[str, Any]:
    """Transform /content/search/affiliation response."""
    sr = _search_root(raw)
    total = int(_safe_get(sr, "opensearch:totalResults", default=0))
    entries = _search_entries(sr)

    affiliations = []
    for e in entries:
        links = _safe_get(e, "link", default=[])
        affil: dict[str, Any] = {
            "affiliation_id": _safe_get(e, "dc:identifier", default="").replace("AFFILIATION_ID:", ""),
            "name": _safe_get(e, "affiliation-name", default=""),
            "city": _safe_get(e, "city", default=""),
            "country": _safe_get(e, "country", default=""),
            "document_count": _optional_count(_safe_get(e, "document-count")),
        }
        scopus_url = _find_link(links, "scopus-affiliation")
        if scopus_url:
            affil["scopus_url"] = scopus_url
        affiliations.append({k: v for k, v in affil.items() if v != ""})

    result: dict[str, Any] = {
        "total_results": total,
        "showing": len(affiliations),
        "affiliations": affiliations,
        "start_index": int(sr.get("opensearch:startIndex", 0)),
        "items_per_page": int(sr.get("opensearch:itemsPerPage", len(affiliations))),
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
        raise ScopusNotFoundError("No citation data found for this record.")

    first = results[0]
    return {
        "scopus_id": _safe_get(first, "scopus_id", default=""),
        "doi": _safe_get(first, "doi", default=None),
        "cited_by_count": _optional_count(_safe_get(first, "citationcount")),
        "self_citation_count": _optional_count(_safe_get(first, "selfcitationcount")),
    }


def format_citations_overview(raw: dict[str, Any]) -> dict[str, Any]:
    """Transform /content/abstract/citations response into yearly breakdown."""
    root = _safe_get(raw, "abstract-citations-response", default={})
    cite_info = _safe_get(root, "citeInfoMatrix", "citeInfoMatrixXML", "citationMatrix", default={})

    if not isinstance(cite_info, dict) or not cite_info:
        raise ScopusNotFoundError("No citation timeline data found for this record.")
    total = _optional_count(cite_info.get("citeCount"))

    # Year-by-year columns
    col_headers = _safe_get(cite_info, "columnHeading", default=[])
    if isinstance(col_headers, dict):
        col_headers = [col_headers]
    years = [str(_safe_get(h, "$", default="")) for h in col_headers if _safe_get(h, "@type") == "YEAR"]

    row = _safe_get(cite_info, "citeCountHeader", default={})
    if isinstance(row, dict):
        row = [row]
    per_year: dict[str, int | None] = {}
    if row and years:
        counts_raw = _safe_get(row[0], "columnValue", default=[])
        if isinstance(counts_raw, (str, int)):
            counts_raw = [counts_raw]
        for index, year in enumerate(years):
            per_year[year] = _optional_count(counts_raw[index]) if index < len(counts_raw) else None

    return {
        "total_citations": total,
        "citations_by_year": per_year,
    }
