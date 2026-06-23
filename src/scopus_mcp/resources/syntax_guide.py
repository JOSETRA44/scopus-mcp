from mcp.server.fastmcp import FastMCP

SEARCH_SYNTAX_GUIDE = """\
# Scopus Boolean Query Syntax Reference

## Field Codes for Paper Search (`scopus_search`)

| Code | Searches | Example |
|------|----------|---------|
| `TITLE-ABS-KEY(term)` | Title + Abstract + Keywords | `TITLE-ABS-KEY("machine learning")` |
| `TITLE(term)` | Title only | `TITLE("neural network")` |
| `ABS(term)` | Abstract only | `ABS(CRISPR)` |
| `KEY(term)` | Author keywords | `KEY(sustainability)` |
| `AUTH(name)` | Author name | `AUTH("Smith J")` |
| `AU-ID(id)` | Author Scopus ID | `AU-ID(7401234567)` |
| `ORCID(id)` | Author ORCID | `ORCID(0000-0002-1234-5678)` |
| `AFFIL(text)` | Author affiliation | `AFFIL(MIT)` |
| `AF-ID(id)` | Affiliation Scopus ID | `AF-ID(60027950)` |
| `SRCTITLE(title)` | Journal/conference name | `SRCTITLE(Nature)` |
| `ISSN(number)` | Journal ISSN | `ISSN(0028-0836)` |
| `DOI(id)` | Digital Object Identifier | `DOI(10.1038/s41586-024-00001-0)` |
| `PUBYEAR` | Publication year | `PUBYEAR > 2020` |
| `DOCTYPE(code)` | Document type | `DOCTYPE(ar)` |
| `LANGUAGE(lang)` | Language | `LANGUAGE(English)` |
| `SUBJAREA(code)` | Subject area | `SUBJAREA(COMP)` |
| `OPENACCESS(1)` | Open access only | `OPENACCESS(1)` |

## Boolean Operators (UPPERCASE required)

- `AND` — both terms must be present
- `OR` — either term must be present
- `AND NOT` — exclude papers with term
- `W/n` — within n words (proximity), e.g. `machine W/3 learning`

## Quoting and Wildcards

- Phrase search: use double quotes — `"climate change"`
- Wildcard: `educat*` matches education, educational, educating
- Single char: `wom?n` matches woman, women

## Document Type Codes (`DOCTYPE`)

| Code | Type |
|------|------|
| `ar` | Article |
| `re` | Review |
| `cp` | Conference paper |
| `ch` | Book chapter |
| `bk` | Book |
| `ed` | Editorial |
| `le` | Letter |
| `sh` | Short survey |

## Subject Area Codes (`SUBJAREA`)

| Code | Area |
|------|------|
| `COMP` | Computer Science |
| `MEDI` | Medicine |
| `ENGI` | Engineering |
| `PHYS` | Physics & Astronomy |
| `CHEM` | Chemistry |
| `BUSI` | Business, Management & Accounting |
| `SOCI` | Social Sciences |
| `ENVI` | Environmental Science |
| `MATH` | Mathematics |
| `ECON` | Economics |
| `PSYC` | Psychology |
| `AGRI` | Agricultural & Biological Sciences |

## Practical Examples

```
# Papers on machine learning applied to cancer, post-2018, articles only
TITLE-ABS-KEY("machine learning" AND cancer) AND PUBYEAR > 2018 AND DOCTYPE(ar)

# Climate change reviews in Nature or Science
TITLE-ABS-KEY("climate change") AND SRCTITLE(Nature OR Science) AND DOCTYPE(re)

# Papers by an author at MIT
AUTH("Smith J") AND AFFIL(MIT)

# Open access papers on COVID-19 in Spanish
TITLE-ABS-KEY(COVID-19) AND LANGUAGE(Spanish) AND OPENACCESS(1)

# Human capital and graduate employability in Peru (matches existing scripts)
TITLE-ABS-KEY("human capital" AND "graduate employability" AND Peru)

# Skill mismatch in higher education
TITLE-ABS-KEY("skill mismatch" AND "higher education" AND employability)
```

## Field Codes for Author Search (`scopus_search_authors`)

- `AUTHLASTNAME(Smith)` — last name
- `AUTHFIRST(John)` — first name or initials
- `AF-ID(60027950)` — filter by affiliation ID
- `ORCID(0000-0002-1234-5678)` — ORCID

Example: `AUTHLASTNAME(Smith) AND AUTHFIRST(J) AND AFFIL(Harvard)`

## Rate Limits (Elsevier API quotas per 7 days)

| API | Quota |
|-----|-------|
| Scopus Search | 20,000 requests |
| Abstract Retrieval | 5,000 requests |
| Citation Count | 50,000 requests |

Quotas depend on your institutional subscription.
"""


def register_resources(mcp: FastMCP) -> None:

    @mcp.resource(
        "scopus://search-syntax",
        name="Scopus Search Syntax Guide",
        description=(
            "Complete reference for Scopus Boolean query syntax: field codes, "
            "operators, wildcards, document types, subject areas, and examples."
        ),
        mime_type="text/markdown",
    )
    def search_syntax_guide() -> str:
        return SEARCH_SYNTAX_GUIDE
