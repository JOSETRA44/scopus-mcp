# Scopus MCP Server

A production-ready [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server that gives AI agents access to the [Elsevier Scopus](https://www.scopus.com/) academic research database.

## Features

- **7 tools** covering search, abstract retrieval, author profiles, and citation analysis
- **In-memory caching** (TTL-based) to avoid redundant API calls
- **Rate limit handling** — tracks remaining quota and retries with backoff on 429 errors
- **Secure configuration** via environment variables (no hardcoded secrets)
- **Structured JSON output** optimized for AI consumption
- **Scopus search syntax guide** exposed as an MCP resource

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A Scopus API key from [dev.elsevier.com](https://dev.elsevier.com/)

## Installation

### Option 1: Development install (from this repo)

```bash
# Clone and enter the repo
cd scopus-mcp

# Install dependencies
uv sync

# Copy and configure the environment file
cp .env.example .env
# Edit .env and set SCOPUS_API_KEY=your_actual_key
```

### Option 2: Install with uvx (after publishing to PyPI)

```bash
uvx scopus-mcp
```

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SCOPUS_API_KEY` | **Yes** | — | Your Elsevier API key |
| `SCOPUS_INST_TOKEN` | No | — | Institutional token for off-campus/full-text access |
| `SCOPUS_CACHE_TTL` | No | `300` | Cache TTL in seconds (0 to disable) |
| `SCOPUS_MAX_RETRIES` | No | `3` | Max retries on rate-limit errors |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity: DEBUG, INFO, WARNING, ERROR |

Get your API key at [https://dev.elsevier.com/](https://dev.elsevier.com/).

## Connecting to Claude

### Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "scopus": {
      "command": "uvx",
      "args": ["scopus-mcp"],
      "env": {
        "SCOPUS_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

### Claude Code (development mode, local install)

Edit `.antigravity.json` in this directory:

```json
{
  "mcpServers": {
    "scopus": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/scopus-mcp", "run", "scopus-mcp"]
    }
  }
}
```

When using the local `.env` file, you don't need the `"env"` block.

## Available Tools

### `scopus_search`
Search for papers using Scopus Boolean query syntax.

```
Query: TITLE-ABS-KEY("machine learning" AND cancer) AND PUBYEAR > 2020
Count: 10, Start: 0
```

Returns: list of papers with title, authors, journal, DOI, citation count, open access status.

### `scopus_get_abstract`
Fetch full paper details by any identifier.

```
identifier_type: doi
identifier: 10.1016/j.labeco.2024.102505
```

Returns: full abstract, all authors with affiliations, keywords, subject areas.

### `scopus_get_author`
Get a researcher's profile by Scopus Author ID.

```
author_id: 7401234567
```

Returns: h-index, citation count, document count, current affiliation, subject areas.

### `scopus_search_authors`
Find author profiles by name.

```
query: AUTHLASTNAME(Smith) AND AUTHFIRST(J) AND AFFIL(MIT)
```

### `scopus_search_affiliations`
Find institutional records.

```
query: AFFIL(Harvard) AND COUNTRY(United States)
```

### `scopus_get_citation_count`
Quick citation count for a paper (lightweight, highly cached).

```
doi: 10.1038/s41591-024-00001-0
```

### `scopus_get_citations_overview`
Year-by-year citation timeline.

```
scopus_id: 85123456789
start_year: 2015
end_year: 2024
```

## MCP Resource

### `scopus://search-syntax`
A complete Markdown reference for Scopus Boolean query syntax — field codes, operators, wildcards, document type codes, subject area codes, and practical examples. Agents should read this resource when constructing complex queries.

## Testing

```bash
# Install dev dependencies and run tests
uv sync --group dev
uv run pytest tests/ -v

# Test the server starts correctly (exits when stdin closes)
echo "" | uv run scopus-mcp

# Interactive test with MCP Inspector
npx @modelcontextprotocol/inspector uv run scopus-mcp
```

## Scopus API Rate Limits

| Endpoint | Quota per 7 days |
|----------|-----------------|
| Search | 20,000 requests |
| Abstract Retrieval | 5,000 requests |
| Citation Count | 50,000 requests |

The server tracks remaining quota from response headers and sleeps automatically when the limit is reached. On HTTP 429, it retries with exponential backoff (up to `SCOPUS_MAX_RETRIES` times).

## Project Structure

```
src/scopus_mcp/
├── server.py        # FastMCP app creation and entry point
├── config.py        # Environment variable configuration
├── client.py        # Async HTTP client with caching and rate limiting
├── exceptions.py    # Error hierarchy
├── formatters.py    # Pure functions: raw Scopus JSON → clean dicts
├── tools/
│   ├── search.py    # scopus_search, scopus_search_authors, scopus_search_affiliations
│   ├── abstract.py  # scopus_get_abstract
│   ├── author.py    # scopus_get_author
│   └── citations.py # scopus_get_citation_count, scopus_get_citations_overview
└── resources/
    └── syntax_guide.py  # scopus://search-syntax static resource
```

## License

MIT
