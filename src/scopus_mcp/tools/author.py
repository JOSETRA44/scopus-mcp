from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from ..client import ScopusClient
from ..exceptions import ScopusAPIError
from ..formatters import format_author_profile


def register_author_tools(mcp: FastMCP, client: ScopusClient) -> None:

    @mcp.tool(
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
    ) -> dict:
        clean = author_id.strip().replace("AUTHOR_ID:", "")
        try:
            raw = await client.request(
                f"/content/author/author_id/{clean}",
                params={"view": "ENHANCED"},
            )
            return format_author_profile(raw)
        except ScopusAPIError as exc:
            raise ToolError(str(exc)) from exc
