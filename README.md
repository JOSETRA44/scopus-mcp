# Scopus MCP Server

Connects any MCP-compatible AI agent to the [Elsevier Scopus](https://www.scopus.com/) academic database — search 100+ million scholarly records, retrieve full abstracts, analyze author impact, and track citation trends.

**Works with:** Claude Desktop · Claude Code · Cursor · VS Code Copilot · Windsurf · Zed · any MCP client

---

## Quickstart (2 minutes)

**1. Get your Scopus API key** (free) at [dev.elsevier.com](https://dev.elsevier.com/) → Register → Create API Key

**2. Install the server**
```bash
# Requires Python 3.11+  and uv  (see Prerequisites below if missing)
pip install scopus-mcp
```

**3. Add to your AI agent** — pick your client from the [Configuration](#configuration-by-client) section below.

---

## Prerequisites

### Python 3.11+
```bash
# Check your version
python --version   # needs 3.11 or higher

# Install if missing: https://python.org/downloads
```

### uv (recommended — fastest installer)
```bash
# Windows
winget install astral-sh.uv

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

> **No uv?** You can use `pip` instead. Wherever you see `uvx scopus-mcp`, replace it with the path returned by `which scopus-mcp` after running `pip install scopus-mcp`.

---

## Installation Options

### Option A — uvx (recommended, no environment management)
```bash
# Install and run in one command — uv handles everything
uvx scopus-mcp

# Upgrade later
uv tool upgrade scopus-mcp
```

### Option B — pip (traditional)
```bash
pip install scopus-mcp

# Find the installed path (needed for some configs)
which scopus-mcp          # macOS/Linux → /usr/local/bin/scopus-mcp
where scopus-mcp          # Windows    → C:\Users\YOU\AppData\...
```

### Option C — From source (for development / customization)
```bash
git clone https://github.com/YOUR_USER/scopus-mcp.git
cd scopus-mcp
uv sync                    # installs all dependencies
cp .env.example .env       # then edit .env with your key
uv run scopus-mcp          # run directly from source
```

---

## Environment Variables

All settings are passed via environment variables (or a `.env` file for local development).

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `SCOPUS_API_KEY` | **Yes** | — | Your Elsevier API key |
| `SCOPUS_INST_TOKEN` | No | — | Institutional token (for off-campus / full-text access) |
| `SCOPUS_CACHE_TTL` | No | `300` | Response cache duration in seconds (0 = disabled) |
| `SCOPUS_MAX_RETRIES` | No | `3` | Retries on rate-limit errors (HTTP 429) |
| `LOG_LEVEL` | No | `INFO` | Verbosity: `DEBUG` · `INFO` · `WARNING` · `ERROR` |

> **Using a `.env` file?** Copy `.env.example` → `.env` and fill in your key. The server loads it automatically on startup. The `.env` file is in `.gitignore` — never commit it.

---

## Configuration by Client

Pick your AI agent and copy the config block. Replace `YOUR_API_KEY_HERE` with your actual key.

---

### Claude Desktop

**Config file location:**
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

Open the file (create it if it doesn't exist) and add the `scopus` block inside `mcpServers`:

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

**Restart Claude Desktop** after saving. You'll see a hammer icon (🔨) in the chat input confirming tools are loaded.

> **Using pip instead of uvx?**
> Replace `"command": "uvx"` and `"args": ["scopus-mcp"]` with:
> ```json
> "command": "C:\\Users\\YOU\\AppData\\Local\\Programs\\Python\\Python311\\Scripts\\scopus-mcp.exe"
> ```
> Use the path from `where scopus-mcp` (Windows) or `which scopus-mcp` (macOS/Linux).

---

### Claude Code (CLI)

Add to your project's `.mcp.json` (or `.antigravity.json`) in the repository root:

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

Or, if you cloned this repo locally and prefer **not** to publish, use the source directly:

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

Verify it loaded with `/mcp` in the Claude Code prompt. You should see `scopus` listed with 7 tools.

---

### Cursor

**Config file location:** `.cursor/mcp.json` in your project root, **or** globally at:
- Windows: `%APPDATA%\Cursor\User\globalStorage\cursor.mcp\mcp.json`
- macOS: `~/Library/Application Support/Cursor/User/globalStorage/cursor.mcp/mcp.json`

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

In Cursor: **Settings → Features → MCP** → toggle on → reload window.

---

### VS Code + GitHub Copilot

Create or edit `.vscode/mcp.json` in your workspace root:

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

Then in VS Code: **Ctrl+Shift+P** → `GitHub Copilot: Configure MCP` → the server should appear.

---

### Windsurf

**Config file location:**
- Windows: `%APPDATA%\Codeium\windsurf\mcp_config.json`
- macOS: `~/.codeium/windsurf/mcp_config.json`

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

Restart Windsurf after saving.

---

### Zed

Edit `~/.config/zed/settings.json` and add:

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

---

### Continue.dev

Edit `.continue/config.yaml` in your project:

```yaml
mcpServers:
  - name: scopus
    command: uvx
    args:
      - scopus-mcp
    env:
      SCOPUS_API_KEY: "YOUR_API_KEY_HERE"
```

---

### Any other MCP client (generic stdio)

The server uses **stdio transport** — the standard for MCP. Any client that supports `stdio` MCPs can connect with:

```
command:  uvx
args:     ["scopus-mcp"]
env:      SCOPUS_API_KEY=YOUR_API_KEY_HERE
```

---

## Automated Setup Script

Run the installer to auto-detect your clients and configure them:

```bash
# Interactive (asks which clients and your API key)
python setup_mcp.py

# Non-interactive (configures all detected clients at once)
python setup_mcp.py --key YOUR_API_KEY_HERE --yes

# Preview what it would do without writing any files
python setup_mcp.py --key YOUR_API_KEY_HERE --dry-run --yes

# Show detected clients only
python setup_mcp.py --list
```

The script will:
1. Detect installed clients (Claude Desktop, Cursor, VS Code, Windsurf)
2. Ask for your API key (or accept it via `--key`)
3. Add the `scopus` server block to each config file
4. Back up existing configs before modifying (e.g. `claude_desktop_config.backup_20260623_142301.json`)

---

## Available Tools

| Tool | What it does |
|------|-------------|
| `scopus_search` | Search papers with Boolean queries (TITLE-ABS-KEY, AUTH, AFFIL, PUBYEAR…) |
| `scopus_get_abstract` | Full paper details by Scopus ID, DOI, EID, or PubMed ID |
| `scopus_get_author` | Author profile: h-index, citation count, affiliation, subject areas |
| `scopus_search_authors` | Find researchers by name, ORCID, or institution |
| `scopus_search_affiliations` | Find institutions by name or country |
| `scopus_get_citation_count` | Quick citation count by Scopus ID or DOI |
| `scopus_get_citations_overview` | Year-by-year citation timeline |

### MCP Resource

| Resource | Contents |
|----------|----------|
| `scopus://search-syntax` | Complete Boolean query syntax reference (field codes, operators, examples) |

---

## Example Queries

```
# Find recent papers on a topic
TITLE-ABS-KEY("machine learning" AND cancer) AND PUBYEAR > 2020

# Reviews only
TITLE-ABS-KEY("federated learning") AND DOCTYPE(re)

# By author + field
AU-ID(7401234567) AND SUBJAREA(COMP)

# From a specific institution
AF-ID(60022195) AND TITLE-ABS-KEY("robotics")

# Open access papers in a journal
SRCTITLE("Nature Medicine") AND OPENACCESS(1) AND PUBYEAR > 2022
```

---

## Rate Limits

The server handles rate limits automatically. It tracks remaining quota from response headers and sleeps until reset before making the next call.

| Endpoint | Quota per 7 days |
|----------|:----------------:|
| Scopus Search | 20,000 |
| Abstract Retrieval | 5,000 |
| Citation Count | 50,000 |

> **Tip:** Use `scopus_get_citation_count` (50K quota) instead of `scopus_get_abstract` (5K quota) when you only need citation counts.

---

## Verify It's Working

### MCP Inspector (interactive browser UI)
```bash
npx @modelcontextprotocol/inspector uvx scopus-mcp
```
Open the URL shown, click **Connect**, then **List Tools** — you should see all 7 tools.

### Quick smoke test
```bash
# Server should start without errors, then exit when stdin closes
echo "" | uvx scopus-mcp
```

### Run unit tests (source install only)
```bash
uv sync --group dev
uv run pytest tests/ -v
# Expected: 19 passed
```

---

## Troubleshooting

### "command not found: uvx"
Install uv: https://docs.astral.sh/uv/getting-started/installation/

### "Configuration error: Missing required environment variable: SCOPUS_API_KEY"
The API key is not being passed to the server. Check:
- Your config file has `"SCOPUS_API_KEY": "your_actual_key"` in the `"env"` block
- The key doesn't contain extra spaces or quotes
- If using a `.env` file (source install), confirm it exists in the repo root

### Server appears in client but tools fail with 401
Your API key is invalid or expired. Regenerate it at [dev.elsevier.com](https://dev.elsevier.com/).

### Server appears in client but tools fail with 403
Your API key may not have Scopus access. Institutional access is required for many endpoints. Contact your librarian about getting `SCOPUS_INST_TOKEN`.

### "uvx scopus-mcp" is slow to start (first run)
uv is downloading and caching the package. Subsequent starts are instant (~0.2s).

### Claude Desktop shows the MCP but no tools appear
Restart Claude Desktop completely (not just the window — quit from the system tray/menu bar).

### Tool calls return empty results
Normal for very specific queries. Try broadening: replace `TITLE(...)` with `TITLE-ABS-KEY(...)` or remove `PUBYEAR` filters.

---

## Project Structure

```
scopus-mcp/
├── src/scopus_mcp/
│   ├── server.py        # FastMCP entry point
│   ├── config.py        # Env var configuration (pydantic-settings)
│   ├── client.py        # Async HTTP client + TTL cache + rate limiter
│   ├── exceptions.py    # Error hierarchy
│   ├── formatters.py    # Raw Scopus JSON → clean AI-friendly dicts
│   ├── tools/           # 7 MCP tools
│   └── resources/       # scopus://search-syntax static resource
├── scopus-researcher/   # Agent skill (install: npx skills add .../scopus-mcp@scopus-researcher)
│   ├── SKILL.md
│   └── references/      # Query patterns, workflows, output field reference
├── tests/               # Unit tests (19 cases, no network required)
├── setup_mcp.py         # Automated config installer
├── .env.example         # Environment variable template
└── pyproject.toml       # Package definition
```

---

## License

MIT
