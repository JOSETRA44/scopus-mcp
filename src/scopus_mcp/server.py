import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .client import ScopusClient
from .config import get_settings
from .exceptions import ScopusConfigError
from .prompts.research import register_prompts
from .resources.api_reference import register_api_resources
from .resources.syntax_guide import register_resources
from .tools.abstract import register_abstract_tools
from .tools.author import register_author_tools
from .tools.citations import register_citation_tools
from .tools.search import register_search_tools


def create_app() -> FastMCP:
    settings = get_settings()

    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(levelname)s [%(name)s] %(message)s",
    )

    client = ScopusClient(settings)

    @asynccontextmanager
    async def lifespan(app: FastMCP) -> AsyncIterator[None]:
        async with client:
            yield

    mcp = FastMCP(
        name="Scopus Research Assistant",
        instructions=(
            "You have access to the Elsevier Scopus academic database — one of the world's "
            "largest curated collections of research literature.\n\n"
            "## Tools (7)\n"
            "- scopus_search — find papers by topic, author, journal, or year using Boolean queries\n"
            "- scopus_get_abstract — fetch full paper details (abstract, authors, keywords) by ID or DOI\n"
            "- scopus_get_author — retrieve researcher metrics (h-index, citations, publications)\n"
            "- scopus_search_authors — find author profiles by name or ORCID\n"
            "- scopus_search_affiliations — find institutional records\n"
            "- scopus_get_citation_count — quick citation count for a paper\n"
            "- scopus_get_citations_overview — year-by-year citation timeline\n\n"
            "## Prompts (3)\n"
            "- systematic_literature_review — structured SLR search strategy with PICO framework\n"
            "- author_impact_analysis — step-by-step researcher benchmarking workflow\n"
            "- research_trend_query — decade-by-decade trend analysis query set\n\n"
            "## Resources (3)\n"
            "- scopus://search-syntax — complete Boolean query reference\n"
            "- scopus://subject-areas — all SUBJAREA() discipline codes\n"
            "- scopus://api-reference — tool quota costs, identifier formats, workflow patterns\n\n"
            "Start with the scopus://search-syntax resource for query syntax, or use a prompt "
            "to get a structured workflow for your research task."
        ),
        lifespan=lifespan,
    )

    register_search_tools(mcp, client)
    register_abstract_tools(mcp, client)
    register_author_tools(mcp, client)
    register_citation_tools(mcp, client)
    register_resources(mcp)
    register_api_resources(mcp)
    register_prompts(mcp)

    return mcp


def main() -> None:
    load_dotenv()
    try:
        app = create_app()
    except ScopusConfigError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc

    app.run(transport="stdio")


if __name__ == "__main__":
    main()
