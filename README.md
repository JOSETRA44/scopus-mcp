[![MCP Badge](https://lobehub.com/badge/mcp/josetra44-scopus-mcp)](https://lobehub.com/mcp/josetra44-scopus-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io)

# Scopus MCP Server

<!-- mcp-name: io.github.JOSETRA44/scopus-mcp -->

Connects any MCP-compatible AI agent to the [Elsevier Scopus](https://www.scopus.com/) academic database — search 100+ million scholarly records, retrieve full abstracts, analyze author impact, and track citation trends.

**Works with:** Claude Desktop · Claude Code · Cursor · VS Code Copilot · Windsurf · Zed · Continue.dev · any MCP client

---



## What you can ask it

| Ask | Tool that answers it |
|---|---|
| "Find papers on machine learning in medicine since 2020" | `scopus_search` |
| "Give me the full abstract and keywords for this DOI" | `scopus_get_abstract` |
| "What is this researcher's h-index?" | `scopus_search_authors` → `scopus_get_author` † |
| "How many times has this paper been cited?" | `scopus_get_citation_count` |
| "Show the citations year by year" | `scopus_get_citations_overview` † |
| "Which institution is this affiliation ID?" | `scopus_search_affiliations` |

**You need a free API key**: register at [dev.elsevier.com](https://dev.elsevier.com/)
and set `SCOPUS_API_KEY`.

† These tools additionally need `SCOPUS_INST_TOKEN` **and** a connection from a
subscribing institution's network. Without both, Elsevier returns
`AUTHENTICATION_ERROR` even though your API key is perfectly valid — this is by
far the most common surprise for new users, and it is a licensing restriction on
Elsevier's side, not a bug here.

## Quickstart (2 minutes)

**1. Get your Scopus API key** (free) at [dev.elsevier.com](https://dev.elsevier.com/) → Register → Create API Key

**2. Install and run** — pick one method:

```bash
# Option A: uvx (recommended — no environment setup needed)
uvx scopus-mcp

# Option B: pip
pip install scopus-mcp
scopus-mcp
```

**3. Add to your AI client** — see the [Configuration](#configuration-by-client) section below.

---

## Prerequisites

### Python 3.11+
```bash
python --version   # needs 3.11 or higher
# Install if missing: https://python.org/downloads
```

### uv (recommended)
```bash
# Windows
winget install astral-sh.uv

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Installation

### Option A — uvx (zero configuration)
```bash
# Install and run in a single command
uvx scopus-mcp

# Upgrade later
uv tool upgrade scopus-mcp
```

### Option B — pip
```bash
pip install scopus-mcp

# Verify installation
scopus-mcp --help
```

### Option C — From source (development)
```bash
git clone https://github.com/JOSETRA44/scopus-mcp.git
cd scopus-mcp
uv sync                    # installs all dependencies
cp .env.example .env       # edit .env with your API key
uv run scopus-mcp          # run directly from source
```

---

## Terminal CLI

Besides running as an MCP server, `scopus-mcp` also installs three equivalent commands — `scopus-mcp`, `scopus`, and the short alias `scps` — as a **standalone command-line tool** for one-off lookups, testing your API key, or scripting, no MCP client required.

```bash
# Install globally as a uv tool (adds scopus / scps / scopus-mcp to PATH)
uv tool install --editable /path/to/scopus-mcp

scopus --help                 # list all subcommands
scopus check                  # validate your API key live against each endpoint
scopus search 'TITLE-ABS-KEY("machine learning")' --count 5
scps abstract 85180904906 --type scopus_id
scopus author 7401234567
scopus search-authors "AUTHLASTNAME(Smith)"
scopus search-affiliations "AFFIL(MIT)"
scopus citation-count --doi 10.1016/j.cell.2023.01.001
scopus citations 85180904906 --start-year 2020 --end-year 2024
```

Add `--json` to any subcommand for raw structured output (useful for piping into `jq` or scripts).

> Running any of the three commands **with no subcommand** starts the MCP stdio server instead — the mode MCP clients (Claude Desktop, Claude Code, etc.) use. It will sit waiting for input on stdin; that's expected, not a hang.

| Subcommand | Equivalent MCP tool |
|---|---|
| `search <query>` | `scopus_search` |
| `abstract <id> --type ...` | `scopus_get_abstract` |
| `author <author_id>` | `scopus_get_author` |
| `search-authors <query>` | `scopus_search_authors` |
| `search-affiliations <query>` | `scopus_search_affiliations` |
| `citation-count --scopus-id/--doi` | `scopus_get_citation_count` |
| `citations <scopus_id>` | `scopus_get_citations_overview` |
| `check` | *(CLI-only)* diagnostic — live-checks your key against every endpoint |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `SCOPUS_API_KEY` | **Yes** | — | Your Elsevier API key |
| `SCOPUS_INST_TOKEN` | No | — | Institutional token (for off-campus / full-text access) |
| `SCOPUS_CACHE_TTL` | No | `300` | Response cache duration in seconds (0 = disabled) |
| `SCOPUS_MAX_RETRIES` | No | `3` | Retries on rate-limit errors (HTTP 429) |
| `LOG_LEVEL` | No | `INFO` | Verbosity: `DEBUG` · `INFO` · `WARNING` · `ERROR` |

> **Using a `.env` file?** Copy `.env.example` → `.env` and fill in your key. Never commit it.

---

## Configuration by Client

Replace `YOUR_API_KEY_HERE` with your actual Elsevier API key in every config block below.

### Claude Desktop

**Config file:**
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "scopus": {
      "command": "uvx",
      "args": ["scopus-mcp"],
      "env": {
        "SCOPUS_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

Restart Claude Desktop after saving. A hammer icon (🔨) in the input bar confirms tools are loaded.

### Claude Code (CLI)

Add to your project's `.mcp.json` (or `.antigravity.json`):

```json
{
  "mcpServers": {
    "scopus": {
      "command": "uvx",
      "args": ["scopus-mcp"],
      "env": {
        "SCOPUS_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

**From source (local development):**
```json
{
  "mcpServers": {
    "scopus": {
      "command": "uv",
      "args": [
        "--directory", "/absolute/path/to/scopus-mcp",
        "run", "scopus-mcp"
      ],
      "env": {
        "SCOPUS_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

Run `/mcp` in the Claude Code prompt to verify — you should see `scopus` with 7 tools.

### Cursor

Global config: `%APPDATA%\Cursor\User\globalStorage\cursor.mcp\mcp.json` (Windows)

```json
{
  "mcpServers": {
    "scopus": {
      "command": "uvx",
      "args": ["scopus-mcp"],
      "env": {
        "SCOPUS_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

### VS Code + GitHub Copilot

Create `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "scopus": {
      "type": "stdio",
      "command": "uvx",
      "args": ["scopus-mcp"],
      "env": {
        "SCOPUS_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

### Windsurf

Config: `%APPDATA%\Codeium\windsurf\mcp_config.json` (Windows)

```json
{
  "mcpServers": {
    "scopus": {
      "command": "uvx",
      "args": ["scopus-mcp"],
      "env": {
        "SCOPUS_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

### Zed

Edit `~/.config/zed/settings.json`:

```json
{
  "context_servers": {
    "scopus": {
      "command": {
        "path": "uvx",
        "args": ["scopus-mcp"],
        "env": {
          "SCOPUS_API_KEY": "YOUR_API_KEY_HERE"
        }
      }
    }
  }
}
```

### Continue.dev

Edit `.continue/config.yaml`:

```yaml
mcpServers:
  - name: scopus
    command: uvx
    args:
      - scopus-mcp
    env:
      SCOPUS_API_KEY: "YOUR_API_KEY_HERE"
```

### Generic stdio (any MCP client)

```
command:  uvx
args:     ["scopus-mcp"]
env:      SCOPUS_API_KEY=YOUR_API_KEY_HERE
```

---

## Automated Setup Script

```bash
# Interactive setup (auto-detects installed clients)
python setup_mcp.py

# Non-interactive
python setup_mcp.py --key YOUR_API_KEY_HERE --yes

# Dry-run preview
python setup_mcp.py --key YOUR_API_KEY_HERE --dry-run --yes
```

---

## Available Tools (7)

| Tool | Description |
|------|-------------|
| `scopus_search` | Search papers with Boolean queries — TITLE-ABS-KEY, AUTH, AFFIL, PUBYEAR, DOCTYPE… |
| `scopus_get_abstract` | Full paper record by Scopus ID, DOI, EID, or PubMed ID |
| `scopus_get_author` | Researcher profile: h-index, total citations, document count, affiliation, ORCID |
| `scopus_search_authors` | Find researchers by name, ORCID, or institution |
| `scopus_search_affiliations` | Find institution records by name or country |
| `scopus_get_citation_count` | Quick citation count by Scopus ID or DOI |
| `scopus_get_citations_overview` | Year-by-year citation timeline for a paper |

---

## Available Prompts (3)

Prompts are reusable research workflows that generate structured query strategies.

| Prompt | Arguments | Description |
|--------|-----------|-------------|
| `systematic_literature_review` | `topic`, `population`, `intervention`, `outcome`, `start_year` | Generates a PICO-framed SLR search strategy with Boolean queries and PRISMA flow template |
| `author_impact_analysis` | `author_name`, `institution` | Step-by-step plan to evaluate a researcher's h-index, citation trends, and collaboration network |
| `research_trend_query` | `topic`, `field_code`, `compare_topic` | Decade-by-decade publication trend queries with document type breakdown and OA analysis |

---

## Available Resources (3)

Resources are reference documents agents can read at any time.

| Resource URI | Contents |
|-------------|----------|
| `scopus://search-syntax` | Complete Boolean query reference — field codes, operators, wildcards, examples |
| `scopus://subject-areas` | All `SUBJAREA()` discipline codes organized by field |
| `scopus://api-reference` | Tool quota costs, identifier formats, and recommended workflow patterns |

---

## Example Queries

```
# Find recent papers on a topic
TITLE-ABS-KEY("machine learning" AND cancer) AND PUBYEAR > 2020

# Reviews only
TITLE-ABS-KEY("federated learning") AND DOCTYPE(re)

# By author ID
AU-ID(7401234567) AND SUBJAREA(COMP)

# From a specific institution
AF-ID(60022195) AND TITLE-ABS-KEY("robotics")

# Open access papers in a specific journal
SRCTITLE("Nature Medicine") AND OPENACCESS(1) AND PUBYEAR > 2022

# Cross-disciplinary topic
TITLE-ABS-KEY("climate change") AND (SUBJAREA(ECON) OR SUBJAREA(ENVI))
```

---

## Rate Limits

The server tracks rate limits from response headers and sleeps automatically before making calls when quota is exhausted.

| Endpoint | Weekly Quota |
|----------|:------------:|
| Scopus Search | 20,000 |
| Abstract Retrieval | 5,000 |
| Author Retrieval | 5,000 |
| Citation Count | **50,000** |
| Citations Overview | 5,000 |

> **Tip:** Use `scopus_get_citation_count` (50K quota) for bulk citation checks. Reserve `scopus_get_abstract` (5K quota) for the papers you actually need in detail.

---

## Verify It's Working

```bash
# Fastest check: validates your API key live against every endpoint
scopus check

# Interactive browser UI (recommended for MCP-specific debugging)
npx @modelcontextprotocol/inspector uvx scopus-mcp

# Quick smoke test (server starts and exits cleanly)
echo "" | SCOPUS_API_KEY=your_key uvx scopus-mcp

# Unit tests (from source)
uv sync --group dev
uv run pytest tests/ -v
# Expected: 19 passed
```

---

## Troubleshooting

**`command not found: uvx`**
Install uv: https://docs.astral.sh/uv/getting-started/installation/

**`Configuration error: Missing required environment variable: SCOPUS_API_KEY`**
Make sure your config's `"env"` block has `"SCOPUS_API_KEY": "your_actual_key"` — not a placeholder.

**Tools fail with HTTP 401**
API key is invalid or expired. Regenerate at [dev.elsevier.com](https://dev.elsevier.com/).

**Tools fail with HTTP 403**
Your key may lack Scopus access. An institutional subscription is required for most endpoints. Ask your librarian about `SCOPUS_INST_TOKEN`.

**First run is slow**
uv downloads and caches the package on first run. Subsequent starts take ~0.2s.

**Tools appear but return empty results**
Try broadening your query: replace `TITLE(...)` with `TITLE-ABS-KEY(...)` or remove `PUBYEAR` constraints.

---

## Project Structure

```
scopus-mcp/
├── src/scopus_mcp/
│   ├── server.py        # Entry point — dispatches to CLI or FastMCP stdio server
│   ├── cli.py           # Terminal CLI (scopus / scps): subcommands + check diagnostic
│   ├── config.py        # Env var configuration (pydantic-settings)
│   ├── client.py        # Async HTTP client + TTL cache + rate limiter
│   ├── exceptions.py    # Error hierarchy
│   ├── formatters.py    # Raw Scopus JSON → clean AI-friendly dicts
│   ├── tools/           # 7 MCP tools (search, abstract, author, citations)
│   ├── prompts/         # 3 MCP prompts (SLR, author analysis, trend query)
│   └── resources/       # 3 MCP resources (syntax, subject areas, API reference)
├── scopus-researcher/   # Agent skill (npx skills add JOSETRA44/scopus-mcp@scopus-researcher)
│   ├── SKILL.md
│   └── references/
├── tests/               # Unit tests (19 cases, no network required)
├── setup_mcp.py         # Automated config installer for all clients
├── .env.example         # Environment variable template
└── pyproject.toml       # Package definition
```

---

## CLI for agents

Curated Elsevier metadata: author h-index and year-by-year citation timelines that OpenAlex does not carry.

This CLI follows [`ARSENAL-SPEC.md`](../ARSENAL-SPEC.md), the contract every research
tool in this workspace shares: an agent that can drive one can drive all of them.

### Discover it without reading this file

```bash
scopus describe --json          # every command, argument, row field and example
scopus describe <command> --json
```

The manifest is derived from the parser itself, so it cannot drift out of date.

### Output

`-f, --format` accepts `table`, `json`, `jsonl`, `csv`, `md`; `-o FILE` writes to a file; `-q` silences notes.
**Data goes to stdout, notes and progress to stderr** — piping to `jq` always yields
parseable JSON.

`--format json` returns the standard envelope:

```json
{
  "ok": true,
  "command": "search",
  "source": "scopus",
  "fetched_at": "2026-08-21T14:03:11Z",
  "cached": false,
  "count": 10,
  "meta": {},
  "data": {},
  "rows": []
}
```

`count` always equals `len(rows)`. An empty result is exit 0, not an error. Failures
return an error envelope carrying `error.code`, `error.message` and an actionable
`error.hint`, printed to stdout in machine formats so a pipeline can inspect it.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | success (including an empty result set) |
| 1 | API returned an error / unexpected response |
| 2 | usage error (bad flag, bad argument, unknown format) |
| 3 | resource not found |
| 4 | auth or configuration error (missing/invalid API key) |
| 5 | rate limited or quota exhausted |
| 6 | network failure or timeout |

### Cache

Results are cached on disk and survive between invocations, so a repeated query is
instant. `--refresh` refetches and rewrites; `--no-cache` skips it entirely; the
envelope reports `cached`.

```bash
scopus cache stats -f json
scopus cache clear
```

### Recipes

```bash
scopus search 'TITLE-ABS-KEY("graph neural network")' --count 5
scopus search 'TITLE-ABS-KEY(crispr) AND PUBYEAR > 2020' -f jsonl --all --max 500
scopus search 'AFFIL(MIT)' -f csv -o mit.csv --all --max 200
scopus abstract 10.1016/j.labeco.2024.102505 --type doi -f json
scopus abstract 85180904906 --type scopus_id
```

Or through the workspace-wide entry point: `arsenal run scopus <command> ...`,
and `arsenal doctor scopus --live` to check this CLI still honours the contract.

## Troubleshooting

**`AUTHENTICATION_ERROR` on author or citation tools, but search works fine**
Expected without an institutional subscription. `scopus_search`,
`scopus_get_abstract` and `scopus_get_citation_count` work with just an API key;
author profiles and citation overviews need `SCOPUS_INST_TOKEN` *and* an
on-network connection. The CLI reports this as exit code 4.

**`Missing SCOPUS_API_KEY`**
Set it in your environment or in a `.env` file beside the project. In an MCP
client, put it in the server's `env` block — see the configuration section above.

**`os error 32` when running the tests**
A running MCP server is holding the console script open. Use
`uv run --no-sync pytest -q`.

**Quota exhausted**
Scopus enforces weekly quotas per key. The remaining quota is reported in the
JSON envelope's `meta`; exhaustion surfaces as exit code 5.

## Documentation

| Document | What's in it |
|---|---|
| [`CHANGELOG.md`](CHANGELOG.md) | What changed in each release |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Dev setup, the CLI contract, how to run the tests |
| [`SECURITY.md`](SECURITY.md) | What this server sends and where; how to report a vulnerability |
| [`server.json`](server.json) | Registry metadata for the official MCP registry |
| [`../ARSENAL-SPEC.md`](../ARSENAL-SPEC.md) | The CLI contract shared by every research server here |

## Licence

MIT — see [`LICENSE`](LICENSE).
