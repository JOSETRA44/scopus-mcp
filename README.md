# Scopus MCP

<!-- mcp-name: io.github.JOSETRA44/scopus-mcp -->

Search Elsevier Scopus from a terminal or an AI assistant: papers, abstracts,
researchers, references and citations. Python 3.11+.

You need an Elsevier API key. **A key does not guarantee access to every API.**
Endpoint permissions, institutional tokens, network requirements and quotas depend
on your Elsevier entitlements. See the [developer portal](https://dev.elsevier.com/)
and [access guidance](https://dev.elsevier.com/api_key_settings.html).

## Install and configure

With [uv](https://docs.astral.sh/uv/getting-started/installation/):

```sh
uv tool install scopus-mcp
scopus setup
scopus check
```

Or install with `python -m pip install scopus-mcp`, then run `scopus setup`.
Without a persistent installation:

```sh
uvx --from scopus-mcp scopus setup
uvx --from scopus-mcp scopus check
```

`scopus`, `scps` and `scopus-mcp` are equivalent commands.

### Guided setup

The wizard has three numbered steps: paste your API key, optionally enter an
institutional token, then confirm the save. Secret entry is hidden. Ctrl+C cancels.
No API requests occur unless you request `--check`.

```sh
scopus setup --language es       # Asistente en español
scopus setup --language en       # English wizard
scopus setup --show              # Status and path; never credentials
scopus setup --check             # Save, then test endpoint access
```

Enter preserves an existing key/token. A `-` in the token prompt removes it.
The wizard uses text prompts, works without colour and can follow the system
language. It never runs automatically when an MCP client starts the server.

Credentials are saved **as local plaintext**, with restricted file permissions
(Windows ACL or POSIX mode 0600). This is not an encrypted credential vault.
`scopus setup --show` displays the exact location in your account's configuration
directory. Treat backups of this file as credentials.

Configuration precedence, highest first:

1. Environment variables.
2. `.env` in the current working directory.
3. The user configuration saved by `scopus setup`.

Check for overrides if a saved change seems ineffective. Automated deployments
can inject environment variables directly. To explicitly save injected values:

```sh
scopus setup --from-env          # Requires SCOPUS_API_KEY in the environment
scopus setup --from-env --force  # Explicitly replace saved credentials
```

The wizard does not accept keys as command-line arguments, keeping them out of
command history and process arguments.

`setup --check` tests the saved credentials explicitly. `scopus check` tests the
effective configuration, including environment/project overrides.

## Connect an MCP client

After running setup under the same operating-system account as the client:

```json
{
  "mcpServers": {
    "scopus": {"command": "uvx", "args": ["scopus-mcp"]}
  }
}
```

Use your client's MCP configuration interface. Clients expecting a `servers`
object can use this equivalent form:

```json
{
  "servers": {
    "scopus": {"type": "stdio", "command": "uvx", "args": ["scopus-mcp"]}
  }
}
```

Containers/remote hosts do not share your local configuration: inject
`SCOPUS_API_KEY` and, if applicable, `SCOPUS_INST_TOKEN` there.
Running a command **without a subcommand starts MCP over stdio** and waits for
client input. Use `scopus --help` for interactive terminal commands.

## Terminal examples

```sh
scopus search 'TITLE-ABS-KEY("machine learning")' --count 5
scopus abstract 10.1038/nature14539 --type doi -f json
scopus search-authors 'AUTHLASTNAME(Smith)' --start 25
scopus search-affiliations 'AFFIL(MIT)' --count 10
scopus author 7401234567
scopus citation-count --doi 10.1038/nature14539
scopus citations 85180904906 --start-year 2020
```

Citation ranges end at the current UTC year when `--end-year` is omitted.
`scopus check` tests all seven original endpoints independently without cache.
It consumes quota and distinguishes authorization, quota, network and response
failures. Sample-record failures do not establish absence of entitlement.

### Export and reproducibility

General formats: `table`, `json`, `jsonl`, `csv`, `md`. Paper search and abstract
retrieval also support `ris`, `bibtex` and `csl-json`.

```sh
scopus search 'TITLE-ABS-KEY(biodiversity)' --all --max 500 -f ris -o papers.ris --record search-record.json
scopus abstract 10.1038/nature14539 --type doi -f bibtex -o paper.bib
scopus search 'AU-ID(7401234567)' -f csl-json -o papers.json
```

Exports preserve available metadata without inventing complete author lists or
publication types. Search may supply only a first author; retrieve the abstract
record for richer metadata when your entitlement allows it.

`--all` pages up to `--max` (default 1,000) and the implemented 5,000-record offset
window. It deduplicates by source identifier. JSON metadata and `--record` expose
`total_results`, `truncated`, `complete_corpus`, `stop_reason`, `next_start` and duplicate counts.
Partial corpora produce a warning even with `--quiet`. A successful exit means
successful execution, **not that all matching literature was retrieved**.

`--record FILE` saves parameters, software version, retrieval timestamps and
completeness without credentials. It is not an immutable database snapshot or a
complete systematic-review protocol. JSONL/CSV remain row streams; use the
separate record for their metadata.

```sh
scopus describe --json
scopus describe search --json
```

JSON envelopes include `ok`, `command`, `source`, `cached`, `count`, `meta`, `data`
and `rows`. `count` equals the row count. `retrieved_at` is the original retrieval
time, `served_at` is the output time and `fetched_at` remains a compatibility alias
for retrieval time. Mixed-page searches report retrieval times in metadata.
Unknown legacy cache timestamps stay null. Data goes to stdout; notes go to
stderr. `-o FILE` writes data to a file; `--json` aliases `-f json`.

| Exit | Meaning |
|---|---|
| 0 | Success, including empty results |
| 1 | API/unexpected response |
| 2 | Invalid usage/interrupted operation |
| 3 | Resource not found |
| 4 | Authentication/configuration error |
| 5 | Quota/rate limit or retry wait budget exceeded |
| 6 | Network failure or timeout |

## MCP capabilities

Tools advertise typed schemas and read-only hints. Unknown metrics remain null.
Failures use MCP error results; batches retain individual successes and failures.

| Tool | Purpose |
|---|---|
| `scopus_search` | Paginated paper search |
| `scopus_search_authors` | Paginated author search |
| `scopus_search_affiliations` | Paginated institution search |
| `scopus_get_abstract` | Paper by Scopus ID, DOI, EID or PubMed ID |
| `scopus_get_abstracts` | 1–25 identifiers with bounded concurrency |
| `scopus_get_author` | Author profile and available metrics |
| `scopus_get_citation_count` | Citation total by ID or DOI |
| `scopus_get_citations_overview` | Year-by-year citations |
| `scopus_check_access` | Live endpoint diagnostics |
| `scopus_get_references` | Available references from a paper |
| `scopus_get_citing_documents` | Paginated citing papers |
| `scopus_analyze_results` | Aggregates over an explicitly bounded corpus |

Resources: `scopus://search-syntax`, `scopus://subject-areas`,
`scopus://api-reference`. Prompts: `systematic_literature_review`,
`author_impact_analysis`, `research_trend_query`.

Prompts are templates, not completed research. Citation analysis is optional and
must not substitute for eligibility or methodological-quality assessment.
Partial-corpus aggregates must not be reported as whole-database statistics.
Reference/citing access is entitlement-dependent; missing reference data is not
reported as an empty bibliography without evidence.

## Cache and request limits

MCP uses a bounded memory cache; CLI uses an atomic disk cache. Entries are
isolated by a non-reversible credential digest. Cache files contain research
metadata, not API keys.

```sh
scopus cache stats -f json
scopus cache path
scopus cache clear
scopus search 'TITLE(test)' --refresh
scopus search 'TITLE(test)' --no-cache
```

Rate state is separate per API family. HTTP 429 and 500/502/503/504 use bounded
retries; `Retry-After` supports seconds and dates. Large quota delays return an
error rather than waiting for days.

| Variable | Default | Purpose |
|---|---|---|
| `SCOPUS_API_KEY` | Required | API key, or use saved setup configuration |
| `SCOPUS_INST_TOKEN` | Optional | Institutional token when applicable |
| `SCOPUS_CACHE_TTL` | `300` | Cache lifetime in seconds; `0` disables reads and writes |
| `SCOPUS_MAX_RETRIES` | `3` | Additional attempts, 0–10 |
| `SCOPUS_MAX_WAIT_SECONDS` | `10` | Cumulative quota/retry wait budget, 0–60 seconds |
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR or CRITICAL |

## Development

```sh
git clone https://github.com/JOSETRA44/scopus-mcp.git
cd scopus-mcp
uv sync --group dev
uv run scopus setup
uv run pytest
uv run ruff check src tests
uv run mypy
uv run python -m build
```

Tests use fake credentials, temporary directories and mocked HTTP. The stdio test
starts a real MCP subprocess with upstream HTTP blocked. CI is configured for
Windows/Ubuntu and Python 3.11/3.13, plus clean wheel installation checks.

The tested SDK line is `mcp>=1.28,<2`; SDK v2 requires a separate compatibility
migration. Shared services do not import FastMCP. See
[IMPLEMENTATION.md](IMPLEMENTATION.md) for scope and remaining release gates.

```text
src/scopus_mcp/
  services/       Shared operations and validation
  tools/          MCP adapters
  models.py       Public schemas
  client.py       HTTP, quotas, retries and provenance
  cache.py        Memory/disk cache
  cli/            Setup, commands, export and search records
  prompts/        Research workflow templates
  resources/      Query and API references
  server.py       MCP assembly and lifecycle
```

Missing credentials: run `scopus setup`. Forbidden endpoint: inspect `scopus check`
and ask your institution/Elsevier about access; retries do not grant permission.
If hidden terminal input is unavailable, setup suggests environment configuration.

MIT license. See [LICENSE](LICENSE).
