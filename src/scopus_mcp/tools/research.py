"""Typed MCP adapters for references, citing documents and bounded analysis."""
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from ..client import ScopusClient
from ..exceptions import ScopusAPIError
from ..models import PaperSearchResult
from ..services.research import do_analyze_results, do_get_citing_documents, do_get_references


class Reference(BaseModel):
    position: str | None = None
    scopus_id: str | None = None
    doi: str | None = None
    title: str | None = None
    authors: list[str]
    publication: str | None = None
    publication_year: str | None = None
    cover_date: str | None = None
    text: str | None = None
    resolution_status: str | None = None


class ReferencesResult(BaseModel):
    identifier: str
    identifier_type: str
    references: list[Reference]
    showing: int
    total_references: int | None
    start_index: int
    next_start: int | None
    truncated: bool | None
    view: str
    source: str
    retrieved_at: str | None
    limitations: list[str]


class CitingDocumentsResult(PaperSearchResult):
    cited_scopus_id: str
    source: str
    retrieved_at: str | None
    limitations: list[str]


class AffiliationCount(BaseModel):
    key: str
    name: str | None
    documents: int


class CorpusAnalysisResult(BaseModel):
    query: str
    source: str
    view: str
    corpus_size: int
    requested_max_rows: int
    total_results: int
    truncated: bool
    complete_corpus: bool
    duplicate_count: int
    retrieval_times: list[str]
    stop_reason: str
    next_start: int | None
    start_index: int
    by_year: dict[str, int]
    by_publication: dict[str, int]
    by_affiliation: list[AffiliationCount]
    unknown: dict[str, int]
    started_at: str
    completed_at: str
    retrieved_at: str | None
    limitations: list[str]


READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)


def register_research_tools(mcp: FastMCP, client: ScopusClient) -> None:
    @mcp.tool(name="scopus_get_references", annotations=READ_ONLY,
              description="Retrieve one page of a paper's bibliography using Elsevier REF view, with FULL bibliography fallback when REF metadata is absent. Requires appropriate entitlement. Missing references are reported as unavailable, never assumed to mean no references. Follow next_start when present.")
    async def scopus_get_references(
        identifier: str,
        identifier_type: Literal["scopus_id", "doi", "eid", "pubmed_id"] = "scopus_id",
        count: Annotated[int, Field(ge=1, le=100)] = 25,
        start: Annotated[int, Field(ge=0)] = 0,
    ) -> ReferencesResult:
        try:
            return ReferencesResult.model_validate(await do_get_references(client, identifier, identifier_type, count, start))
        except (ScopusAPIError, ValueError) as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(name="scopus_get_citing_documents", annotations=READ_ONLY,
              description="Find Scopus documents citing a paper using REFEID. This search field requires specific Elsevier access permission. Returns a paginated corpus of indexed citing documents, not a universal citation census.")
    async def scopus_get_citing_documents(
        scopus_id: str,
        count: Annotated[int, Field(ge=1, le=25)] = 10,
        start: Annotated[int, Field(ge=0, le=4999)] = 0,
    ) -> CitingDocumentsResult:
        try:
            return CitingDocumentsResult.model_validate(await do_get_citing_documents(client, scopus_id, count, start))
        except (ScopusAPIError, ValueError) as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(name="scopus_analyze_results", annotations=READ_ONLY,
              description="Aggregate a bounded Scopus search corpus by cover year, publication source and affiliation. Defaults to 100 documents; at most 5000. Reports truncation, continuation and unknown metadata explicitly. Counts describe retrieved documents only; do not extrapolate to all literature. Each institution counts once per document.")
    async def scopus_analyze_results(
        query: str,
        max_rows: Annotated[int, Field(ge=1, le=5000)] = 100,
        start: Annotated[int, Field(ge=0, le=4999)] = 0,
        view: Literal["STANDARD", "COMPLETE"] = "STANDARD",
    ) -> CorpusAnalysisResult:
        try:
            return CorpusAnalysisResult.model_validate(await do_analyze_results(client, query, max_rows, start, view))
        except (ScopusAPIError, ValueError) as exc:
            raise ToolError(str(exc)) from exc
