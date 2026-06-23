from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from ..client import ScopusClient
from ..exceptions import ScopusAPIError
from ..formatters import format_citation_count, format_citations_overview


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
        if not scopus_id and not doi:
            raise ToolError("Provide at least one of: scopus_id or doi.")

        params: dict = {}
        if scopus_id:
            params["scopus_id"] = scopus_id.strip()
        elif doi:
            params["doi"] = doi.strip()

        try:
            raw = await client.request("/content/abstract/citation-count", params=params)
            return format_citation_count(raw)
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
            "to obtain the scopus_id."
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
        if start_year > end_year:
            raise ToolError("start_year must be less than or equal to end_year.")

        try:
            raw = await client.request(
                "/content/abstract/citations",
                params={
                    "scopus_id": scopus_id.strip(),
                    "date": f"{start_year}-{end_year}",
                    "httpAccept": "application/json",
                },
            )
            return format_citations_overview(raw)
        except ScopusAPIError as exc:
            raise ToolError(str(exc)) from exc
