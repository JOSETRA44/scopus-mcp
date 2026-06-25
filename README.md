[![MCP Badge](https://lobehub.com/badge/mcp/josetra44-scopus-mcp)](https://lobehub.com/mcp/josetra44-scopus-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io)

# Scopus MCP Server

Connects any MCP-compatible AI agent to the [Elsevier Scopus](https://www.scopus.com/) academic database — search 100+ million scholarly records, retrieve full abstracts, analyze author impact, and track citation trends.

**Works with:** Claude Desktop · Claude Code · Cursor · VS Code Copilot · Windsurf · Zed · Continue.dev · any MCP client

---

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
# Interactive browser UI (recommended)
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
│   ├── server.py        # FastMCP entry point — registers tools, prompts, resources
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

## License

[MIT](LICENSE) — © 2026 JOSETRA44
