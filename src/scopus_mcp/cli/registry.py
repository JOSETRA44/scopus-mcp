"""Per-command metadata the parser cannot express on its own.

The ``describe`` manifest is derived from the argparse parser (names, arguments,
options, help text). What argparse does *not* know is the shape of a command's
rows, whether it can bulk-harvest, and what a realistic invocation looks like —
that lives here and is merged in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from . import rows as R


@dataclass(frozen=True)
class CommandSpec:
    """Everything the output layer and ``describe`` need about one subcommand."""

    name: str
    title: str
    rows_from: Callable[[dict], list[dict]]
    row_fields: list[str]
    meta_from: Callable[[dict], dict[str, Any]] = R.no_meta
    supports_all: bool = False
    examples: list[str] = field(default_factory=list)


COMMANDS: dict[str, CommandSpec] = {
    "search": CommandSpec(
        name="search",
        title="Papers",
        rows_from=R.rows_search,
        row_fields=R.PAPER_FIELDS,
        meta_from=R.search_meta,
        supports_all=True,
        examples=[
            'scopus search \'TITLE-ABS-KEY("graph neural network")\' --count 5',
            "scopus search 'TITLE-ABS-KEY(crispr) AND PUBYEAR > 2020' -f jsonl --all --max 500",
            "scopus search 'AFFIL(MIT)' -f csv -o mit.csv --all --max 200",
        ],
    ),
    "abstract": CommandSpec(
        name="abstract",
        title="Paper",
        rows_from=R.rows_abstract,
        row_fields=R.ABSTRACT_FIELDS,
        examples=[
            "scopus abstract 10.1016/j.labeco.2024.102505 --type doi -f json",
            "scopus abstract 85180904906 --type scopus_id",
        ],
    ),
    "author": CommandSpec(
        name="author",
        title="Author profile",
        rows_from=R.rows_author,
        row_fields=R.AUTHOR_PROFILE_FIELDS,
        examples=["scopus author 7401234567 -f json"],
    ),
    "search-authors": CommandSpec(
        name="search-authors",
        title="Authors",
        rows_from=R.rows_search_authors,
        row_fields=R.AUTHOR_ROW_FIELDS,
        meta_from=R.total_meta,
        supports_all=True,
        examples=[
            "scopus search-authors 'AUTHLASTNAME(Hinton)' --count 5",
            "scopus search-authors 'AFFIL(MIT)' -f jsonl --all --max 100",
        ],
    ),
    "search-affiliations": CommandSpec(
        name="search-affiliations",
        title="Affiliations",
        rows_from=R.rows_search_affiliations,
        row_fields=R.AFFILIATION_ROW_FIELDS,
        meta_from=R.total_meta,
        supports_all=True,
        examples=[
            "scopus search-affiliations 'AFFIL(Cambridge)' -f md",
            "scopus search-affiliations 'COUNTRY(Peru)' -f csv --all --max 300",
        ],
    ),
    "citation-count": CommandSpec(
        name="citation-count",
        title="Citation count",
        rows_from=R.rows_citation_count,
        row_fields=R.CITATION_COUNT_FIELDS,
        examples=["scopus citation-count --doi 10.1038/nature14539 -f json"],
    ),
    "citations": CommandSpec(
        name="citations",
        title="Citations by year",
        rows_from=R.rows_citations,
        row_fields=R.CITATIONS_FIELDS,
        examples=["scopus citations 85180904906 --start-year 2019 --end-year 2025 -f csv"],
    ),
    "check": CommandSpec(
        name="check",
        title="Capabilities",
        rows_from=R.rows_check,
        row_fields=R.CHECK_FIELDS,
        examples=["scopus check -f json"],
    ),
    "cache": CommandSpec(
        name="cache",
        title="Cache",
        rows_from=R.rows_cache,
        row_fields=R.CACHE_FIELDS,
        examples=["scopus cache stats -f json", "scopus cache path", "scopus cache clear"],
    ),
    "describe": CommandSpec(
        name="describe",
        title="Commands",
        rows_from=lambda result: result.get("rows", []),
        row_fields=["name", "summary", "supports_all"],
        examples=["scopus describe --json", "scopus describe search --json"],
    ),
}
