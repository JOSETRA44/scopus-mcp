"""Exercise the public MCP wire contract with an in-memory session."""
from unittest.mock import AsyncMock

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from scopus_mcp import server
from scopus_mcp.client import ScopusClient


@pytest.fixture
def app(monkeypatch, settings):
    monkeypatch.setattr(server, "get_settings", lambda: settings)
    return server.create_app()


async def test_discovery_exposes_schemas_and_readonly_annotations(app):
    async with create_connected_server_and_client_session(app) as session:
        tools = (await session.list_tools()).tools
        assert len(tools) >= 8
        for tool in tools:
            assert tool.outputSchema is not None, tool.name
            assert tool.annotations.readOnlyHint is True
        for name in ("scopus_search_authors", "scopus_search_affiliations"):
            tool = next(tool for tool in tools if tool.name == name)
            assert "start" in tool.inputSchema["properties"]


async def test_search_returns_structured_data_and_empty_results(app, monkeypatch):
    monkeypatch.setattr(ScopusClient, "request", AsyncMock(return_value={
        "search-results": {"opensearch:totalResults": "0", "entry": [{"error": "Result set was empty"}]}
    }))
    async with create_connected_server_and_client_session(app) as session:
        result = await session.call_tool("scopus_search", {"query": "TITLE(test)"})
        assert result.isError is False
        assert result.structuredContent["papers"] == []
        assert result.structuredContent["showing"] == 0


async def test_missing_citation_payload_is_tool_error(app, monkeypatch):
    monkeypatch.setattr(ScopusClient, "request", AsyncMock(return_value={}))
    async with create_connected_server_and_client_session(app) as session:
        result = await session.call_tool("scopus_get_citation_count", {"scopus_id": "123"})
        assert result.isError is True
        assert "No citation data" in result.content[0].text


@pytest.mark.parametrize("arguments", [
    {"query": "   "}, {"query": "TITLE(test)", "view": "INVALID"},
    {"query": "TITLE(test)", "start": 4999, "count": 10},
])
async def test_invalid_search_is_rejected_before_network(app, monkeypatch, arguments):
    request = AsyncMock()
    monkeypatch.setattr(ScopusClient, "request", request)
    async with create_connected_server_and_client_session(app) as session:
        result = await session.call_tool("scopus_search", arguments)
        assert result.isError is True
        request.assert_not_awaited()
