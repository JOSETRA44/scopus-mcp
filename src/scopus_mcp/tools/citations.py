from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from ..client import ScopusClient
from ..exceptions import ScopusAPIError, ScopusAuthError
from ..formatters import format_citation_count, format_citations_overview

CITATIONS_INST_NOTE = (
    "This endpoint requires an institutional Elsevier subscription. "
    "Set SCOPUS_INST_TOKEN in your .env file. "
    "Tip: the cited_by_count field in scopus_search and scopus_get_abstract "
    "provides citation totals without institutional access."
)


async def do_get_citation_count(
    client: ScopusClient,
    scopus_id: str | None = None,
    doi: str | None = None,
) -> dict:
    if not scopus_id and not doi:
        raise ValueError("Provide at least one of: scopus_id or doi.")

    params: dict = {}
    if scopus_id:
        params["scopus_id"] = scopus_id.strip()
    elif doi:
        params["doi"] = doi.strip()

    raw = await client.request("/content/abstract/citation-count", params=params)
    return format_citation_count(raw)


async def do_get_citations_overview(
    client: ScopusClient,
    scopus_id: str,
    start_year: int = 2000,
    end_year: int = 2025,
) -> dict:
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year.")

    raw = await client.request(
        "/content/abstract/citations",
        params={
            "scopus_id": scopus_id.strip(),
            "date": f"{start_year}-{end_year}",
            "httpAccept": "application/json",
        },
    )
    return format_citations_overview(raw)


def register_citation_tools(mcp: FastMCP, client: ScopusClient) -> None:

    @mcp.tool(
        name="scopus_get_citation_count",
        description=(
            "Get the current total citation count for a paper.\n\n"
            "Provide either a Scopus ID or a DOI — at least one is required.\n"
            "This endpoint is lightweight and cached; use it for quick citation lookups "
            "without fetching the full abstract."
        ),
    )
    async def scopus_get_citation_count(
        scopus_id: Annotated[
            str | None,
            Field(default=None, description="Scopus numeric ID of the paper"),
        ] = None,
        doi: Annotated[
            str | None,
            Field(default=None, description="DOI of the paper"),
        ] = None,
    ) -> dict:
        try:
            return await do_get_citation_count(client, scopus_id, doi)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        except ScopusAuthError as exc:
            raise ToolError(CITATIONS_INST_NOTE) from exc
        except ScopusAPIError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="scopus_get_citations_overview",
        description=(
            "Get a year-by-year citation timeline for a paper.\n\n"
            "Returns how many times the paper was cited in each calendar year "
            "within the specified date range. Useful for tracking research impact "
            "and citation trends over time.\n\n"
            "Requires a Scopus ID. Use scopus_search or scopus_get_abstract first "
            "to obtain the scopus_id.\n\n"
            "Prefer scopus_get_citation_count when you only need one total - it is a "
            "single cheap lookup. Use this when the *shape* of the citation curve over "
            "time matters.\n\n"
            "**Access:** needs SCOPUS_INST_TOKEN *and* a request from a subscribing "
            "institution network, on top of SCOPUS_API_KEY. Without both, Elsevier "
            "returns AUTHENTICATION_ERROR even with a valid key - a licensing "
            "restriction, so retrying will not help."
        ),
    )
    async def scopus_get_citations_overview(
        scopus_id: Annotated[
            str,
            Field(description="Scopus numeric ID of the paper"),
        ],
        start_year: Annotated[
            int,
            Field(default=2000, ge=1960, le=2030, description="First year of citation range"),
        ] = 2000,
        end_year: Annotated[
            int,
            Field(default=2025, ge=1960, le=2030, description="Last year of citation range"),
        ] = 2025,
    ) -> dict:
        try:
            return await do_get_citations_overview(client, scopus_id, start_year, end_year)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        except ScopusAuthError as exc:
            raise ToolError(CITATIONS_INST_NOTE) from exc
        except ScopusAPIError as exc:
            raise ToolError(str(exc)) from exc
