from ..models import AuthorProfile
from typing import Annotated
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field
from ..client import ScopusClient
from ..exceptions import ScopusAPIError, ScopusAuthError
from ..services.author import (do_get_author, AUTHOR_INST_NOTE)

def register_author_tools(mcp: FastMCP, client: ScopusClient) -> None:

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
        name="scopus_get_author",
        description=(
            "Retrieve a researcher's full Scopus profile by their Scopus Author ID.\n\n"
            "Returns: h-index, total citation count, document count, current institutional "
            "affiliation, subject areas, ORCID (if available), and publication year range.\n\n"
            "To find an author's ID, first use scopus_search_authors.\n"
            "Example author IDs: '7401234567' or '57209123456'."
        ),
    )
    async def scopus_get_author(
        author_id: Annotated[
            str,
            Field(description="Scopus Author ID (numeric string, without 'AUTHOR_ID:' prefix)"),
        ],
    ) -> AuthorProfile:
        try:
            return AuthorProfile.model_validate(await do_get_author(client, author_id))
        except ScopusAuthError as exc:
            raise ToolError(f"{AUTHOR_INST_NOTE} ({exc})") from exc
        except (ScopusAPIError, ValueError) as exc:
            raise ToolError(str(exc)) from exc
