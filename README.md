<img width="1600" height="500" alt="SCOPUS-MCP _ Minimal GitHub banner · 1600×500" src="https://github.com/user-attachments/assets/20cf9e90-f9cf-49e6-8997-cc5662e6d84e" />

# Scopus MCP

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)

<!-- mcp-name: io.github.JOSETRA44/scopus-mcp -->

**Search academic literature from your AI assistant or terminal.** Find papers,
retrieve abstracts, explore citations and export references with Elsevier Scopus.
Includes a guided setup, 12 MCP tools and a standalone CLI.
**Después de inatalar el MCP los agentes pueden conectarse a scopus y acceder a los miles de papers indexados**

[Quick start](#quick-start) · [Installation methods](#installation-methods) ·
[API key setup](#api-key-setup) · [Connect your AI assistant](#connect-your-ai-assistant) ·
[Examples](#examples) · [Troubleshooting](#troubleshooting)

**Official package name:** `josetra-scopus-mcp` · **CLI commands:** `scopus`,
`scps`, `scopus-mcp`, `josetra-scopus-mcp` · **Python import:** `scopus_mcp`.

The first PyPI release is being prepared. The PyPI installation commands below
work after that release is published; until then, use a GitHub source or local
checkout. The unrelated PyPI name `scopus-mcp` is not this distribution.

## Quick start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```sh
uv tool install josetra-scopus-mcp
uv tool update-shell
```

**Close and reopen your terminal** so the PATH change takes effect. Then:

```sh
scopus setup
scopus check
scopus search 'TITLE-ABS-KEY("machine learning")' --count 5
```

`setup` asks for your API key without displaying it. Get a key from the
[Elsevier developer portal](https://dev.elsevier.com/). Endpoint access depends on
your Elsevier entitlements; a key alone does not guarantee access to every tool.

For Spanish prompts: `scopus setup --language es`.

## Installation methods

Choose **one** method. You do not need to install the package multiple ways.

| You want to… | Method | How you run commands |
|---|---|---|
| Try it without adding commands to PATH | [A. uvx](#a-run-with-uvx) | `uvx josetra-scopus-mcp …` |
| Run `scopus` from any folder | [B. Install on PATH](#b-install-on-your-path) | `scopus …` |
| Use Python and pip | [C. pip](#c-install-with-pip) | Virtual-environment executable |
| Run or install a downloaded folder | [D. Local path](#d-use-a-local-folder) | `uvx --from "/path/…" scopus …` |
| Develop or modify the code | [E. Source checkout](#e-work-from-source) | `uv run scopus …` |

Python **3.11 or newer** is required. uv can download a compatible Python when
needed. Git is required for `git+https://…` installs and cloning; a local folder
or wheel can be installed without Git.

<details>
<summary>Install uv first</summary>

**Windows — PowerShell**

```powershell
winget install --id astral-sh.uv -e
```

**macOS / Linux**

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Reopen the terminal, then verify:

```sh
uv --version
uvx --version
```

Alternative installers are listed in the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

</details>

### A. Run with uvx

Run the official PyPI package in an isolated environment, without adding commands to your PATH:

```sh
uvx josetra-scopus-mcp --help
uvx josetra-scopus-mcp setup
uvx josetra-scopus-mcp check
```

The equivalent longer form is `uv tool run josetra-scopus-mcp --help`.
To select the shorter executable explicitly, use `uvx --from josetra-scopus-mcp scopus --help`.
uv caches the tool environment, so it need not download everything each time.

To request the latest published release on a later run:

```sh
uvx josetra-scopus-mcp@latest --help
```

### B. Install on your PATH

Recommended for regular terminal use. uv creates an isolated tool environment
and exposes the `scopus`, `scps` and `scopus-mcp` commands:

```sh
uv tool install josetra-scopus-mcp
uv tool update-shell
```

Reopen your terminal. These commands should now work **from any folder**:

```sh
scopus --help
scopus setup
scopus check
```

To reinstall this distribution explicitly:

```sh
uv tool install --reinstall josetra-scopus-mcp
```

Locate the executable directory with `uv tool dir --bin`. To see which executable
your terminal will use:

```powershell
# Windows — PowerShell
(Get-Command scopus).Source
(Get-Command scopus-mcp).Source
```

```sh
# macOS / Linux
command -v scopus
command -v scopus-mcp
```

### C. Install with pip

Use a virtual environment to keep dependencies separate from your system Python.
These examples call its executables directly, so activation is optional.

**Windows — PowerShell**

```powershell
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install josetra-scopus-mcp
& .\.venv\Scripts\scopus.exe setup
& .\.venv\Scripts\scopus.exe check
```

Use your installed Python version if it is newer than 3.11.

**macOS / Linux**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install josetra-scopus-mcp
.venv/bin/scopus setup
.venv/bin/scopus check
```

Check `python3 --version` first; it must be at least 3.11. To use `scopus` without
its path, activate the environment in each terminal, or choose method B for a
persistent PATH installation. MCP clients should use the **absolute path** to
this environment's `scopus-mcp` executable.

### D. Use a local folder

Already cloned or downloaded this repository? Point uv directly to the folder
containing `pyproject.toml`. Quote paths containing spaces.

**Windows — PowerShell**

```powershell
uvx --from "C:/Projects/scopus-mcp" scopus setup
uvx --from "C:/Projects/scopus-mcp" scopus check
```

**macOS / Linux**

```sh
uvx --from "/absolute/path/to/scopus-mcp" scopus setup
uvx --from "/absolute/path/to/scopus-mcp" scopus check
```

To install that folder on PATH instead:

```sh
uv tool install --editable "/absolute/path/to/scopus-mcp"
uv tool update-shell
```

On Windows, replace the path with `C:/Projects/scopus-mcp`. Reopen the terminal,
then run `scopus --help`. An editable installation reads your local source;
keep the folder in place. If replacing an existing tool installation, add
`--reinstall` explicitly.

### E. Work from source

To install from GitHub before the first PyPI release (Git required):

```sh
uv tool install --from git+https://github.com/JOSETRA44/scopus-mcp.git josetra-scopus-mcp
uv tool update-shell
```

Or clone the repository for development:

```sh
git clone https://github.com/JOSETRA44/scopus-mcp.git
cd scopus-mcp
uv sync --group dev
uv run scopus setup
uv run scopus check
```

No PATH installation is needed: prefix commands with `uv run` while inside the
repository. From another folder, use an absolute directory:

```sh
uv --directory "/absolute/path/to/scopus-mcp" run scopus --help
```

## API key setup

After installing, use `scopus setup` (or the corresponding uvx/uv run command).
The wizard guides you through:

1. Entering your Elsevier API key with hidden input.
2. Optionally entering an institutional token.
3. Confirming where to save the configuration.

```sh
scopus setup --language es
scopus setup --show
scopus setup --check
```

Enter preserves an existing value; `-` removes a saved institutional token.
Ctrl+C cancels. `--show` displays status and path, never credentials.
`--check` tests the saved credentials after saving and consumes API quota.

Configuration is stored for your operating-system account and works across
folders. The file is plaintext with restricted permissions, not an encrypted
vault. Environment variables override the working-directory `.env`, which
in turn overrides the saved user configuration.

For containers or automation, supply `SCOPUS_API_KEY` and, if applicable,
`SCOPUS_INST_TOKEN` through the environment. To save those values explicitly,
use `scopus setup --from-env`; add `--force` to replace an existing saved file.
A container or another operating-system user does not automatically inherit your
saved local configuration.

## Connect your AI assistant

First run setup using the same source and account that the client will use.
Then add **one** of the following server definitions in your client's MCP settings.

### Run directly with uvx

For clients using `mcpServers`, such as Claude Desktop or Cursor:

```json
{
  "mcpServers": {
    "scopus": {
      "command": "uvx",
      "args": ["josetra-scopus-mcp"]
    }
  }
}
```

### Use an installed executable

If you installed on PATH, use `"command": "scopus-mcp"` with `"args": []`.
If the desktop app does not inherit your shell's PATH, use the absolute executable
path reported by `Get-Command scopus-mcp` or `command -v scopus-mcp`.

For a pip virtual environment, a Windows example is:

```json
{
  "mcpServers": {
    "scopus": {
      "command": "C:/Projects/scopus-mcp/.venv/Scripts/scopus-mcp.exe",
      "args": []
    }
  }
}
```

Replace the example path with your actual environment. On macOS/Linux it ends
in `.venv/bin/scopus-mcp`. Forward slashes in Windows JSON paths avoid escaping
backslashes.

### Run a local checkout

```json
{
  "mcpServers": {
    "scopus": {
      "command": "uv",
      "args": ["--directory", "C:/Projects/scopus-mcp", "run", "scopus-mcp"]
    }
  }
}
```

Replace the directory with your absolute path. This also works on macOS/Linux.

### VS Code

In `.vscode/mcp.json`, use the `servers` wrapper and `stdio` transport:

```json
{
  "servers": {
    "scopus": {
      "type": "stdio",
      "command": "uvx",
      "args": ["josetra-scopus-mcp"]
    }
  }
}
```

Restart or reconnect the MCP server in your client. Confirm that it lists the
Scopus tools, then ask: **“Find five papers about machine learning in medicine.”**

> Running `scopus-mcp`, `scopus` or `scps` **without a subcommand** starts the MCP
> server and waits for input. A quiet terminal is expected. Use `--help` for CLI
> help, `setup` for configuration or `check` for diagnostics.

## Examples

These examples assume a PATH installation; otherwise add your uvx or uv run prefix.

```sh
scopus search 'TITLE-ABS-KEY("machine learning")' --count 5
scopus abstract 10.1038/nature14539 --type doi -f json
scopus search-authors 'AUTHLASTNAME(Smith)' --start 25
scopus author 7401234567
scopus citation-count --doi 10.1038/nature14539
scopus citations 85180904906 --start-year 2020
```

Export references or keep a reproducible search record:

```sh
scopus search 'TITLE-ABS-KEY(biodiversity)' --all --max 500 -f ris -o papers.ris --record search-record.json
scopus abstract 10.1038/nature14539 --type doi -f bibtex -o paper.bib
scopus search 'AU-ID(7401234567)' -f csl-json -o papers.json
```

General formats: `table`, `json`, `jsonl`, `csv`, `md`. Paper search and abstract
retrieval also support `ris`, `bibtex`, `csl-json`. Search records can have
incomplete author metadata; retrieve individual abstracts for richer exports.

`--all` retrieves up to `--max` and the implemented 5,000-record offset window.
Check `complete_corpus`, `truncated` and `stop_reason` before treating results as
complete. Missing metrics remain null, not zero. JSON preserves original retrieval
timestamps separately from the time it was served; `--record` saves query and
completeness metadata without credentials.

```sh
scopus describe --json          # Command and output-schema discovery
scopus cache stats -f json
scopus cache clear
```

Data goes to stdout; notes go to stderr. `--json` aliases `-f json`.

| Exit code | Meaning |
|---|---|
| 0 | Successful operation, including empty results |
| 1 | API/unexpected response |
| 2 | Usage error or interrupted operation |
| 3 | Resource not found |
| 4 | Authentication/configuration error |
| 5 | Quota/rate limit |
| 6 | Network failure or timeout |

## MCP tools and resources

| Tool | Purpose |
|---|---|
| `scopus_search` | Paginated paper search |
| `scopus_search_authors` | Paginated author search |
| `scopus_search_affiliations` | Paginated institution search |
| `scopus_get_abstract` | Paper by Scopus ID, DOI, EID or PubMed ID |
| `scopus_get_abstracts` | Batches of up to 25 identifiers |
| `scopus_get_author` | Author profile and available metrics |
| `scopus_get_citation_count` | Citation total |
| `scopus_get_citations_overview` | Citations by year |
| `scopus_check_access` | Live endpoint diagnostics |
| `scopus_get_references` | Available references from a paper |
| `scopus_get_citing_documents` | Paginated citing papers |
| `scopus_analyze_results` | Aggregates over a bounded retrieved corpus |

Resources: `scopus://search-syntax`, `scopus://subject-areas`, `scopus://api-reference`.
Prompts: `systematic_literature_review`, `author_impact_analysis`, `research_trend_query`.
Prompts are workflow templates; corpus aggregates describe retrieved documents,
not necessarily all matching literature.

## Configuration reference

| Variable | Default | Purpose |
|---|---|---|
| `SCOPUS_API_KEY` | Required or saved through setup | Elsevier API key |
| `SCOPUS_INST_TOKEN` | Optional | Institutional token when applicable |
| `SCOPUS_CACHE_TTL` | `300` | Cache lifetime in seconds; `0` disables caching |
| `SCOPUS_MAX_RETRIES` | `3` | Additional attempts, 0–10 |
| `SCOPUS_MAX_WAIT_SECONDS` | `10` | Cumulative quota/retry wait budget, 0–60 seconds |
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR or CRITICAL |

Quotas are tracked per API family and depend on your entitlement. Large reset
delays return an error rather than waiting for days. See
[Elsevier's access and quota guidance](https://dev.elsevier.com/api_key_settings.html).

## Update or uninstall

**PyPI installation on PATH**

```sh
uv tool upgrade josetra-scopus-mcp
```

**Source checkout**

```sh
git pull --ff-only
uv sync --group dev
```

For pip, run `python -m pip install --upgrade josetra-scopus-mcp` with the same environment's Python. Restart running MCP clients after updating. For repeatable deployments, replace
the Git source with `git+https://github.com/JOSETRA44/scopus-mcp.git@COMMIT_SHA`,
using the full commit you intend to install.

Uninstall a uv tool with `uv tool uninstall josetra-scopus-mcp`. For pip, use the same
virtual environment's Python: `python -m pip uninstall josetra-scopus-mcp`.
Uninstalling the package does not remove your saved credentials; locate them
with `scopus setup --show` before uninstalling if you also want to remove them.

## Troubleshooting

| Symptom | What to do |
|---|---|
| `uv` / `uvx` not found | Install uv and reopen the terminal. |
| `scopus` not found after a uv install | Run `uv tool update-shell`, reopen the terminal and inspect `uv tool dir --bin`. |
| `setup` is missing or tool names differ | Install `josetra-scopus-mcp`; the PyPI package named `scopus-mcp` is a different project. |
| MCP client cannot find the command | Use the absolute executable path; desktop apps may have a different PATH. |
| Terminal appears to wait forever | No subcommand starts MCP stdio. Use `scopus --help` for terminal use. |
| Missing API key | Run setup under the same account as the MCP client. |
| HTTP 401 / 403 | Run `scopus check`; verify credentials and endpoint entitlement with Elsevier or your institution. |
| Saved key appears ignored | Environment variables and the working-directory `.env` override saved configuration. |
| Hidden input is unavailable | Run setup in an interactive terminal or inject credentials through the environment. |
| Windows reports an executable is in use during update | Stop that MCP server in its client, update, then restart it. |

## Development

From a source checkout:

```sh
uv run pytest
uv run ruff check src tests
uv run mypy
uv run python -m build
```

Tests use fake credentials and mocked HTTP. CI is configured for Windows/Linux
and Python 3.11/3.13, including MCP transport and package installation checks.
See [CHANGELOG.md](CHANGELOG.md), [IMPLEMENTATION.md](IMPLEMENTATION.md) and
the [PyPI release guide](docs/PUBLISHING.md).

[MIT license](LICENSE) · [Report an issue](https://github.com/JOSETRA44/scopus-mcp/issues)
