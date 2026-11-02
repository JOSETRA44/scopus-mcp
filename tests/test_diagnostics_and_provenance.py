import json

import httpx

from .conftest import paper_entry


def response(request):
    if request.url.path == "/content/search/scopus":
        return httpx.Response(200, json={"search-results": {
            "opensearch:totalResults": "100", "opensearch:itemsPerPage": "1",
            "entry": [paper_entry(int(request.url.params.get("start", 0)))]}})
    if request.url.path == "/content/abstract/citation-count":
        return httpx.Response(200, json={"abstract-citations-response": {"result": {"citationcount": "2"}}})
    if request.url.path == "/content/search/author":
        return httpx.Response(200, json={"search-results": {"opensearch:totalResults": "0", "entry": []}})
    return httpx.Response(403, json={})


def test_check_separates_endpoints_and_bypasses_cache(cli, fake_scopus, capsys):
    api = fake_scopus(response)
    assert cli("check", "-f", "json") == 0
    first = json.loads(capsys.readouterr().out)
    assert first["data"]["capabilities"]["citation-count"] == "ok"
    assert first["data"]["capabilities"]["citations"].startswith("forbidden")
    assert first["data"]["capabilities"]["search-authors"] == "ok"
    assert first["data"]["capabilities"]["author"].startswith("forbidden")
    assert cli("check", "-f", "json") == 0
    second = json.loads(capsys.readouterr().out)
    assert not second["cached"]
    assert len(api.requests) == 14


def test_bulk_records_partial_corpus(cli, fake_scopus, capsys, tmp_path):
    fake_scopus(response)
    record = tmp_path / "search-record.json"
    assert cli("search", "TITLE(x)", "--all", "--max", "2", "--record", str(record), "-f", "json") == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["meta"]["truncated"] is True
    assert result["meta"]["stop_reason"] == "max_rows"
    assert "Partial corpus" in captured.err
    manifest = json.loads(record.read_text(encoding="utf-8"))
    assert manifest["count"] == 2
    assert manifest["parameters"]["query"] == "TITLE(x)"
    assert manifest["meta"]["total_results"] == 100
    assert "test-key-not-real" not in record.read_text(encoding="utf-8")


def test_cached_output_preserves_retrieval_time(cli, fake_scopus, capsys):
    fake_scopus(response)
    cli("search", "TITLE(x)", "-f", "json")
    first = json.loads(capsys.readouterr().out)
    cli("search", "TITLE(x)", "-f", "json")
    second = json.loads(capsys.readouterr().out)
    assert second["cached"]
    assert second["retrieved_at"] == first["retrieved_at"]
    assert second["fetched_at"] == first["retrieved_at"]


def test_unsupported_export_fails_before_network(cli, fake_scopus):
    def forbidden(request):
        raise AssertionError("Should validate before any HTTP request")
    fake_scopus(forbidden)
    assert cli("author", "123", "-f", "bibtex") == 2


def test_record_and_output_cannot_overwrite_one_another(cli, tmp_path):
    path = tmp_path / "result.json"
    path.write_text("preserve", encoding="utf-8")
    assert cli("search", "TITLE(x)", "--record", str(path), "-o", str(path)) == 2
    assert path.read_text(encoding="utf-8") == "preserve"


def test_bulk_bibtex_exports_full_metadata(cli, fake_scopus, capsys):
    fake_scopus(response)
    assert cli("search", "TITLE(x)", "--all", "--max", "2", "-f", "bibtex") == 0
    out = capsys.readouterr().out
    assert "10.1000/test.0" in out and "10.1000/test.1" in out


def test_record_failure_never_emits_success_json(cli, fake_scopus, capsys, tmp_path):
    fake_scopus(response)
    assert cli("search", "TITLE(x)", "--record", str(tmp_path / "missing" / "record.json"), "-f", "json") == 1
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_check_rejects_empty_and_error_roots(cli, fake_scopus, capsys):
    fake_scopus(lambda request: httpx.Response(200, json={"search-results": {},
        "author-retrieval-response": [{"error-response": {"error-code": "bad"}}],
        "abstracts-retrieval-response": {}, "abstract-citations-response": {}}))
    assert cli("check", "-f", "json") == 1
    data = json.loads(capsys.readouterr().out)["data"]
    assert all(value != "ok" for value in data["capabilities"].values())
