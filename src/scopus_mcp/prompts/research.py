from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:

    @mcp.prompt(
        name="systematic_literature_review",
        description=(
            "Generate a structured Scopus search strategy for a systematic literature review (SLR). "
            "Produces PICO-framed Boolean queries, inclusion/exclusion criteria, and a step-by-step "
            "workflow using scopus_search and scopus_get_abstract tools."
        ),
    )
    def systematic_literature_review(
        topic: str,
        population: str = "",
        intervention: str = "",
        outcome: str = "",
        start_year: int = 2015,
    ) -> str:
        pico_block = ""
        if population or intervention or outcome:
            pico_block = f"""
## PICO Framework
| Element | Value |
|---------|-------|
| Population | {population or "_(not specified)_"} |
| Intervention/Exposure | {intervention or "_(not specified)_"} |
| Outcome | {outcome or "_(not specified)_"} |
"""

        return f"""# Systematic Literature Review — Scopus Search Strategy

## Topic
{topic}
{pico_block}
## Step 1 — Broad discovery query

Run `scopus_search` with this query to get a baseline result count:

```
TITLE-ABS-KEY("{topic}") AND PUBYEAR > {start_year}
```

## Step 2 — Focused query (articles and reviews only)

```
TITLE-ABS-KEY("{topic}") AND PUBYEAR > {start_year} AND DOCTYPE(ar OR re)
```

## Step 3 — Refine with PICO terms (if applicable)

Combine population, intervention, and outcome using nested AND/OR groups:

```
TITLE-ABS-KEY(
  ("{topic}")
  {"AND (" + population + ")" if population else ""}
  {"AND (" + intervention + ")" if intervention else ""}
  {"AND (" + outcome + ")" if outcome else ""}
) AND PUBYEAR > {start_year} AND DOCTYPE(ar OR re)
```

## Step 4 — Retrieve full details

For each paper in the results, call `scopus_get_abstract` with:
- `identifier_type`: `"scopus_id"`
- `identifier`: the `scopus_id` from search results

## Step 5 — Citation impact screening

Use `scopus_get_citation_count` to quickly screen for high-impact papers without consuming Abstract API quota.

## Inclusion criteria checklist
- [ ] Published {start_year}–present
- [ ] Article or review document type
- [ ] Peer-reviewed (Scopus-indexed sources only)
- [ ] Language: English (add `AND LANGUAGE(English)` if needed)
- [ ] Directly addresses: {topic}

## Exclusion criteria checklist
- [ ] Conference abstracts only (`AND NOT DOCTYPE(cp)`)
- [ ] Grey literature / editorials
- [ ] Duplicate records (check DOI)

## PRISMA flow (template)
```
Records identified via Scopus (n = ?)
  → After duplicate removal (n = ?)
  → After title/abstract screening (n = ?)
  → After full-text assessment (n = ?)
  → Included in synthesis (n = ?)
```

Read `scopus://search-syntax` for the full Boolean field code reference.
"""

    @mcp.prompt(
        name="author_impact_analysis",
        description=(
            "Generate a step-by-step analysis plan for evaluating a researcher's academic impact "
            "using Scopus. Returns a structured workflow covering h-index, citation trends, "
            "co-authorship, and institutional affiliation, with ready-to-run tool calls."
        ),
    )
    def author_impact_analysis(
        author_name: str,
        institution: str = "",
    ) -> str:
        affil_filter = f" AND AFFIL({institution})" if institution else ""
        return f"""# Author Impact Analysis — {author_name}

## Step 1 — Find the author profile

Call `scopus_search_authors` with:
```
AUTHLASTNAME({author_name.split()[-1] if " " in author_name else author_name}) AND AUTHFIRST({author_name.split()[0][0] if " " in author_name else ""}){affil_filter}
```

This returns `author_id` values. Pick the correct match by inspecting affiliation and document count.

## Step 2 — Retrieve full metrics

Call `scopus_get_author` with the `author_id` from Step 1.

**Metrics returned:**
| Metric | What it means |
|--------|---------------|
| `h_index` | Papers with ≥ h citations — core productivity indicator |
| `cited_by_count` | Total citations received across all works |
| `document_count` | Number of Scopus-indexed publications |
| `affiliation` | Current institutional home |
| `subject_areas` | Research domain distribution |
| `orcid` | Cross-platform researcher ID |

## Step 3 — Publication output by year

Call `scopus_search` with:
```
AU-ID(<author_id>) AND PUBYEAR > 2010
```
Set `count=25` and paginate with `start` to collect the full list.

## Step 4 — Citation trend analysis

For the top 5 papers by citation count, call `scopus_get_citations_overview` with:
- `start_year`: 2010
- `end_year`: 2026

## Step 5 — Collaboration network

Search for co-authored papers:
```
AU-ID(<author_id>) AND NOT AUTH("{author_name}")
```
(Retrieves papers where the author appears alongside others — useful for network mapping.)

## Step 6 — Benchmark interpretation
| h-index range | Career stage indicator |
|---------------|----------------------|
| 0–5 | Early career / emerging |
| 6–15 | Established researcher |
| 16–30 | Senior / recognized expert |
| 31+ | Highly influential / field leader |

> These are discipline-dependent. Compare against peers in the same `subject_area` and career stage.
"""

    @mcp.prompt(
        name="research_trend_query",
        description=(
            "Build a Scopus query set to map research trends over time for a given topic. "
            "Returns ready-to-run scopus_search queries grouped by decade and document type, "
            "plus a year-over-year publication count strategy."
        ),
    )
    def research_trend_query(
        topic: str,
        field_code: str = "COMP",
        compare_topic: str = "",
    ) -> str:
        comparison_block = ""
        if compare_topic:
            comparison_block = f"""
## Comparative trend query

Run both queries and compare total result counts across years:

**Topic A — {topic}:**
```
TITLE-ABS-KEY("{topic}") AND SUBJAREA({field_code}) AND PUBYEAR > 2000
```

**Topic B — {compare_topic}:**
```
TITLE-ABS-KEY("{compare_topic}") AND SUBJAREA({field_code}) AND PUBYEAR > 2000
```
"""

        return f"""# Research Trend Analysis — {topic}

## Step 1 — Overall volume query

Call `scopus_search` with each decade range to measure publication growth:

**2000–2009 (baseline):**
```
TITLE-ABS-KEY("{topic}") AND PUBYEAR > 1999 AND PUBYEAR < 2010
```

**2010–2019 (growth decade):**
```
TITLE-ABS-KEY("{topic}") AND PUBYEAR > 2009 AND PUBYEAR < 2020
```

**2020–present (recent surge):**
```
TITLE-ABS-KEY("{topic}") AND PUBYEAR > 2019
```

## Step 2 — Document type breakdown

**Journal articles (core literature):**
```
TITLE-ABS-KEY("{topic}") AND DOCTYPE(ar) AND PUBYEAR > 2015
```

**Conference papers (applied/emerging work):**
```
TITLE-ABS-KEY("{topic}") AND DOCTYPE(cp) AND PUBYEAR > 2015
```

**Review papers (consensus/synthesis):**
```
TITLE-ABS-KEY("{topic}") AND DOCTYPE(re) AND PUBYEAR > 2015
```

## Step 3 — Subject area filter

Narrow to {field_code} subject area:
```
TITLE-ABS-KEY("{topic}") AND SUBJAREA({field_code}) AND PUBYEAR > 2015
```

See `scopus://subject-areas` for all subject area codes.

## Step 4 — Open access trajectory

```
TITLE-ABS-KEY("{topic}") AND OPENACCESS(1) AND PUBYEAR > 2015
```

Compare against total volume to calculate OA percentage per year.

## Step 5 — Top journals in this space

Run `scopus_search` with `view=COMPLETE` and inspect `publication` fields in results to identify the most frequent source titles.
{comparison_block}
## Trend interpretation guide

| Pattern | Interpretation |
|---------|----------------|
| Exponential growth | Hot/emerging field — high competition |
| Plateau | Mature field — incremental advances |
| Decline followed by surge | Paradigm shift (e.g., deep learning in 2012) |
| Conference > journal ratio | Applied/industry-driven domain |
| High OA % | Well-funded / policy-mandated area |
"""
