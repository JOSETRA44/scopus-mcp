"""Unit tests for formatters — no network access required."""

import pytest

from scopus_mcp.formatters import (
    format_abstract,
    format_author_profile,
    format_author_search_results,
    format_citation_count,
    format_search_results,
    _safe_get,
    _strip_scopus_id,
)


class TestSafeGet:
    def test_existing_key(self):
        assert _safe_get({"a": 1}, "a") == 1

    def test_missing_key_returns_default(self):
        assert _safe_get({}, "missing") is None
        assert _safe_get({}, "missing", default="x") == "x"

    def test_nested_access(self):
        obj = {"a": {"b": {"c": 42}}}
        assert _safe_get(obj, "a", "b", "c") == 42

    def test_list_access(self):
        assert _safe_get([10, 20, 30], 1) == 20

    def test_type_error_returns_default(self):
        assert _safe_get(None, "key") is None
        assert _safe_get("string", "key") is None


class TestStripScopusId:
    def test_strips_prefix(self):
        assert _strip_scopus_id("SCOPUS_ID:85123456789") == "85123456789"

    def test_no_prefix_unchanged(self):
        assert _strip_scopus_id("85123456789") == "85123456789"


class TestFormatSearchResults:
    SAMPLE_RAW = {
        "search-results": {
            "opensearch:totalResults": "2",
            "opensearch:itemsPerPage": "2",
            "opensearch:startIndex": "0",
            "entry": [
                {
                    "dc:identifier": "SCOPUS_ID:85001",
                    "eid": "2-s2.0-85001",
                    "dc:title": "Machine Learning in Medicine",
                    "dc:creator": "Smith, J.",
                    "prism:publicationName": "Nature Medicine",
                    "prism:coverDate": "2024-01-01",
                    "prism:doi": "10.1038/s41591-024-00001-0",
                    "citedby-count": "42",
                    "openaccess": "1",
                    "link": [{"@ref": "scopus", "@href": "https://www.scopus.com/record/85001"}],
                },
                {
                    "dc:identifier": "SCOPUS_ID:85002",
                    "eid": "2-s2.0-85002",
                    "dc:title": "Deep Learning Survey",
                    "dc:creator": "Jones, A.",
                    "prism:publicationName": "IEEE TPAMI",
                    "prism:coverDate": "2023-06-01",
                    "citedby-count": "120",
                    "openaccess": "0",
                    "link": [],
                },
            ],
        }
    }

    def test_total_results(self):
        result = format_search_results(self.SAMPLE_RAW)
        assert result["total_results"] == 2
        assert result["showing"] == 2
        assert result["start_index"] == 0

    def test_paper_fields(self):
        papers = format_search_results(self.SAMPLE_RAW)["papers"]
        assert papers[0]["scopus_id"] == "85001"
        assert papers[0]["title"] == "Machine Learning in Medicine"
        assert papers[0]["doi"] == "10.1038/s41591-024-00001-0"
        assert papers[0]["cited_by_count"] == 42
        assert papers[0]["open_access"] is True

    def test_open_access_false(self):
        papers = format_search_results(self.SAMPLE_RAW)["papers"]
        assert papers[1]["open_access"] is False

    def test_query_echo(self):
        result = format_search_results(self.SAMPLE_RAW, query="TITLE(test)")
        assert result["query"] == "TITLE(test)"

    def test_empty_results(self):
        raw = {"search-results": {"opensearch:totalResults": "0", "entry": []}}
        result = format_search_results(raw)
        assert result["total_results"] == 0
        assert result["papers"] == []


class TestFormatAbstract:
    SAMPLE_RAW = {
        "abstracts-retrieval-response": {
            "coredata": {
                "dc:identifier": "SCOPUS_ID:85001",
                "eid": "2-s2.0-85001",
                "dc:title": "Test Paper Title",
                "dc:description": "This paper studies important things.",
                "prism:publicationName": "Test Journal",
                "prism:coverDate": "2024-01-15",
                "prism:doi": "10.1234/test.2024",
                "citedby-count": "10",
                "openaccess": "0",
            },
            "authors": {
                "author": [
                    {
                        "@auid": "7401234567",
                        "ce:surname": "Smith",
                        "ce:given-name": "John",
                        "affiliation": {"ce:text": "MIT, USA"},
                    }
                ]
            },
            "authkeywords": {
                "author-keyword": [
                    {"$": "machine learning"},
                    {"$": "cancer"},
                ]
            },
            "subject-areas": {
                "subject-area": [
                    {"$": "Computer Science"},
                    {"$": "Medicine"},
                ]
            },
        }
    }

    def test_basic_fields(self):
        result = format_abstract(self.SAMPLE_RAW)
        assert result["scopus_id"] == "85001"
        assert result["title"] == "Test Paper Title"
        assert result["doi"] == "10.1234/test.2024"
        assert result["cited_by_count"] == 10

    def test_authors(self):
        result = format_abstract(self.SAMPLE_RAW)
        assert len(result["authors"]) == 1
        assert result["authors"][0]["name"] == "Smith, John"
        assert result["authors"][0]["scopus_author_id"] == "7401234567"
        assert result["authors"][0]["affiliation"] == "MIT, USA"

    def test_keywords(self):
        result = format_abstract(self.SAMPLE_RAW)
        assert result["keywords"] == ["machine learning", "cancer"]

    def test_subject_areas(self):
        result = format_abstract(self.SAMPLE_RAW)
        assert "Computer Science" in result["subject_areas"]


class TestFormatAuthorProfile:
    SAMPLE_RAW = {
        "author-retrieval-response": [
            {
                "coredata": {
                    "dc:identifier": "AUTHOR_ID:7401234567",
                    "document-count": "85",
                    "cited-by-count": "1200",
                    "citation-count": "1500",
                },
                "h-index": "22",
                "author-profile": {
                    "preferred-name": {
                        "ce:surname": "Smith",
                        "ce:given-name": "John",
                        "ce:initials": "J.",
                    },
                    "publication-range": {"@start": "2005", "@end": "2024"},
                },
                "subject-areas": {
                    "subject-area": [{"$": "Computer Science"}]
                },
            }
        ]
    }

    def test_basic_fields(self):
        result = format_author_profile(self.SAMPLE_RAW)
        assert result["author_id"] == "7401234567"
        assert result["name"] == "Smith, John"
        assert result["h_index"] == 22
        assert result["document_count"] == 85
        assert result["cited_by_count"] == 1200

    def test_publication_range(self):
        result = format_author_profile(self.SAMPLE_RAW)
        assert result["publication_range"]["start"] == "2005"
        assert result["publication_range"]["end"] == "2024"


class TestFormatCitationCount:
    def test_basic(self):
        raw = {
            "abstract-citations-response": {
                "result": [
                    {"scopus_id": "85001", "doi": "10.1234/test", "citationcount": "42"}
                ]
            }
        }
        result = format_citation_count(raw)
        assert result["cited_by_count"] == 42
        assert result["scopus_id"] == "85001"
