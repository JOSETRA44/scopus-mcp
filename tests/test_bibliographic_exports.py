"""Bibliographic interoperability and provenance without network requests."""

import io
import json

import pytest

from scopus_mcp.cli.render import (
    BIBLIOGRAPHIC_FORMATS,
    Emitter,
    build_envelope,
    render_bibtex,
    render_csl_json,
    render_ris,
)
from scopus_mcp.cli.rows import project_paper


PAPER = {
    "scopus_id": "85123",
    "title": "Perú: models & 100% evidence",
    "authors": [{"name": "García, María"}, {"name": "Research and Development Group"}],
    "publication": "Research Journal",
    "document_type": "article",
    "cover_date": "2024-02-29",
    "doi": "10.1000/example",
    "volume": "7",
    "issue": "2",
    "page_range": "10-19",
    "keywords": ["research", "Perú"],
}


def test_csl_preserves_full_record_and_literal_author_names():
    record = json.loads(render_csl_json([PAPER]))[0]
    assert record["id"] == "85123"
    assert record["type"] == "article-journal"
    assert record["DOI"] == PAPER["doi"]
    assert record["container-title"] == PAPER["publication"]
    assert record["author"] == [{"literal": a["name"]} for a in PAPER["authors"]]
    assert record["issued"] == {"date-parts": [[2024, 2, 29]]}


def test_ris_repeats_authors_keywords_and_has_record_boundaries():
    output = render_ris([PAPER])
    assert output.startswith("TY  - JOUR\n")
    assert output.endswith("ER  - \n")
    assert output.count("AU  - ") == 2
    assert output.count("KW  - ") == 2
    assert "SP  - 10\nEP  - 19\n" in output
    assert "DA  - 2024/02/29" in output


def test_ris_cannot_inject_new_records_through_multiline_fields():
    output = render_ris([{"title": "Valid\nER  -\nTY  - JOUR", "scopus_id": "1"}])
    assert sum(line.startswith("TY  -") for line in output.splitlines()) == 1
    assert sum(line.startswith("ER  -") for line in output.splitlines()) == 1


def test_bibtex_escapes_tex_and_protects_literal_names():
    output = render_bibtex([PAPER])
    assert output.startswith("@article{85123,")
    assert r"models \& 100\% evidence" in output
    assert "{Research and Development Group}" in output
    assert "{García, María} and {Research and Development Group}" in output
    malicious = render_bibtex([{"title": r"}{\input{other}} $ _ # ^ ~"}])
    assert r"\input{" not in malicious
    assert r"\textbackslash{}input\{" in malicious


@pytest.mark.parametrize("fmt", BIBLIOGRAPHIC_FORMATS)
def test_emitter_prefers_full_abstract_record_to_flattened_rows(fmt):
    output = io.StringIO()
    emitter = Emitter(fmt)
    emitter.write = output.write
    emitter.emit("abstract", [{"title": "lossy projection"}], data=PAPER)
    assert "lossy projection" not in output.getvalue()
    assert "García" in output.getvalue()
    assert "Research and Development Group" in output.getvalue()


@pytest.mark.parametrize("fmt", BIBLIOGRAPHIC_FORMATS)
def test_unsupported_commands_fail_without_fake_bibliographic_records(fmt):
    with pytest.raises(ValueError, match="search and abstract only"):
        Emitter(fmt).emit("author", [{"name": "Smith"}])


@pytest.mark.parametrize("fmt", BIBLIOGRAPHIC_FORMATS)
def test_export_errors_do_not_pollute_bibliography_stdout(fmt, capsys):
    Emitter(fmt).emit_error("search", "auth", "Access denied", "Run scopus setup")
    captured = capsys.readouterr()
    assert not captured.out
    assert "Access denied" in captured.err


def test_search_first_author_is_marked_as_partial_and_unknown_type_stays_generic():
    record = {"title": "Search result", "first_author": "Smith J.", "publication": "Source"}
    csl = json.loads(render_csl_json([record]))[0]
    assert csl["type"] == "document"
    assert csl["author"] == [{"literal": "Smith J."}]
    assert "Only the first author" in csl["note"]
    assert "Only the first author" in render_bibtex([record])
    assert "Only the first author" in render_ris([record])


def test_missing_fields_are_not_invented_and_invalid_dates_are_omitted():
    csl = json.loads(render_csl_json([{"title": "Unknown", "cover_date": "2023-02-29"}]))[0]
    assert "author" not in csl and "issued" not in csl and "DOI" not in csl
    assert csl["id"].startswith("record-")


def test_csl_and_bibtex_duplicate_identifiers_get_unique_local_keys():
    records = [PAPER, PAPER]
    assert [r["id"] for r in json.loads(render_csl_json(records))] == ["85123", "85123_2"]
    assert "@article{85123_2," in render_bibtex(records)


def test_cached_retrieval_time_survives_serving_a_response():
    envelope = build_envelope("search", [], cached=True, retrieved_at="2020-01-01T00:00:00Z")
    assert envelope["retrieved_at"] == envelope["fetched_at"] == "2020-01-01T00:00:00Z"
    assert envelope["served_at"] != envelope["retrieved_at"]
    assert build_envelope("search", [], cached=True)["retrieved_at"] is None


def test_projection_preserves_unknown_metrics_instead_of_zero_or_false():
    projected = project_paper({"title": "Unknown metrics"})
    assert projected["cited_by_count"] is None
    assert projected["open_access"] is None
    assert project_paper({"cited_by_count": 0, "open_access": False})["cited_by_count"] == 0
