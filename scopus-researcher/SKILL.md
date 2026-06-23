---
name: scopus-researcher
description: >
  Expert academic researcher using the Scopus MCP. Finds papers, retrieves
  full abstracts, builds author profiles, analyzes citation impact, and
  constructs advanced Boolean queries across the Elsevier Scopus database.
  Activate when asked to search for academic papers, analyze research trends,
  find citations, profile researchers, or explore scholarly literature.
version: "1.0.0"
license: MIT

category: research
tags:
  - scopus
  - academic
  - research
  - citations
  - elsevier
  - literature-review
  - bibliometrics

mcp:
  server: scopus
  tools:
    - scopus_search
    - scopus_get_abstract
    - scopus_get_author
    - scopus_search_authors
    - scopus_search_affiliations
    - scopus_get_citation_count
    - scopus_get_citations_overview
  resources:
    - scopus://search-syntax

models:
  recommended:
    - claude-sonnet-4-6

capabilities:
  - literature_search
  - citation_analysis
  - author_profiling
  - research_trend_mapping
  - bibliometric_analysis

related_skills:
  - mcp-creator
---

# Scopus Researcher

Expert academic research assistant powered by the Elsevier Scopus MCP.
Searches over 100 million scholarly records across journals, conferences, and books.

## When to Use This Skill

- "Find papers about X published after 2020"
- "Who are the top researchers in Y field?"
- "How many times has this paper been cited?"
- "What's the citation trend for paper Z over the last 10 years?"
- "Find all papers by author X at institution Y"
- "Search for reviews on topic Z in high-impact journals"
- "Analyze the research output of MIT on machine learning"

## MCP Setup

Ensure the Scopus MCP is running. The `scopus-dev` entry in `.antigravity.json` points to the local install:

```json
{
  "mcpServers": {
    "scopus": {
      "command": "uvx",
      "args": ["scopus-mcp"],
      "env": { "SCOPUS_API_KEY": "your_key_here" }
    }
  }
}
```

Read the `scopus://search-syntax` resource for the full Boolean query reference before constructing complex queries.

---

## Workflow: Literature Search

**Goal:** Find papers on a topic, filter by year/type, retrieve full details.

```
Step 1 — Broad search
  scopus_search(query="TITLE-ABS-KEY(\"machine learning\" AND cancer)", count=10)

Step 2 — Retrieve full abstract for top result
  scopus_get_abstract(identifier_type="scopus_id", identifier="85123456789")

Step 3 — Check citation count
  scopus_get_citation_count(scopus_id="85123456789")

Step 4 — Paginate for more results
  scopus_search(query="...", count=10, start=10)
```

## Workflow: Author Profile

**Goal:** Find a researcher and analyze their impact.

```
Step 1 — Find author by name
  scopus_search_authors(query="AUTHLASTNAME(Smith) AND AUTHFIRST(J) AND AFFIL(Harvard)")

Step 2 — Get full profile with h-index
  scopus_get_author(author_id="7401234567")

Step 3 — See their papers
  scopus_search(query="AU-ID(7401234567)", count=10)
```

## Workflow: Citation Impact Analysis

**Goal:** Understand how a paper's citations grew over time.

```
Step 1 — Find the paper
  scopus_search(query="TITLE(\"Attention Is All You Need\")", count=1)

Step 2 — Year-by-year citation trend
  scopus_get_citations_overview(
    scopus_id="85029815652",
    start_year=2017,
    end_year=2025
  )
```

## Workflow: Institutional Research Audit

**Goal:** Analyze research output of a university on a topic.

```
Step 1 — Find the institution's Scopus ID
  scopus_search_affiliations(query="AFFIL(MIT)")

Step 2 — Search papers from that institution
  scopus_search(
    query="AF-ID(60022195) AND TITLE-ABS-KEY(\"deep learning\")",
    count=25
  )
```

---

## Tool Reference

### `scopus_search` — Search Papers

```python
scopus_search(
  query    = "TITLE-ABS-KEY(\"climate change\" AND \"machine learning\")",
  count    = 10,     # 1–25 results per page
  start    = 0,      # pagination offset
  view     = "STANDARD"  # or "COMPLETE" for more fields
)
```

**Returns:**
```json
{
  "query": "...",
  "total_results": 4821,
  "showing": 10,
  "papers": [
    {
      "scopus_id": "85123456789",
      "doi": "10.1038/s41591-024-00001-0",
      "title": "Deep learning for cancer genomics",
      "first_author": "Smith, J.",
      "publication": "Nature Medicine",
      "cover_date": "2024-03-01",
      "cited_by_count": 142,
      "open_access": true
    }
  ]
}
```

**Key query patterns:**
| Pattern | Use case |
|---------|----------|
| `TITLE-ABS-KEY("term")` | Most comprehensive search |
| `AND PUBYEAR > 2020` | Filter by year |
| `AND DOCTYPE(ar)` | Articles only |
| `AND DOCTYPE(re)` | Reviews only |
| `AND OPENACCESS(1)` | Open access only |
| `AND LANGUAGE(English)` | Language filter |
| `AND SUBJAREA(COMP)` | Computer science papers |

---

### `scopus_get_abstract` — Full Paper Details

```python
scopus_get_abstract(
  identifier_type = "doi",          # scopus_id | doi | eid | pubmed_id
  identifier      = "10.1038/s41591-024-00001-0"
)
```

**Returns:** title, full abstract text, all authors with affiliations and author IDs, DOI, keywords, subject areas, citation count, open access status.

**Tip:** DOIs can contain slashes and dots — pass them raw, the tool handles encoding automatically.

---

### `scopus_get_author` — Researcher Profile

```python
scopus_get_author(author_id="7401234567")
```

**Returns:**
```json
{
  "author_id": "7401234567",
  "name": "Smith, John",
  "h_index": 42,
  "document_count": 120,
  "cited_by_count": 8500,
  "citation_count": 10200,
  "affiliation": {
    "institution": "Massachusetts Institute of Technology",
    "country": "United States"
  },
  "subject_areas": ["Computer Science", "Medicine"],
  "publication_range": {"start": "2005", "end": "2024"}
}
```

---

### `scopus_search_authors` — Find Researchers

```python
scopus_search_authors(
  query = "AUTHLASTNAME(LeCun) AND AUTHFIRST(Y)",
  count = 5
)
```

**Common query patterns:**
- `AUTHLASTNAME(Smith) AND AUTHFIRST(John)` — full name
- `ORCID(0000-0002-1234-5678)` — by ORCID
- `AUTHLASTNAME(García) AND AFFIL(UNAM)` — name + institution

---

### `scopus_search_affiliations` — Find Institutions

```python
scopus_search_affiliations(
  query = "AFFIL(Stanford University) AND COUNTRY(United States)",
  count = 5
)
```

**Returns:** `affiliation_id`, `name`, `city`, `country`, `document_count`.

Use the `affiliation_id` in `AF-ID(...)` queries to filter papers by institution.

---

### `scopus_get_citation_count` — Quick Citation Lookup

```python
# By Scopus ID:
scopus_get_citation_count(scopus_id="85029815652")

# By DOI:
scopus_get_citation_count(doi="10.1145/3292500.3330924")
```

Lightweight endpoint — use this instead of `scopus_get_abstract` when only citations are needed.

---

### `scopus_get_citations_overview` — Year-by-Year Trend

```python
scopus_get_citations_overview(
  scopus_id  = "85029815652",
  start_year = 2017,
  end_year   = 2025
)
```

**Returns:**
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
    "2024": 15000
  }
}
```

---

## Advanced Query Patterns

See `references/query-patterns.md` for the complete syntax guide.

### Multi-field Boolean
```
TITLE-ABS-KEY("deep learning" AND (cancer OR tumor)) AND PUBYEAR > 2019 AND DOCTYPE(ar)
```

### Author + Field + Year
```
AU-ID(7401234567) AND TITLE-ABS-KEY("neural network") AND PUBYEAR > 2018
```

### Institution research profile
```
AF-ID(60027950) AND SUBJAREA(COMP) AND DOCTYPE(ar) AND PUBYEAR > 2020
```

### Proximity search (within 3 words)
```
TITLE(machine W/3 learning)
```

### Highly cited review articles
```
TITLE-ABS-KEY("federated learning") AND DOCTYPE(re) AND PUBYEAR > 2020
```

---

## Rate Limits & Best Practices

| API | Quota / 7 days |
|-----|---------------|
| Search | 20,000 requests |
| Abstract Retrieval | 5,000 requests |
| Citation Count | 50,000 requests |

**Agent guidelines:**
1. Always search first (`scopus_search`) before fetching abstracts — avoid unnecessary `scopus_get_abstract` calls on papers the user doesn't need
2. Use `scopus_get_citation_count` (50K quota) instead of `scopus_get_abstract` (5K quota) when only citation counts are needed
3. Use pagination (`start` parameter) rather than increasing `count` beyond 25
4. Cache responses in your session — identical queries return cached results automatically (5-min TTL)
5. When the user asks for "top papers," sort by citation count by adding `&sort=citedby-count` context — the tool doesn't sort but you can re-rank the returned list

---

## Installation

### Install this skill
```bash
npx skills add <github-user>/scopus-mcp@scopus-researcher
```

### Install the MCP server
```bash
# Development (local)
cd scopus-mcp && uv sync

# Production (published to PyPI)
uvx scopus-mcp
```

### Reference Files

| File | Contents |
|------|----------|
| [Query Patterns](references/query-patterns.md) | Full Boolean syntax reference with 30+ examples |
| [Workflow Examples](references/workflow-examples.md) | End-to-end research workflows for common tasks |
| [Output Reference](references/output-reference.md) | Complete field-by-field output documentation |
