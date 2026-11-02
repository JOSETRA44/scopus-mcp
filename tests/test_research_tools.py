"""Research services use synthetic upstream records and no credentials/network."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session

from scopus_mcp.exceptions import ScopusAPIError, ScopusAuthError
from scopus_mcp.services.research import do_analyze_results, do_get_citing_documents, do_get_references
from scopus_mcp.tools.research import register_research_tools


def fake_client(*responses):
    return SimpleNamespace(request=AsyncMock(side_effect=list(responses)), retrieved_at="2024-01-01T00:00:00Z")


async def test_resolved_reference_preserves_available_fields_and_unknowns():
    client = fake_client({"abstracts-retrieval-response": {"references": {
        "@total-references": "2", "reference": {"@id": "1", "ref-info": {
            "scopus-id": "123", "title": "Referenced paper", "ce:doi": "10.1000/test",
            "author-list": {"author": {"ce:surname": "García", "ce:given-name": "Ana"}},
        }},
    }}})
    result = await do_get_references(client, "SCOPUS_ID:456", count=1)
    assert result["references"][0]["authors"] == ["García, Ana"]
    assert result["references"][0]["publication"] is None
    assert result["truncated"] is True
    assert result["next_start"] == 1
    client.request.assert_awaited_once_with("/content/abstract/scopus_id/456", {"view": "REF", "refcount": 1, "startref": 0})


async def test_full_bibliography_fallback_parses_official_payload_shape_and_slices():
    entry = {"@id": "2", "ref-info": {
        "refd-itemidlist": {"itemid": [{"@idtype": "SGR", "$": "123"}, {"@idtype": "DOI", "$": "10.1000/test"}]},
        "ref-title": {"ref-titletext": "Reference title"}, "ref-sourcetitle": "Source",
        "ref-publicationyear": {"@first": "2020"},
    }}
    client = fake_client({"abstracts-retrieval-response": {}}, {"abstracts-retrieval-response": {
        "item": {"bibrecord": {"tail": {"bibliography": {"@refcount": "2", "reference": [entry, entry]}}}},
    }})
    result = await do_get_references(client, "456", start=1, count=1)
    assert result["view"] == "FULL"
    assert result["showing"] == 1
    assert result["truncated"] is False
    assert result["references"][0]["publication_year"] == "2020"
    assert result["references"][0]["scopus_id"] == "123"


async def test_missing_bibliography_is_an_error_not_an_empty_result():
    client = fake_client({"abstracts-retrieval-response": {}}, {"abstracts-retrieval-response": {}})
    with pytest.raises(ScopusAPIError, match="unavailable"):
        await do_get_references(client, "456")


@pytest.mark.parametrize("container", [{}, {"@total-references": "4", "reference": []}])
async def test_unresolved_or_absent_references_are_not_reported_as_zero(container):
    client = fake_client({"abstracts-retrieval-response": {"references": container}})
    with pytest.raises(ScopusAPIError, match="did not confirm"):
        await do_get_references(client, "456")


async def test_confirmed_zero_references_is_a_valid_empty_result():
    client = fake_client({"abstracts-retrieval-response": {"references": {"@total-references": "0"}}})
    result = await do_get_references(client, "456")
    assert result["references"] == [] and result["truncated"] is False


async def test_unknown_reference_total_stays_unknown():
    client = fake_client({"abstracts-retrieval-response": {"references": {
        "reference": {"ref-fulltext": "Unresolved citation text"},
    }}})
    result = await do_get_references(client, "456")
    assert result["total_references"] is None and result["truncated"] is None


async def test_auth_failure_does_not_trigger_full_fallback():
    client = fake_client(ScopusAuthError("Denied", status_code=403))
    with pytest.raises(ScopusAuthError):
        await do_get_references(client, "456")
    assert client.request.await_count == 1


async def test_citing_documents_constructs_safe_refeid_and_preserves_pagination():
    client = fake_client({"search-results": {"opensearch:totalResults": "2", "entry": [
        {"dc:identifier": "SCOPUS_ID:111", "dc:title": "Citing paper"},
    ]}})
    result = await do_get_citing_documents(client, "SCOPUS_ID:456", count=1)
    assert result["query"] == "REFEID(2-s2.0-456)"
    assert result["next_start"] == 1
    assert result["cited_scopus_id"] == "456"
    with pytest.raises(ValueError):
        await do_get_citing_documents(client, "456) OR ALL(test)")
    assert client.request.await_count == 1


async def test_analysis_counts_only_bounded_corpus_with_unknown_fields():
    client = fake_client({"search-results": {"opensearch:totalResults": "10", "entry": [
        {"dc:identifier": "SCOPUS_ID:1", "prism:coverDate": "2024-01-01", "prism:publicationName": "Source",
         "affiliation": [{"afid": "20", "affilname": "Institution"}, {"afid": "20", "affilname": "Institution"}]},
        {"dc:identifier": "SCOPUS_ID:2"},
    ]}})
    result = await do_analyze_results(client, "TITLE(test)", max_rows=2)
    assert result["corpus_size"] == 2
    assert result["total_results"] == 10
    assert result["truncated"] is True and result["stop_reason"] == "max_rows"
    assert result["by_year"] == {"2024": 1}
    assert result["by_publication"] == {"Source": 1}
    assert result["by_affiliation"] == [{"key": "id:20", "name": "Institution", "documents": 1}]
    assert result["unknown"] == {"year": 1, "publication": 1, "affiliation": 1}


async def test_analysis_limit_is_validated_before_network():
    client = fake_client()
    with pytest.raises(ValueError):
        await do_analyze_results(client, "TITLE(test)", max_rows=5001)
    client.request.assert_not_awaited()


async def test_final_page_from_nonzero_offset_is_not_a_complete_corpus():
    client = fake_client({"search-results": {"opensearch:totalResults": "2",
        "entry": [{"dc:identifier": "SCOPUS_ID:2", "dc:title": "Last paper"}]}})
    result = await do_analyze_results(client, "TITLE(test)", start=1, max_rows=1)
    assert result["truncated"] is False
    assert result["complete_corpus"] is False
    assert result["corpus_size"] == 1
    assert result["retrieval_times"] == ["2024-01-01T00:00:00Z"]


async def test_research_tools_have_schemas_and_return_errors_on_wire():
    client = fake_client({"abstracts-retrieval-response": {}}, {"abstracts-retrieval-response": {}})
    app = FastMCP("research-test")
    register_research_tools(app, client)
    async with create_connected_server_and_client_session(app) as session:
        tools = (await session.list_tools()).tools
        assert len(tools) == 3
        assert all(t.outputSchema and t.annotations.readOnlyHint for t in tools)
        result = await session.call_tool("scopus_get_references", {"identifier": "456"})
        assert result.isError is True


async def test_analysis_wire_output_is_structured_and_empty_is_explicit():
    client = fake_client({"search-results": {"opensearch:totalResults": "0", "entry": []}})
    app = FastMCP("research-test")
    register_research_tools(app, client)
    async with create_connected_server_and_client_session(app) as session:
        result = await session.call_tool("scopus_analyze_results", {"query": "TITLE(test)"})
        assert not result.isError
        assert result.structuredContent["corpus_size"] == 0
        assert result.structuredContent["truncated"] is False
        assert result.structuredContent["unknown"] == {"year": 0, "publication": 0, "affiliation": 0}
