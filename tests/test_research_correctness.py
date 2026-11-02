import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from scopus_mcp.exceptions import ScopusAPIError, ScopusNotFoundError
from scopus_mcp.formatters import (
    format_search_results, format_author_search_results, format_affiliation_search_results,
    format_citations_overview, format_citation_count,
)
from scopus_mcp.services.abstract import do_get_abstracts
from scopus_mcp.services.citations import do_get_citations_overview
from scopus_mcp.services.search import iter_scopus_search, do_scopus_search_authors
from scopus_mcp.services.validation import identifier
from scopus_mcp.prompts.research import register_prompts
from mcp.server.fastmcp import FastMCP


@pytest.mark.parametrize("formatter,key", [
    (format_search_results, "papers"), (format_author_search_results, "authors"),
    (format_affiliation_search_results, "affiliations"),
])
def test_empty_error_sentinel_is_not_a_record(formatter, key):
    result = formatter({"search-results": {"opensearch:totalResults": "0", "entry": [{"error": "Result set was empty"}]}})
    assert result[key] == []
    assert result["showing"] == 0


def test_missing_metrics_remain_unknown_and_zero_remains_zero():
    missing = format_search_results({"search-results": {"opensearch:totalResults": "1", "entry": [{"dc:identifier": "SCOPUS_ID:1"}]}})["papers"][0]
    assert missing["cited_by_count"] is None
    assert missing["open_access"] is None
    zero = format_citation_count({"abstract-citations-response": {"result": {"scopus_id": "1", "citationcount": "0"}}})
    assert zero["cited_by_count"] == 0


@pytest.mark.parametrize("raw", [{}, {"search-results": {}}, {"search-results": {"opensearch:totalResults": "0", "entry": [{"error": "unauthorized"}]}}])
def test_missing_or_failed_search_is_not_an_empty_success(raw):
    with pytest.raises(ScopusAPIError):
        format_search_results(raw)


@pytest.mark.parametrize("formatter", [format_citations_overview, format_citation_count])
def test_missing_citation_payload_cannot_claim_zero(formatter):
    with pytest.raises(ScopusNotFoundError):
        formatter({})


async def test_default_citations_end_at_current_year():
    client = SimpleNamespace(request=AsyncMock(return_value={"abstract-citations-response": {"citeInfoMatrix": {"citeInfoMatrixXML": {"citationMatrix": {"citeCount": "0"}}}}}))
    await do_get_citations_overview(client, "123")
    assert client.request.call_args.kwargs["params"]["date"] == f"2000-{datetime.now(timezone.utc).year}"


async def test_author_page_can_continue():
    client = SimpleNamespace(request=AsyncMock(return_value={"search-results": {"opensearch:totalResults": "30", "entry": [{"dc:identifier": "AUTHOR_ID:123"}]}}))
    page = await do_scopus_search_authors(client, "AUTHLASTNAME(Smith)", 1, 25)
    assert client.request.call_args.kwargs["params"]["start"] == 25
    assert page["next_start"] == 26
    assert page["truncated"] is True


async def test_record_provenance_preserves_original_retrieval_time():
    client = SimpleNamespace(retrieved_at="2020-01-01T00:00:00Z", request=AsyncMock(return_value={"search-results": {"opensearch:totalResults": "1", "entry": [{"dc:identifier": "AUTHOR_ID:123"}]}}))
    page = await do_scopus_search_authors(client, "AUTHLASTNAME(Smith)")
    assert page["retrieved_at"] == "2020-01-01T00:00:00Z"
    assert page["authors"][0]["retrieved_at"] == page["retrieved_at"]
    assert page["served_at"] != page["retrieved_at"]


async def test_harvest_reports_offset_truncation():
    client = SimpleNamespace(request=AsyncMock(return_value={"search-results": {"opensearch:totalResults": "8000", "entry": [{"dc:identifier": "SCOPUS_ID:123"}]}}))
    status = {}
    records = [row async for row in iter_scopus_search(client, "TITLE(test)", start=4999, max_rows=10, harvest=status)]
    assert len(records) == 1
    assert status["truncated"] is True
    assert status["stop_reason"] == "offset_limit"
    assert status["total_results"] == 8000
    assert status["next_start"] is None


async def test_batch_preserves_order_and_bounds_concurrency():
    active = peak = 0
    async def request(path, params=None):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0)
        active -= 1
        return {"abstracts-retrieval-response": {"coredata": {"dc:identifier": "SCOPUS_ID:" + path.rsplit("/", 1)[-1]}}}
    result = await do_get_abstracts(SimpleNamespace(request=request), "scopus_id", ["1", "bad", "2", "3"], concurrency=2)
    assert peak <= 2
    assert [item["identifier"] for item in result["results"]] == ["1", "bad", "2", "3"]
    assert result["failed"] == 1
    assert result["succeeded"] == 3


@pytest.mark.parametrize("value,kind", [("../123", "scopus_id"), ("12?view=FULL", "author_id"), (" ", "doi")])
def test_identifiers_cannot_modify_request_paths(value, kind):
    with pytest.raises(ValueError):
        identifier(value, kind)


async def test_systematic_review_includes_start_year_and_explains_citation_bias():
    app = FastMCP("prompt-test")
    register_prompts(app)
    result = await app.get_prompt("systematic_literature_review", {"topic": "cancer", "start_year": "2020"})
    text = result.messages[0].content.text
    assert "PUBYEAR > 2019" in text
    assert "PUBYEAR > 2020" not in text
    assert "(DOCTYPE(ar) OR DOCTYPE(re))" in text
    assert "predefined eligibility criteria" in text
