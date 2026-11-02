from ..models import PaperSearchResult, AuthorSearchResult, AffiliationSearchResult
from typing import Annotated, Literal
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field
from ..client import ScopusClient
from ..exceptions import ScopusAPIError, ScopusAuthError
from ..services.search import (do_scopus_search, do_scopus_search_authors, do_scopus_search_affiliations, iter_scopus_search, iter_scopus_search_authors, iter_scopus_search_affiliations, AUTHOR_SEARCH_INST_NOTE, AFFILIATION_SEARCH_INST_NOTE, PAGE_MAX, OFFSET_MAX)

def register_search_tools(mcp: FastMCP, client: ScopusClient) -> None:

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
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
            Field(default=0, ge=0, le=4999, description="Pagination offset (0-based)"),
        ] = 0,
        view: Annotated[
            Literal["STANDARD", "COMPLETE"],
            Field(default="STANDARD", description="Response detail: STANDARD or COMPLETE"),
        ] = "STANDARD",
    ) -> PaperSearchResult:
        try:
            return PaperSearchResult.model_validate(await do_scopus_search(client, query, count, start, view))
        except (ScopusAPIError, ValueError) as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
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
        start: Annotated[int, Field(ge=0, le=4999, description="Pagination offset")] = 0,
    ) -> AuthorSearchResult:
        try:
            return AuthorSearchResult.model_validate(await do_scopus_search_authors(client, query, count, start))
        except ScopusAuthError as exc:
            raise ToolError(AUTHOR_SEARCH_INST_NOTE) from exc
        except (ScopusAPIError, ValueError) as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
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
        start: Annotated[int, Field(ge=0, le=4999, description="Pagination offset")] = 0,
    ) -> AffiliationSearchResult:
        try:
            return AffiliationSearchResult.model_validate(await do_scopus_search_affiliations(client, query, count, start))
        except ScopusAuthError as exc:
            raise ToolError(AFFILIATION_SEARCH_INST_NOTE) from exc
        except (ScopusAPIError, ValueError) as exc:
            raise ToolError(str(exc)) from exc

# Backward-compatible public imports for existing CLI integrations.
__all__ = ['iter_scopus_search', 'iter_scopus_search_authors', 'iter_scopus_search_affiliations', 'PAGE_MAX', 'OFFSET_MAX', 'register_search_tools']
