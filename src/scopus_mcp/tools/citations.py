from ..models import CitationCountResult, CitationsOverviewResult
from typing import Annotated
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field
from ..client import ScopusClient
from ..exceptions import ScopusAPIError, ScopusAuthError
from ..services.citations import (do_get_citation_count, do_get_citations_overview, CITATIONS_INST_NOTE)

def register_citation_tools(mcp: FastMCP, client: ScopusClient) -> None:

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
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
    ) -> CitationCountResult:
        try:
            return CitationCountResult.model_validate(await do_get_citation_count(client, scopus_id, doi))
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        except ScopusAuthError as exc:
            raise ToolError(CITATIONS_INST_NOTE) from exc
        except (ScopusAPIError, ValueError) as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
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
            "Access depends on your Elsevier endpoint entitlement. An institutional "
            "token or approved network may be required; use scopus_check_access to "
            "diagnose access before retrying authorization failures."
        ),
    )
    async def scopus_get_citations_overview(
        scopus_id: Annotated[
            str,
            Field(description="Scopus numeric ID of the paper"),
        ],
        start_year: Annotated[
            int,
            Field(default=2000, ge=1960, description="First year of citation range"),
        ] = 2000,
        end_year: Annotated[
            int | None,
            Field(default=None, ge=1960, description="Last year of citation range; defaults to current year"),
        ] = None,
    ) -> CitationsOverviewResult:
        try:
            return CitationsOverviewResult.model_validate(await do_get_citations_overview(client, scopus_id, start_year, end_year))
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        except ScopusAuthError as exc:
            raise ToolError(CITATIONS_INST_NOTE) from exc
        except (ScopusAPIError, ValueError) as exc:
            raise ToolError(str(exc)) from exc
