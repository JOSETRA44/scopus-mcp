"""Validation shared by both public adapters."""
import re


def identifier(value: str, kind: str) -> str:
    clean = value.strip()
    prefixes = {"scopus_id": "SCOPUS_ID:", "pubmed_id": "PMID:", "eid": "EID:", "author_id": "AUTHOR_ID:"}
    prefix = prefixes.get(kind, "")
    if prefix and clean.upper().startswith(prefix):
        clean = clean[len(prefix):].strip()
    if kind == "doi":
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if clean.lower().startswith(prefix):
                clean = clean[len(prefix):].strip()
                break
        valid = re.fullmatch(r"10\.\d{4,9}/\S+", clean)
    elif kind == "eid":
        valid = re.fullmatch(r"2-s2\.0-\d+", clean)
    elif kind in ("scopus_id", "pubmed_id", "author_id"):
        valid = re.fullmatch(r"[0-9]+", clean)
    else:
        raise ValueError("Unsupported identifier type.")
    if not valid:
        raise ValueError(f"Invalid {kind}: use a valid identifier.")
    return clean


def search_input(query: str, count: int, start: int, view: str = "STANDARD") -> str:
    query = query.strip()
    if not query:
        raise ValueError("Search query must not be empty.")
    if not 1 <= count <= 25:
        raise ValueError("count must be between 1 and 25.")
    if not 0 <= start < 5000 or start + count > 5000:
        raise ValueError("start + count must not exceed the 5000-record offset window.")
    if view not in ("STANDARD", "COMPLETE"):
        raise ValueError("view must be STANDARD or COMPLETE.")
    return query
