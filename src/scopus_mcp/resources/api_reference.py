from mcp.server.fastmcp import FastMCP

SUBJECT_AREAS_GUIDE = """\
# Scopus Subject Area Codes

Use these codes with the `SUBJAREA(code)` field in any `scopus_search` query
to restrict results to a specific discipline.

## Life Sciences & Health

| Code | Subject Area |
|------|-------------|
| `AGRI` | Agricultural and Biological Sciences |
| `BIOC` | Biochemistry, Genetics and Molecular Biology |
| `DENT` | Dentistry |
| `HEAL` | Health Professions |
| `IMMU` | Immunology and Microbiology |
| `MEDI` | Medicine |
| `NEUR` | Neuroscience |
| `NURS` | Nursing |
| `PHAR` | Pharmacology, Toxicology and Pharmaceutics |
| `VETE` | Veterinary |

## Physical Sciences & Engineering

| Code | Subject Area |
|------|-------------|
| `CENG` | Chemical Engineering |
| `CHEM` | Chemistry |
| `COMP` | Computer Science |
| `EART` | Earth and Planetary Sciences |
| `ENER` | Energy |
| `ENGI` | Engineering |
| `ENVI` | Environmental Science |
| `MATE` | Materials Science |
| `MATH` | Mathematics |
| `PHYS` | Physics and Astronomy |

## Social Sciences & Humanities

| Code | Subject Area |
|------|-------------|
| `ARTS` | Arts and Humanities |
| `BUSI` | Business, Management and Accounting |
| `DECI` | Decision Sciences |
| `ECON` | Economics, Econometrics and Finance |
| `PSYC` | Psychology |
| `SOCI` | Social Sciences |

## Multidisciplinary

| Code | Subject Area |
|------|-------------|
| `MULT` | Multidisciplinary |

## Usage Examples

```
# Computer science papers on NLP, post-2018
TITLE-ABS-KEY("natural language processing") AND SUBJAREA(COMP) AND PUBYEAR > 2018

# Medical trials on diabetes treatments
TITLE-ABS-KEY(diabetes AND treatment) AND SUBJAREA(MEDI) AND DOCTYPE(ar)

# Environmental economics papers
TITLE-ABS-KEY("carbon pricing") AND (SUBJAREA(ECON) OR SUBJAREA(ENVI))

# Cross-disciplinary AI + medicine
TITLE-ABS-KEY("artificial intelligence") AND (SUBJAREA(COMP) OR SUBJAREA(MEDI))
```
"""

API_REFERENCE_GUIDE = """\
# Scopus API Reference for MCP Tools

## Rate Limits (per 7-day rolling window)

| API Endpoint | Weekly Quota | Notes |
|-------------|:------------:|-------|
| Scopus Search | 20,000 | `scopus_search`, `scopus_search_authors`, `scopus_search_affiliations` |
| Abstract Retrieval | 5,000 | `scopus_get_abstract` — use sparingly |
| Author Retrieval | 5,000 | `scopus_get_author` |
| Citation Count | 50,000 | `scopus_get_citation_count` — preferred for bulk checks |
| Citations Overview | 5,000 | `scopus_get_citations_overview` |

> Quotas depend on your institutional Elsevier subscription. Free developer keys have lower limits.

## Tool Quick Reference

### `scopus_search` → papers list
- **Best for:** Topic discovery, filtering by year/type/journal/author
- **Key params:** `query` (Boolean), `count` (1–25), `start` (pagination offset)
- **Quota cost:** 1 per call
- **Example:** `TITLE-ABS-KEY("machine learning") AND PUBYEAR > 2020`

### `scopus_get_abstract` → full paper record
- **Best for:** Full metadata, authors, keywords, affiliations
- **Key params:** `identifier_type` (scopus_id|doi|eid|pubmed_id), `identifier`
- **Quota cost:** 1 per call from the 5,000 Abstract pool — use wisely
- **Tip:** Use `scopus_get_citation_count` first if you only need citations

### `scopus_get_author` → researcher profile
- **Best for:** h-index, career metrics, affiliation
- **Key params:** `author_id` (numeric string)
- **Workflow:** First run `scopus_search_authors` to find the ID

### `scopus_search_authors` → author list
- **Best for:** Finding researcher IDs by name/ORCID/institution
- **Key params:** `query` (author Boolean), `count`
- **Example:** `AUTHLASTNAME(Smith) AND AUTHFIRST(J) AND AFFIL(MIT)`

### `scopus_search_affiliations` → institution list
- **Best for:** Finding affiliation IDs for `AF-ID()` filters
- **Key params:** `query`, `count`
- **Example:** `AFFIL(Harvard) AND COUNTRY(United States)`

### `scopus_get_citation_count` → single number
- **Best for:** Quick citation screening of many papers
- **Key params:** `scopus_id` OR `doi`
- **Quota cost:** 1 per call from the generous 50,000 pool

### `scopus_get_citations_overview` → year-by-year dict
- **Best for:** Citation trend charts, impact trajectory
- **Key params:** `scopus_id`, `start_year`, `end_year`

## Efficient Workflow Patterns

### Pattern 1 — Topic → High-impact papers
1. `scopus_search` with broad query → get `scopus_id` list
2. `scopus_get_citation_count` in bulk → rank by citations (uses 50K pool)
3. `scopus_get_abstract` only for top N papers → rich metadata (uses 5K pool)

### Pattern 2 — Author benchmarking
1. `scopus_search_authors` → get `author_id`
2. `scopus_get_author` → h-index, document count
3. `scopus_search` with `AU-ID(<id>)` → paper list
4. `scopus_get_citations_overview` for top papers → trend data

### Pattern 3 — Journal/venue discovery
1. `scopus_search` with `DOCTYPE(ar)` on topic → inspect `publication` field in results
2. Identify top journals → verify with `SRCTITLE(<name>)` filter

## Identifier Format Guide

| Type | Format | Example |
|------|--------|---------|
| Scopus ID | Numeric string | `"85123456789"` |
| DOI | `10.xxxx/...` | `"10.1016/j.labeco.2024.102505"` |
| EID | `2-s2.0-` prefix | `"2-s2.0-85123456789"` |
| PubMed ID | Numeric string | `"38541234"` |
| Author ID | Numeric string | `"7401234567"` |
| ORCID | `0000-XXXX-XXXX-XXXX` | `"0000-0002-1234-5678"` |

## Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SCOPUS_API_KEY` | _(required)_ | Elsevier API key from dev.elsevier.com |
| `SCOPUS_INST_TOKEN` | `None` | Institutional token for full-text/off-campus access |
| `SCOPUS_CACHE_TTL` | `300` | Response cache TTL in seconds (0 = disabled) |
| `SCOPUS_MAX_RETRIES` | `3` | Retries on HTTP 429 |
| `LOG_LEVEL` | `INFO` | `DEBUG` · `INFO` · `WARNING` · `ERROR` |
"""


def register_api_resources(mcp: FastMCP) -> None:

    @mcp.resource(
        "scopus://subject-areas",
        name="Scopus Subject Area Codes",
        description=(
            "Complete list of Scopus SUBJAREA() codes organized by discipline. "
            "Use these codes to filter searches to a specific academic field."
        ),
        mime_type="text/markdown",
    )
    def subject_areas_guide() -> str:
        return SUBJECT_AREAS_GUIDE

    @mcp.resource(
        "scopus://api-reference",
        name="Scopus MCP API Reference",
        description=(
            "Quick reference for all 7 Scopus MCP tools: rate limits, quota costs, "
            "identifier formats, and recommended workflow patterns."
        ),
        mime_type="text/markdown",
    )
    def api_reference_guide() -> str:
        return API_REFERENCE_GUIDE
