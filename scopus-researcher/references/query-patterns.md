# Scopus Query Patterns Reference

## Field Code Cheat Sheet

| Code | Scope | Example |
|------|-------|---------|
| `TITLE(term)` | Paper title | `TITLE("neural network")` |
| `ABS(term)` | Abstract text | `ABS(CRISPR)` |
| `KEY(term)` | Author keywords | `KEY(sustainability)` |
| `TITLE-ABS-KEY(term)` | Title + Abstract + Keywords | `TITLE-ABS-KEY("machine learning")` |
| `AUTH(name)` | Author name | `AUTH("Smith J")` |
| `AU-ID(id)` | Author Scopus ID | `AU-ID(7401234567)` |
| `ORCID(id)` | ORCID | `ORCID(0000-0002-1234-5678)` |
| `AUTHLASTNAME(n)` | Author last name | `AUTHLASTNAME(García)` |
| `AUTHFIRST(n)` | Author first name/initials | `AUTHFIRST(J)` |
| `AFFIL(text)` | Author affiliation | `AFFIL(MIT)` |
| `AF-ID(id)` | Affiliation Scopus ID | `AF-ID(60027950)` |
| `SRCTITLE(title)` | Journal/conf name | `SRCTITLE(Nature)` |
| `ISSN(number)` | Journal ISSN | `ISSN(0028-0836)` |
| `DOI(id)` | DOI | `DOI(10.1038/...)` |
| `PUBYEAR` | Year operators | `PUBYEAR > 2020` |
| `DOCTYPE(code)` | Document type | `DOCTYPE(ar)` |
| `LANGUAGE(lang)` | Language | `LANGUAGE(English)` |
| `SUBJAREA(code)` | Subject area | `SUBJAREA(COMP)` |
| `OPENACCESS(1)` | Open access only | `OPENACCESS(1)` |
| `CITEDBY-COUNT` | Citation count | n/a in query; use in results |

## Boolean Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `AND` | Both required | `A AND B` |
| `OR` | Either | `A OR B` |
| `AND NOT` | Exclude | `A AND NOT B` |
| `W/n` | Within n words | `machine W/3 learning` |
| `PRE/n` | A precedes B by n words | `deep PRE/2 learning` |

**Always UPPERCASE**: `AND`, `OR`, `AND NOT`

## PUBYEAR Operators

```
PUBYEAR > 2020          # After 2020
PUBYEAR < 2010          # Before 2010
PUBYEAR = 2023          # Exact year
PUBYEAR AFT 2020        # Same as >
PUBYEAR BEF 2010        # Same as <
```

## Document Type Codes

| Code | Type |
|------|------|
| `ar` | Journal article |
| `re` | Review article |
| `cp` | Conference paper |
| `ch` | Book chapter |
| `bk` | Book |
| `ed` | Editorial |
| `le` | Letter |
| `sh` | Short survey |
| `no` | Note |
| `er` | Erratum |
| `ab` | Abstract report |

## Subject Area Codes

| Code | Area |
|------|------|
| `AGRI` | Agricultural & Biological Sciences |
| `ARTS` | Arts & Humanities |
| `BIOC` | Biochemistry, Genetics & Mol Bio |
| `BUSI` | Business, Management & Accounting |
| `CENG` | Chemical Engineering |
| `CHEM` | Chemistry |
| `COMP` | Computer Science |
| `DECI` | Decision Sciences |
| `DENT` | Dentistry |
| `EART` | Earth & Planetary Sciences |
| `ECON` | Economics, Econometrics & Finance |
| `ENER` | Energy |
| `ENGI` | Engineering |
| `ENVI` | Environmental Science |
| `HEAL` | Health Professions |
| `IMMU` | Immunology & Microbiology |
| `MATE` | Materials Science |
| `MATH` | Mathematics |
| `MEDI` | Medicine |
| `NEUR` | Neuroscience |
| `NURS` | Nursing |
| `PHAR` | Pharmacology, Tox & Pharma |
| `PHYS` | Physics & Astronomy |
| `PSYC` | Psychology |
| `SOCI` | Social Sciences |
| `VETE` | Veterinary |
| `MULT` | Multidisciplinary |

---

## 30+ Query Examples by Use Case

### Topic Discovery

```
# Broad topic search (most results)
TITLE-ABS-KEY("climate change")

# Focused topic search
TITLE("federated learning")

# Phrase + keyword combination
TITLE-ABS-KEY("machine learning" AND (cancer OR tumor))

# Multi-concept with exclusion
TITLE-ABS-KEY("artificial intelligence" AND healthcare AND NOT "systematic review")
```

### Temporal Filters

```
# Papers from last 5 years
TITLE-ABS-KEY("quantum computing") AND PUBYEAR > 2019

# Specific decade
TITLE-ABS-KEY("deep learning") AND PUBYEAR > 2009 AND PUBYEAR < 2020

# Exact year
TITLE-ABS-KEY(ChatGPT) AND PUBYEAR = 2023
```

### Document Type Filters

```
# Review articles only (best for literature surveys)
TITLE-ABS-KEY("CRISPR") AND DOCTYPE(re)

# Journal articles only (exclude conferences)
TITLE-ABS-KEY("reinforcement learning") AND DOCTYPE(ar)

# Conference papers on a topic
TITLE-ABS-KEY("graph neural network") AND DOCTYPE(cp)
```

### Author-Centric

```
# By author name (fuzzy — use AU-ID for precision)
AUTH("Hinton G")

# By Scopus Author ID (exact)
AU-ID(7201482550)

# Author's papers in a field
AU-ID(7201482550) AND SUBJAREA(COMP)

# Collaborations between two authors
AUTH("LeCun Y") AND AUTH("Bengio Y")
```

### Institution-Centric

```
# Papers from a university
AFFIL(MIT)

# With precise institution ID
AF-ID(60022195)

# Institution + topic
AF-ID(60022195) AND TITLE-ABS-KEY("robotics")

# Country-level filter
AFFIL(Peru) AND TITLE-ABS-KEY("education")
```

### Journal-Specific

```
# Papers in Nature journals
SRCTITLE(Nature)

# Specific journal by ISSN
ISSN(1553-7358)  # PLOS Computational Biology

# High-impact journals on topic
(SRCTITLE(Nature) OR SRCTITLE(Science) OR SRCTITLE(Cell)) AND TITLE-ABS-KEY("genomics")
```

### Open Access & Language

```
# Open access only
TITLE-ABS-KEY("mental health") AND OPENACCESS(1)

# Spanish language papers
TITLE-ABS-KEY("cambio climático") AND LANGUAGE(Spanish)

# English reviews, open access
TITLE-ABS-KEY("COVID-19") AND DOCTYPE(re) AND LANGUAGE(English) AND OPENACCESS(1)
```

### Latin America Research

```
# Papers from Latin America on education
(AFFIL(Peru) OR AFFIL(Colombia) OR AFFIL(Chile) OR AFFIL(Argentina)) AND TITLE-ABS-KEY("higher education")

# Peru-specific research
AFFIL(Peru) AND SUBJAREA(ECON) AND PUBYEAR > 2015

# Employment/labor economics in the region
TITLE-ABS-KEY("labor market" AND "Latin America") AND DOCTYPE(ar)
```

### Economics & Social Sciences (matching existing scripts)

```
# Skill mismatch in education
TITLE-ABS-KEY("skill mismatch" AND "higher education" AND employability)

# Returns to education
TITLE-ABS-KEY("returns to education" AND quality AND university)

# Human capital and employability
TITLE-ABS-KEY("human capital" AND "graduate employability")

# Digital divide
TITLE-ABS-KEY("digital divide" AND "higher education" AND "Latin America")

# Reservation wage
TITLE-ABS-KEY("reservation wage" AND students AND expectations)
```

### Proximity Searches

```
# Words within 3 of each other
TITLE(machine W/3 learning)

# Ordered proximity
TITLE(deep PRE/2 learning)
```

### Highly Cited / Impact

```
# Top cited papers in AI (sort by citations in results)
TITLE-ABS-KEY("attention mechanism") AND PUBYEAR > 2015 AND DOCTYPE(ar)

# Reviews with many citations
TITLE-ABS-KEY("transformer" AND "natural language processing") AND DOCTYPE(re)
```
