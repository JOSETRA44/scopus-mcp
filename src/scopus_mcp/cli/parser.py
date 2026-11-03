"""Argparse construction for the Scopus CLI.

Global flags are registered twice: once on the root parser (so they may precede
the subcommand) and once on every subparser with ``default=SUPPRESS`` (so they
may follow it without a subparser default clobbering the root value — argparse
copies the sub-namespace over the root one, and SUPPRESS keeps absent flags out
of that copy).
"""

from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version

from .render import FORMATS

SUPPRESS = argparse.SUPPRESS


def get_version() -> str:
    try:
        return version("josetra-scopus-mcp")
    except PackageNotFoundError:
        from .. import __version__
        return f"{__version__} (dev, not installed)"


def add_global_flags(parser: argparse.ArgumentParser, sub: bool = False) -> None:
    """Attach the ARSENAL-SPEC §1 flags. ``sub=True`` suppresses defaults."""

    def default(value: object) -> object:
        return SUPPRESS if sub else value

    parser.add_argument("-f", "--format", choices=list(FORMATS), default=default("table"),
                        help="Output format (default: table); RIS/BibTeX/CSL-JSON for papers")
    parser.add_argument("-o", "--output", metavar="FILE", default=default(None),
                        help="Write output to FILE instead of stdout")
    parser.add_argument("-q", "--quiet", action="store_true", default=default(False),
                        help="Suppress progress and notes on stderr")
    parser.add_argument("--no-color", action="store_true", default=default(False),
                        help="Disable ANSI colour (also honours NO_COLOR)")
    parser.add_argument("--refresh", action="store_true", default=default(False),
                        help="Ignore the cached response, refetch and rewrite the cache")
    parser.add_argument("--no-cache", action="store_true", dest="no_cache",
                        default=default(False),
                        help="Neither read nor write the disk cache")
    parser.add_argument("--record", metavar="FILE", default=default(None),
                        help="Save a reproducibility record (query, retrieval times, completeness; no credentials)")


def _add_json_alias(parser: argparse.ArgumentParser) -> None:
    """Legacy ``--json`` — kept as a hidden alias for ``--format json``."""
    parser.add_argument(
        "--json", action="store_const", const="json", dest="format",
        default=SUPPRESS, help=SUPPRESS,
    )


def _add_bulk_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--all", action="store_true", dest="fetch_all",
                        help="Keep paging until the result set is exhausted")
    parser.add_argument("--max", type=int, default=1000, dest="max_rows",
                        help="Hard ceiling on rows harvested by --all (default: 1000)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scopus",
        description=(
            "Scopus academic research CLI — search papers, fetch abstracts, and look up "
            "researcher/citation data directly from the terminal.\n\n"
            "Running with NO subcommand starts the MCP stdio server instead (for use by "
            "an MCP client such as Claude Desktop/Code) — it will block waiting for "
            "input on stdin, which is expected and not an error.\n\n"
            "Agents: run `scopus describe --json` for a machine-readable manifest of "
            "every command, its arguments, its row fields and its exit codes."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    add_global_flags(parser)

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    def new(name: str, help_text: str, bulk: bool = False) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text, description=help_text)
        add_global_flags(p, sub=True)
        _add_json_alias(p)
        if bulk:
            _add_bulk_flags(p)
        return p

    p_search = new("search", "Search papers by Boolean query", bulk=True)
    p_search.add_argument("query", help='Scopus Boolean query, e.g. TITLE-ABS-KEY("machine learning")')
    p_search.add_argument("--count", type=int, default=10, help="Results per page, 1-25 (default: 10)")
    p_search.add_argument("--start", type=int, default=0, help="Pagination offset (default: 0)")
    p_search.add_argument("--view", default="STANDARD", choices=["STANDARD", "COMPLETE"])

    p_abstract = new("abstract", "Fetch full paper details by identifier")
    p_abstract.add_argument("identifier", help="Identifier value (scopus_id, doi, eid, or pubmed_id)")
    p_abstract.add_argument(
        "--type", dest="identifier_type", required=True,
        choices=["scopus_id", "doi", "eid", "pubmed_id"],
        help="Type of the identifier",
    )

    p_author = new("author", "Fetch a researcher's Scopus profile (requires SCOPUS_INST_TOKEN)")
    p_author.add_argument("author_id", help="Scopus Author ID")

    p_search_authors = new(
        "search-authors", "Search author profiles (requires SCOPUS_INST_TOKEN)", bulk=True
    )
    p_search_authors.add_argument("query", help="Author search query, e.g. AUTHLASTNAME(Smith)")
    p_search_authors.add_argument("--count", type=int, default=10, help="Results per page, 1-25")
    p_search_authors.add_argument("--start", type=int, default=0, help="Pagination offset")

    p_search_affil = new(
        "search-affiliations",
        "Search institution/affiliation records (requires SCOPUS_INST_TOKEN)",
        bulk=True,
    )
    p_search_affil.add_argument("query", help="Affiliation search query, e.g. AFFIL(MIT)")
    p_search_affil.add_argument("--count", type=int, default=10, help="Results per page, 1-25")
    p_search_affil.add_argument("--start", type=int, default=0, help="Pagination offset")

    p_citation_count = new(
        "citation-count", "Get total citation count for a paper (requires SCOPUS_INST_TOKEN)"
    )
    group = p_citation_count.add_mutually_exclusive_group(required=True)
    group.add_argument("--scopus-id", dest="scopus_id", help="Scopus numeric ID of the paper")
    group.add_argument("--doi", help="DOI of the paper")

    p_citations = new("citations", "Year-by-year citation timeline (requires SCOPUS_INST_TOKEN)")
    p_citations.add_argument("scopus_id", help="Scopus numeric ID of the paper")
    p_citations.add_argument("--start-year", type=int, default=2000, help="First year of the range")
    p_citations.add_argument("--end-year", type=int, default=None, help="Last year of the range (default: current year)")

    new("check", "Validate API key and show which tools are available")
    p_setup = new("setup", "Configure Scopus with a guided, private API key prompt")
    p_setup.add_argument("--language", choices=["en", "es"], help="Wizard language (default: system language)")
    p_setup.add_argument("--from-env", action="store_true", help="Save SCOPUS_API_KEY and optional SCOPUS_INST_TOKEN without prompting")
    p_setup.add_argument("--force", action="store_true", help="Allow --from-env to replace saved credentials")
    p_setup.add_argument("--show", action="store_true", help="Show saved configuration status and path, never credentials")
    p_setup.add_argument("--check", action="store_true", help="After saving, test each endpoint (uses API quota)")

    p_cache = new("cache", "Inspect or clear the persistent response cache")
    p_cache.add_argument(
        "action", nargs="?", default="stats", choices=["stats", "clear", "path"],
        help="stats (default) | clear | path",
    )

    p_describe = new("describe", "Print a machine-readable manifest of this CLI")
    p_describe.add_argument(
        "target", nargs="?", default=None,
        help="Restrict the manifest to a single command",
    )

    return parser
