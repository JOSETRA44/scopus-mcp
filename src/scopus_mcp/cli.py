"""Terminal CLI for scopus-mcp: run Scopus lookups directly from a shell.

This module powers the `scopus` / `scps` / `scopus-mcp <subcommand>` commands.
Running the entry point with NO subcommand keeps the original behavior of
starting the MCP stdio server (see server.py:main) — that path is untouched.
"""

import argparse
import asyncio
import json
import sys
from importlib.metadata import PackageNotFoundError, version

from .client import ScopusClient
from .config import ScopusSettings, get_settings
from .exceptions import ScopusAPIError, ScopusAuthError, ScopusConfigError
from .tools.abstract import do_get_abstract
from .tools.author import AUTHOR_INST_NOTE, do_get_author
from .tools.citations import (
    CITATIONS_INST_NOTE,
    do_get_citation_count,
    do_get_citations_overview,
)
from .tools.search import (
    AFFILIATION_SEARCH_INST_NOTE,
    AUTHOR_SEARCH_INST_NOTE,
    do_scopus_search,
    do_scopus_search_affiliations,
    do_scopus_search_authors,
)

_INST_NOTES: dict[str, str] = {
    "author": AUTHOR_INST_NOTE,
    "search-authors": AUTHOR_SEARCH_INST_NOTE,
    "search-affiliations": AFFILIATION_SEARCH_INST_NOTE,
    "citation-count": CITATIONS_INST_NOTE,
    "citations": CITATIONS_INST_NOTE,
}


def get_version() -> str:
    try:
        return version("scopus-mcp")
    except PackageNotFoundError:
        return "0.1.0 (dev, not installed)"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scopus",
        description=(
            "Scopus academic research CLI — search papers, fetch abstracts, and look up "
            "researcher/citation data directly from the terminal.\n\n"
            "Running with NO subcommand starts the MCP stdio server instead (for use by "
            "an MCP client such as Claude Desktop/Code) — it will block waiting for "
            "input on stdin, which is expected and not an error."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="store_true", help="Show version and exit")

    sub = parser.add_subparsers(dest="command")

    p_search = sub.add_parser("search", help="Search papers by Boolean query")
    p_search.add_argument("query", help='Scopus Boolean query, e.g. TITLE-ABS-KEY("machine learning")')
    p_search.add_argument("--count", type=int, default=10, help="Results to return, 1-25 (default: 10)")
    p_search.add_argument("--start", type=int, default=0, help="Pagination offset (default: 0)")
    p_search.add_argument("--view", default="STANDARD", choices=["STANDARD", "COMPLETE"])
    p_search.add_argument("--json", action="store_true", help="Print raw JSON instead of a summary")

    p_abstract = sub.add_parser("abstract", help="Fetch full paper details by identifier")
    p_abstract.add_argument("identifier", help="Identifier value (scopus_id, doi, eid, or pubmed_id)")
    p_abstract.add_argument(
        "--type",
        dest="identifier_type",
        required=True,
        choices=["scopus_id", "doi", "eid", "pubmed_id"],
        help="Type of the identifier",
    )
    p_abstract.add_argument("--json", action="store_true")

    p_author = sub.add_parser("author", help="Fetch a researcher's Scopus profile (requires SCOPUS_INST_TOKEN)")
    p_author.add_argument("author_id", help="Scopus Author ID")
    p_author.add_argument("--json", action="store_true")

    p_search_authors = sub.add_parser(
        "search-authors", help="Search author profiles (requires SCOPUS_INST_TOKEN)"
    )
    p_search_authors.add_argument("query", help="Author search query, e.g. AUTHLASTNAME(Smith)")
    p_search_authors.add_argument("--count", type=int, default=10)
    p_search_authors.add_argument("--json", action="store_true")

    p_search_affil = sub.add_parser(
        "search-affiliations", help="Search institution/affiliation records (requires SCOPUS_INST_TOKEN)"
    )
    p_search_affil.add_argument("query", help="Affiliation search query, e.g. AFFIL(MIT)")
    p_search_affil.add_argument("--count", type=int, default=10)
    p_search_affil.add_argument("--json", action="store_true")

    p_citation_count = sub.add_parser(
        "citation-count", help="Get total citation count for a paper (requires SCOPUS_INST_TOKEN)"
    )
    group = p_citation_count.add_mutually_exclusive_group(required=True)
    group.add_argument("--scopus-id", dest="scopus_id")
    group.add_argument("--doi")
    p_citation_count.add_argument("--json", action="store_true")

    p_citations = sub.add_parser(
        "citations", help="Year-by-year citation timeline (requires SCOPUS_INST_TOKEN)"
    )
    p_citations.add_argument("scopus_id", help="Scopus numeric ID of the paper")
    p_citations.add_argument("--start-year", type=int, default=2000)
    p_citations.add_argument("--end-year", type=int, default=2025)
    p_citations.add_argument("--json", action="store_true")

    p_check = sub.add_parser("check", help="Validate API key and show which tools are available")
    p_check.add_argument("--json", action="store_true")

    return parser


# ── Human-readable renderers ────────────────────────────────────────────────

def _print_result(result: dict, as_json: bool, renderer) -> None:
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        renderer(result)


def _render_search(result: dict) -> None:
    total = result.get("total_results", 0)
    papers = result.get("papers", [])
    print(f"Total: {total} results (showing {len(papers)})\n")
    for p in papers:
        year = (p.get("cover_date") or "")[:4]
        print(f"- [{p.get('scopus_id')}] {p.get('title')} ({year}) — {p.get('cited_by_count', 0)} citations")
        if p.get("doi"):
            print(f"    doi: {p['doi']}")


def _render_abstract(result: dict) -> None:
    print(result.get("title", ""))
    authors = result.get("authors", [])
    if authors:
        print("Authors: " + ", ".join(a.get("name", "") for a in authors))
    if result.get("publication"):
        print(f"Publication: {result['publication']} ({result.get('cover_date', '')})")
    if result.get("doi"):
        print(f"DOI: {result['doi']}")
    print(f"Cited by: {result.get('cited_by_count', 0)}")
    if result.get("abstract"):
        print(f"\nAbstract:\n{result['abstract']}")
    if result.get("access_note"):
        print(f"\nNote: {result['access_note']}")


def _render_author(result: dict) -> None:
    print(result.get("name", ""))
    print(f"h-index: {result.get('h_index')}")
    print(f"Documents: {result.get('document_count')}")
    print(f"Cited by: {result.get('cited_by_count')}")
    affiliation = result.get("affiliation")
    if affiliation:
        print(f"Affiliation: {affiliation.get('institution', '')} ({affiliation.get('country', '')})")


def _render_author_search(result: dict) -> None:
    total = result.get("total_results", 0)
    authors = result.get("authors", [])
    print(f"Total: {total} authors (showing {len(authors)})\n")
    for a in authors:
        line = f"- [{a.get('author_id')}] {a.get('name')}"
        if a.get("affiliation"):
            line += f" — {a['affiliation']}"
        print(line)


def _render_affiliation_search(result: dict) -> None:
    total = result.get("total_results", 0)
    affs = result.get("affiliations", [])
    print(f"Total: {total} affiliations (showing {len(affs)})\n")
    for a in affs:
        loc = ", ".join(x for x in [a.get("city"), a.get("country")] if x)
        print(f"- [{a.get('affiliation_id')}] {a.get('name')} — {loc} ({a.get('document_count', 0)} docs)")


def _render_citation_count(result: dict) -> None:
    print(f"Scopus ID: {result.get('scopus_id', '')}")
    if result.get("doi"):
        print(f"DOI: {result['doi']}")
    print(f"Cited by: {result.get('cited_by_count', 0)}")


def _render_citations_overview(result: dict) -> None:
    print(f"Total citations: {result.get('total_citations', 0)}")
    for year, count in result.get("citations_by_year", {}).items():
        print(f"  {year}: {count}")


# ── check command ───────────────────────────────────────────────────────────

async def _probe(coro) -> str:
    """Run a cheap live call and classify the result for the capability report."""
    try:
        await coro
        return "ok"
    except ScopusAuthError:
        return "requires SCOPUS_INST_TOKEN"
    except ScopusAPIError as exc:
        return f"FAIL: {exc}"


async def _cmd_check(settings: ScopusSettings, as_json: bool) -> int:
    masked = (
        f"{settings.api_key[:8]}...{settings.api_key[-4:]}"
        if len(settings.api_key) > 12
        else "****"
    )
    has_inst_token = bool(settings.inst_token)

    # Live probes reflect the *actual* current entitlements of this API key —
    # Elsevier's per-endpoint access tiers can vary independently of each other,
    # so a static guess table would be misleading.
    async with ScopusClient(settings) as client:
        capabilities = {
            "search": await _probe(do_scopus_search(client, "TITLE(test)", count=1)),
            "abstract": "adaptive — tries full view, falls back to metadata-only per paper",
            "author / search-authors": await _probe(
                do_scopus_search_authors(client, "AUTHLASTNAME(Smith)", count=1)
            ),
            "search-affiliations": await _probe(
                do_scopus_search_affiliations(client, "AFFIL(MIT)", count=1)
            ),
            "citation-count / citations": await _probe(
                do_get_citation_count(client, scopus_id="85180904906")
            ),
        }

    search_ok = capabilities["search"] == "ok"

    if as_json:
        print(json.dumps({
            "api_key": masked,
            "inst_token_configured": has_inst_token,
            "capabilities": capabilities,
        }, indent=2, ensure_ascii=False))
    else:
        print(f"API key: {masked}")
        print(f"Institutional token: {'configured' if has_inst_token else 'not set'}")
        print()
        print("Tool availability with this configuration (live-checked):")
        for name, status in capabilities.items():
            print(f"  {name:28} {status}")

    return 0 if search_ok else 1


# ── Dispatcher ───────────────────────────────────────────────────────────────

async def run_cli(args: argparse.Namespace) -> int:
    try:
        settings = get_settings()
    except ScopusConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    if args.command == "check":
        return await _cmd_check(settings, args.json)

    async with ScopusClient(settings) as client:
        try:
            if args.command == "search":
                result = await do_scopus_search(client, args.query, args.count, args.start, args.view)
                _print_result(result, args.json, _render_search)
            elif args.command == "abstract":
                result = await do_get_abstract(client, args.identifier_type, args.identifier)
                _print_result(result, args.json, _render_abstract)
            elif args.command == "author":
                result = await do_get_author(client, args.author_id)
                _print_result(result, args.json, _render_author)
            elif args.command == "search-authors":
                result = await do_scopus_search_authors(client, args.query, args.count)
                _print_result(result, args.json, _render_author_search)
            elif args.command == "search-affiliations":
                result = await do_scopus_search_affiliations(client, args.query, args.count)
                _print_result(result, args.json, _render_affiliation_search)
            elif args.command == "citation-count":
                result = await do_get_citation_count(client, args.scopus_id, args.doi)
                _print_result(result, args.json, _render_citation_count)
            elif args.command == "citations":
                result = await do_get_citations_overview(
                    client, args.scopus_id, args.start_year, args.end_year
                )
                _print_result(result, args.json, _render_citations_overview)
            else:
                return 1
        except ScopusAuthError as exc:
            print(_INST_NOTES.get(args.command, str(exc)), file=sys.stderr)
            return 1
        except (ScopusAPIError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    return 0


def main_cli(args: argparse.Namespace) -> int:
    return asyncio.run(run_cli(args))
