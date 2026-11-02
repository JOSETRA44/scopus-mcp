from pydantic import BaseModel
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..cache import NullCache
from ..client import ScopusClient
from ..config import ScopusSettings
from ..services.diagnostics import diagnose


class CapabilitiesResult(BaseModel):
    capabilities: dict[str, str]
    rate_limits: dict[str, dict]
    checked_at: str
    note: str


def register_diagnostics_tools(mcp: FastMCP, settings: ScopusSettings) -> None:
    @mcp.tool(
        name="scopus_check_access",
        description="Test each Scopus endpoint independently using seven live requests. Uses API quota; bypasses cache. Never returns credentials. Run when access is uncertain, not before every search.",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=True),
    )
    async def check_access() -> CapabilitiesResult:
        async with ScopusClient(settings, cache=NullCache()) as client:
            return CapabilitiesResult.model_validate(await diagnose(client))
