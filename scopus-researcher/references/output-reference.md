# Scopus MCP Output Field Reference

## `scopus_search` Output

```json
{
  "query": "the original search query (echoed back)",
  "total_results": 4821,
  "showing": 10,
  "start_index": 0,
  "items_per_page": 10,
  "papers": [ ...see Paper Object below... ]
}
```

### Paper Object (in search results)

| Field | Type | Description |
|-------|------|-------------|
| `scopus_id` | string | Scopus numeric ID (strip "SCOPUS_ID:" prefix) |
| `eid` | string | Electronic ID (e.g. "2-s2.0-85123456789") |
| `doi` | string? | Digital Object Identifier (if available) |
| `title` | string | Full paper title |
| `first_author` | string | "Surname, Initials" |
| `publication` | string | Journal or conference name |
| `cover_date` | string | ISO date "YYYY-MM-DD" |
| `cited_by_count` | int | Times cited in Scopus |
| `open_access` | bool | Whether freely accessible |
| `scopus_url` | string? | Link to Scopus record |
| `volume` | string? | Journal volume |
| `issue` | string? | Journal issue |
| `page_range` | string? | Page range "1-15" |

**Notes:**
- Fields absent when null/empty (not set to null)
- `cover_date[:4]` gives the year string
- Sort by `cited_by_count` to find most impactful papers

---

## `scopus_get_abstract` Output

```json
{
  "scopus_id": "85123456789",
  "eid": "2-s2.0-85123456789",
  "doi": "10.1038/s41591-024-00001-0",
  "pii": "S0140673623012345",
  "pubmed_id": "38123456",
  "title": "Full paper title",
  "abstract": "The full abstract text, often several paragraphs...",
  "publication": "Nature Medicine",
  "cover_date": "2024-03-01",
  "volume": "30",
  "issue": "3",
  "page_range": "512-524",
  "cited_by_count": 142,
  "open_access": true,
  "language": "eng",
  "authors": [
    {
      "name": "Smith, John",
      "scopus_author_id": "7401234567",
      "affiliation": "MIT, United States"
    }
  ],
  "keywords": ["machine learning", "cancer genomics", "biomarkers"],
  "subject_areas": ["Medicine", "Computer Science", "Biochemistry"]
}
```

**Notes:**
- `abstract` is the complete text (no truncation)
- `authors` always a list (never dict)
- `pii`, `pubmed_id` only present when available
- Use `scopus_author_id` from authors to call `scopus_get_author`

---

## `scopus_get_author` Output

```json
{
  "author_id": "7401234567",
  "name": "Smith, John",
  "surname": "Smith",
  "given_name": "John",
  "initials": "J.",
  "orcid": "0000-0002-1234-5678",
  "h_index": 42,
  "document_count": 120,
  "cited_by_count": 8500,
  "citation_count": 10200,
  "affiliation": {
    "institution": "Massachusetts Institute of Technology",
    "country": "United States",
    "city": "Cambridge"
  },
  "subject_areas": ["Computer Science", "Medicine"],
  "publication_range": {
    "start": "2005",
    "end": "2024"
  }
}
```

**Notes:**
- `cited_by_count` = unique papers that cited any of their work
- `citation_count` = total citation instances (includes duplicates)
- `orcid` and `city` may be absent
- `affiliation` may be absent for inactive/deceased researchers

---

## `scopus_search_authors` Output

```json
{
  "query": "AUTHLASTNAME(Smith) AND AUTHFIRST(J)",
  "total_results": 8,
  "showing": 5,
  "authors": [
    {
      "author_id": "7401234567",
      "name": "Smith, J.",
      "document_count": 120,
      "affiliation": "MIT",
      "country": "United States",
      "orcid": "0000-0002-1234-5678"
    }
  ]
}
```

**Notes:**
- Author names in search results use "Surname, Initials" format
- Always verify by checking `document_count` and `affiliation`
- Use `author_id` in `scopus_get_author` for full profile

---

## `scopus_search_affiliations` Output

```json
{
  "query": "AFFIL(MIT)",
  "total_results": 3,
  "showing": 3,
  "affiliations": [
    {
      "affiliation_id": "60022195",
      "name": "Massachusetts Institute of Technology",
      "city": "Cambridge",
      "country": "United States",
      "document_count": 120000
    }
  ]
}
```

**Notes:**
- Use `affiliation_id` in `AF-ID(...)` queries for precision
- `document_count` = total Scopus-indexed output from this institution

---

## `scopus_get_citation_count` Output

```json
{
  "scopus_id": "85029815652",
  "doi": "10.48550/arxiv.1706.03762",
  "cited_by_count": 85000,
  "self_citation_count": null
}
```

**Notes:**
- Fastest endpoint for citation lookups (50K quota vs 5K for abstract)
- `self_citation_count` may be null depending on API tier

---

## `scopus_get_citations_overview` Output

```json
{
  "total_citations": 85000,
  "citations_by_year": {
    "2017": 12,
    "2018": 450,
    "2019": 3200,
    "2020": 8900,
    "2021": 15000,
    "2022": 20000,
    "2023": 22000,
    "2024": 15000,
    "2025": 400
  }
}
```

**Notes:**
- Years as string keys
- Citation counts as integers
- May not sum exactly to `total_citations` (different counting windows)
- Useful for detecting "sleeping beauties" — papers cited heavily years after publication

---

## Error Responses

When a tool fails, it raises `ToolError` with a message string:

| Scenario | Error message |
|----------|--------------|
| Invalid API key | `Scopus authentication failed (401). Check your SCOPUS_API_KEY` |
| Paper not found | `Resource not found in Scopus: /content/abstract/doi/...` |
| Rate limit exhausted | `Scopus rate limit exceeded after all retries` |
| No identifier provided | `Provide at least one of: scopus_id or doi` |
| Invalid year range | `start_year must be less than or equal to end_year` |
| Network timeout | `Request timed out after 30s` |

**Agent response strategy on errors:**
- 404 Not Found → inform user the identifier may be wrong; try a different identifier type
- Auth errors → tell user to check their `SCOPUS_API_KEY` environment variable
- Rate limit → inform user about quota; suggest spacing out requests
