from ..models import AbstractResult, BatchAbstractResult
from typing import Annotated
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field
from ..client import ScopusClient
from ..exceptions import ScopusAPIError
from ..services.abstract import (do_get_abstract, do_get_abstracts, IdentifierType, ABSTRACT_ACCESS_NOTE)

def register_abstract_tools(mcp: FastMCP, client: ScopusClient) -> None:

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
        name="scopus_get_abstract",
        description=(
            "Retrieve full paper details from Scopus using any supported identifier.\n\n"
            "Identifier types:\n"
            "- scopus_id — Scopus internal numeric ID (e.g. \"85123456789\")\n"
            "- doi — Digital Object Identifier (e.g. \"10.1016/j.labeco.2024.102505\")\n"
            "- eid — Electronic ID (e.g. \"2-s2.0-85123456789\")\n"
            "- pubmed_id — PubMed/MEDLINE numeric ID\n\n"
            "Returns: title, full abstract, authors with affiliations, keywords, "
            "subject areas, citation count, DOI, and open access status."
        ),
    )
    async def scopus_get_abstract(
        identifier_type: Annotated[
            IdentifierType,
            Field(description="Type of identifier being provided"),
        ],
        identifier: Annotated[
            str,
            Field(description="The identifier value (strip any 'SCOPUS_ID:' prefix from scopus_id)"),
        ],
    ) -> AbstractResult:
        try:
            return AbstractResult.model_validate(await do_get_abstract(client, identifier_type, identifier))
        except (ScopusAPIError, ValueError) as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="scopus_get_abstracts",
        description="Fetch metadata/abstracts for 1–25 identifiers of the same type. Returns each record or its error in input order; access depends on Elsevier entitlements.",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
    )
    async def scopus_get_abstracts(
        identifier_type: IdentifierType,
        identifiers: Annotated[list[str], Field(min_length=1, max_length=25)],
        concurrency: Annotated[int, Field(ge=1, le=5)] = 3,
    ) -> BatchAbstractResult:
        try:
            return BatchAbstractResult.model_validate(await do_get_abstracts(client, identifier_type, identifiers, concurrency))
        except (ScopusAPIError, ValueError) as exc:
            raise ToolError(str(exc)) from exc

# Backward-compatible public imports for existing CLI integrations.
__all__ = ['ABSTRACT_ACCESS_NOTE', 'register_abstract_tools']
