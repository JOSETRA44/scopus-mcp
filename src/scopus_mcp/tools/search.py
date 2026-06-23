from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from ..client import ScopusClient
from ..exceptions import ScopusAPIError
from ..formatters import (
    format_affiliation_search_results,
    format_author_search_results,
    format_search_results,
)


def register_search_tools(mcp: FastMCP, client: ScopusClient) -> None:

    @mcp.tool(
        name="scopus_search",
        description=(
            "Search the Scopus academic database for papers using Boolean query syntax.\n\n"
            "Common field codes:\n"
            "- TITLE-ABS-KEY(term) — search title, abstract, and keywords (most useful)\n"
            "- TITLE(term) — title only\n"
            "- AUTH(name) — author name, e.g. AUTH(\"Smith J\")\n"
            "- AFFIL(institution) — author affiliation\n"
            "- PUBYEAR > 2020 — filter by publication year\n"
            "- DOCTYPE(ar) — document type: ar=article, re=review, cp=conference paper\n\n"
            "Boolean operators: AND, OR, AND NOT\n"
            "Example: TITLE-ABS-KEY(\"machine learning\" AND cancer) AND PUBYEAR > 2020\n\n"
            "Read the scopus://search-syntax resource for the full syntax reference."
        ),
    )
    async def scopus_search(
        query: Annotated[str, Field(description="Scopus Boolean search query")],
        count: Annotated[
            int,
            Field(default=10, ge=1, le=25, description="Number of results to return (1–25)"),
        ] = 10,
        start: Annotated[
            int,
            Field(default=0, ge=0, description="Pagination offset (0-based)"),
        ] = 0,
        view: Annotated[
            str,
            Field(default="STANDARD", description="Response detail: STANDARD or COMPLETE"),
        ] = "STANDARD",
    ) -> dict:
        try:
            raw = await client.request(
                "/content/search/scopus",
                params={"query": query, "count": count, "start": start, "view": view},
            )
            return format_search_results(raw, query=query)
        except ScopusAPIError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="scopus_search_authors",
        description=(
            "Search for author profiles in the Scopus author index.\n\n"
            "Query field codes:\n"
            "- AUTHLASTNAME(Smith) — last name\n"
            "- AUTHFIRST(John) — first name or initials\n"
            "- ORCID(0000-0002-1234-5678) — ORCID identifier\n"
            "- AF-ID(60027950) — affiliation ID\n\n"
            "Example: AUTHLASTNAME(Smith) AND AUTHFIRST(J) AND AFFIL(MIT)\n\n"
            "Use scopus_get_author with the returned author_id to fetch full metrics."
        ),
    )
    async def scopus_search_authors(
        query: Annotated[str, Field(description="Author search query")],
        count: Annotated[
            int,
            Field(default=10, ge=1, le=25, description="Number of results (1–25)"),
        ] = 10,
    ) -> dict:
        try:
            raw = await client.request(
                "/content/search/author",
                params={"query": query, "count": count},
            )
            return format_author_search_results(raw, query=query)
        except ScopusAPIError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="scopus_search_affiliations",
        description=(
            "Search for institution and affiliation records in Scopus.\n\n"
            "Query examples:\n"
            "- AFFIL(MIT) — by name keyword\n"
            "- AFFIL(Harvard) AND COUNTRY(United States)\n"
            "- AFFIL-ID(60027950) — by Scopus affiliation ID\n\n"
            "Returns affiliation_id needed for author searches and filtering."
        ),
    )
    async def scopus_search_affiliations(
        query: Annotated[str, Field(description="Affiliation/institution search query")],
        count: Annotated[
            int,
            Field(default=10, ge=1, le=25, description="Number of results (1–25)"),
        ] = 10,
    ) -> dict:
        try:
            raw = await client.request(
                "/content/search/affiliation",
                params={"query": query, "count": count},
            )
            return format_affiliation_search_results(raw, query=query)
        except ScopusAPIError as exc:
            raise ToolError(str(exc)) from exc
