import urllib.parse
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from ..client import ScopusClient
from ..exceptions import ScopusAPIError, ScopusAuthError
from ..formatters import format_abstract


def register_abstract_tools(mcp: FastMCP, client: ScopusClient) -> None:

    @mcp.tool(
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
            Literal["scopus_id", "doi", "eid", "pubmed_id"],
            Field(description="Type of identifier being provided"),
        ],
        identifier: Annotated[
            str,
            Field(description="The identifier value (strip any 'SCOPUS_ID:' prefix from scopus_id)"),
        ],
    ) -> dict:
        clean = identifier.strip()
        # Strip common prefixes users might include
        for prefix in ("SCOPUS_ID:", "EID:", "PMID:"):
            if clean.upper().startswith(prefix):
                clean = clean[len(prefix):]
                break

        path_map: dict[str, str] = {
            "scopus_id": f"/content/abstract/scopus_id/{clean}",
            "doi": f"/content/abstract/doi/{urllib.parse.quote(clean, safe='')}",
            "eid": f"/content/abstract/eid/{clean}",
            "pubmed_id": f"/content/abstract/pubmed_id/{clean}",
        }
        path = path_map[identifier_type]

        try:
            try:
                raw = await client.request(path, params={"view": "FULL"})
                return format_abstract(raw)
            except ScopusAuthError:
                # Free API keys can't access FULL/META_ABS views — fall back to META
                raw = await client.request(path, params={"view": "META"})
                result = format_abstract(raw)
                result["access_note"] = (
                    "Returned metadata only (view=META). Abstract text, full author list, "
                    "and keywords require an institutional Elsevier token. "
                    "Set SCOPUS_INST_TOKEN in your .env file for full access."
                )
                return result
        except ScopusAPIError as exc:
            raise ToolError(str(exc)) from exc
