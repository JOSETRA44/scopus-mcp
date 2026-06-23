# Scopus Research Workflow Examples

## 1. Systematic Literature Review (SLR) Preparation

**Task:** Find all recent review articles on a topic for a systematic review.

```python
# Step 1: Search for recent reviews
results = scopus_search(
    query='TITLE-ABS-KEY("federated learning" AND "privacy") AND DOCTYPE(re) AND PUBYEAR > 2020',
    count=25
)
# → total_results tells you the full pool size

# Step 2: Paginate through all results
# If total_results > 25, iterate with start=0, 25, 50...
results_p2 = scopus_search(
    query='TITLE-ABS-KEY("federated learning" AND "privacy") AND DOCTYPE(re) AND PUBYEAR > 2020',
    count=25, start=25
)

# Step 3: Get full details for selected papers
abstract = scopus_get_abstract(identifier_type="doi", identifier="10.1109/TNNLS.2023.3329524")
# → full abstract, all authors, keywords, subject areas
```

---

## 2. Author Benchmarking

**Task:** Compare two researchers in the same field by h-index and output.

```python
# Find first author
authors_a = scopus_search_authors(query="AUTHLASTNAME(Hinton) AND AUTHFIRST(G)")
# → authors[0].author_id = "7201482550"

profile_a = scopus_get_author(author_id="7201482550")
# → h_index, document_count, cited_by_count, affiliation

# Find second author
authors_b = scopus_search_authors(query="AUTHLASTNAME(LeCun) AND AUTHFIRST(Y)")
profile_b = scopus_get_author(author_id=authors_b["authors"][0]["author_id"])

# Compare:
# profile_a["h_index"] vs profile_b["h_index"]
# profile_a["cited_by_count"] vs profile_b["cited_by_count"]
```

---

## 3. Citation Trend Analysis (Research Impact)

**Task:** Understand how a landmark paper's influence grew over time.

```python
# Step 1: Find the paper
results = scopus_search(
    query='TITLE("Attention Is All You Need")',
    count=1
)
scopus_id = results["papers"][0]["scopus_id"]  # "85029815652"

# Step 2: Get year-by-year breakdown
trend = scopus_get_citations_overview(
    scopus_id=scopus_id,
    start_year=2017,
    end_year=2025
)
# → citations_by_year: {"2017": 12, "2018": 450, ..., "2024": 22000}

# Step 3: Verify total
count = scopus_get_citation_count(scopus_id=scopus_id)
# → cited_by_count: 85000
```

---

## 4. Institutional Research Audit

**Task:** Analyze what a university publishes in a specific field.

```python
# Step 1: Find the institution
affiliations = scopus_search_affiliations(
    query="AFFIL(Universidad Nacional Mayor de San Marcos)"
)
affil_id = affiliations["affiliations"][0]["affiliation_id"]

# Step 2: Search papers from that institution
papers = scopus_search(
    query=f'AF-ID({affil_id}) AND TITLE-ABS-KEY("economia" OR "economics") AND PUBYEAR > 2018',
    count=25
)

# Step 3: Get details for highest-cited papers
top_papers = sorted(papers["papers"], key=lambda p: p["cited_by_count"], reverse=True)
for paper in top_papers[:5]:
    detail = scopus_get_abstract(identifier_type="scopus_id", identifier=paper["scopus_id"])
```

---

## 5. Research Gap Discovery

**Task:** Find understudied topic combinations.

```python
# Check how much exists on topic intersection
gap_check = scopus_search(
    query='TITLE-ABS-KEY("digital divide" AND "higher education" AND "Latin America") AND PUBYEAR > 2018',
    count=1
)
# → total_results: 47 → small corpus = potential research gap

# Compare with broader topic
broader = scopus_search(
    query='TITLE-ABS-KEY("digital divide" AND "higher education") AND PUBYEAR > 2018',
    count=1
)
# → total_results: 1820 → much larger = your niche is underrepresented
```

---

## 6. Finding Papers by DOI Batch

**Task:** Retrieve metadata for a list of DOIs (e.g., from a reference list).

```python
dois = [
    "10.1016/j.japwor.2026.101357",
    "10.1080/09645292.2024.2354848",
    "10.1016/j.labeco.2024.102505",
    "10.15691/07194714.2024.004",
]

papers = []
for doi in dois:
    paper = scopus_get_abstract(identifier_type="doi", identifier=doi)
    papers.append({
        "doi": doi,
        "title": paper["title"],
        "authors": paper["authors"],
        "year": paper["cover_date"][:4],
        "cited_by": paper["cited_by_count"],
        "abstract": paper["abstract"][:300] + "..."
    })
```

---

## 7. Journal Impact Analysis

**Task:** Find the most-cited papers in a specific journal from 2023.

```python
journal_papers = scopus_search(
    query='SRCTITLE("Journal of Labor Economics") AND PUBYEAR = 2023 AND DOCTYPE(ar)',
    count=25
)

# Sort by citations (highest impact)
sorted_papers = sorted(
    journal_papers["papers"],
    key=lambda p: p.get("cited_by_count", 0),
    reverse=True
)

# Get full details for top 3
for paper in sorted_papers[:3]:
    detail = scopus_get_abstract(
        identifier_type="doi",
        identifier=paper.get("doi", "")
    ) if paper.get("doi") else None
```

---

## 8. Graduate Employability Research (Domain-Specific)

**Task:** Support research on human capital and graduate outcomes in Peru.

```python
# Query 1: Core topic
results_1 = scopus_search(
    query='TITLE-ABS-KEY("human capital" AND "graduate employability" AND Peru)',
    count=15
)

# Query 2: Broader context
results_2 = scopus_search(
    query='TITLE-ABS-KEY("skill mismatch" AND "higher education" AND employability)',
    count=15
)

# Query 3: Returns to education
results_3 = scopus_search(
    query='TITLE-ABS-KEY("returns to education" AND quality AND university)',
    count=15
)

# Deduplicate by scopus_id across all result sets
all_papers = {}
for r in [results_1, results_2, results_3]:
    for p in r["papers"]:
        all_papers[p["scopus_id"]] = p

# Get abstracts for unique papers
for scopus_id, paper in list(all_papers.items())[:20]:
    detail = scopus_get_abstract(identifier_type="scopus_id", identifier=scopus_id)
    paper["abstract"] = detail.get("abstract", "")
    paper["keywords"] = detail.get("keywords", [])
```

---

## Output Formatting Tips

When presenting results to users:

### For paper lists
```
{index}. **{title}**
   {first_author} | {publication} ({cover_date[:4]}) | Cited {cited_by_count}×
   DOI: {doi} | {"Open Access" if open_access else ""}
```

### For author profiles
```
**{name}** — {affiliation.institution}, {affiliation.country}
h-index: {h_index} | {document_count} papers | {cited_by_count} citations
Active: {publication_range.start}–{publication_range.end}
```

### For citation trends
```
Citation growth for "{title}":
{year}: {"█" * (count // scale)} {count}
```
