"""Exercise the real MCP transport with isolated credentials and no upstream network."""
import sys
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_stdio_discovery_validation_and_clean_shutdown(tmp_path):
    # Run the actual CLI/server entry point in a child process. Disable all .env
    # loading and HTTP requests, even if future initialization adds a live probe.
    bootstrap = """
import httpx
import dotenv
from scopus_mcp import config

async def forbidden_request(*args, **kwargs):
    raise RuntimeError('NETWORK_FORBIDDEN_IN_PROTOCOL_TEST')

httpx.AsyncClient.request = forbidden_request
dotenv.load_dotenv = lambda *args, **kwargs: False
config.get_settings = lambda: config.ScopusSettings(_env_file=None)
from scopus_mcp.cli import main
main()
"""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-c", bootstrap],
        cwd=str(tmp_path),
        env={
            "SCOPUS_API_KEY": "test-key-not-real",
            "SCOPUS_INST_TOKEN": "test-token-not-real",
            "SCOPUS_CACHE_TTL": "0",
            "SCOPUS_MAX_RETRIES": "0",
            "SCOPUS_MAX_WAIT_SECONDS": "0",
            "PYTHONUTF8": "1",
        },
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=15)) as session:
            initialized = await session.initialize()
            assert initialized.capabilities.tools is not None
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            assert len(names) == 12
            assert all(tool.outputSchema and tool.annotations.readOnlyHint for tool in listed.tools)
            assert {"scopus_search", "scopus_get_abstract", "scopus_get_citation_count"} <= names
            resources = await session.list_resources()
            assert "scopus://search-syntax" in {str(resource.uri) for resource in resources.resources}
            prompts = await session.list_prompts()
            assert "systematic_literature_review" in {prompt.name for prompt in prompts.prompts}
            resource = await session.read_resource("scopus://search-syntax")
            assert resource.contents
            invalid = await session.call_tool("scopus_search", {"query": "TITLE(test)", "count": 0})
            assert invalid.isError
            assert "NETWORK_FORBIDDEN_IN_PROTOCOL_TEST" not in str(invalid.content)
            unknown = await session.call_tool("scopus_nonexistent_tool", {})
            assert unknown.isError
