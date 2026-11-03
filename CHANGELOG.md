# Changelog

## Unreleased

The first official PyPI distribution is prepared as `josetra-scopus-mcp` 0.1.0.
Publication uses `publish.yml`, GitHub environment `pypi` and Trusted Publishing.
The matching console alias supports `uvx josetra-scopus-mcp`; existing commands remain.

- Guided `scopus setup` in English/Spanish with hidden secret input, explicit
  save, private atomic user configuration, environment import and status display.
- Typed MCP outputs and read-only annotations; services shared with the CLI.
- Five additional MCP tools: batch abstracts, access diagnostics, references,
  citing documents and bounded corpus analysis (12 tools in total).
- Correct empty-result handling, unknown metrics, citation years and review dates.
- Per-API quotas, bounded Retry-After/backoff and transient HTTP retries.
- Credential-isolated caches, bounded memory and atomic disk writes.
- Author/institution pagination and explicit corpus completeness.
- RIS, BibTeX and CSL-JSON export; reproducibility records via `--record`.
- Retrieval provenance distinct from serving time.
- CI matrix, transport tests, packaging smoke checks and regression coverage.

### Compatibility notes

- MCP SDK minimum is now 1.28; v2 migration is separate.
- Missing metrics are null, not zero; malformed upstream payloads are errors.
- Citation range defaults now include the current UTC year.
- Cache entries from earlier versions are not reused across credential namespaces.
- `check` reports endpoints independently instead of grouped capabilities.
- Existing command names, general output formats and stdio startup are retained.
- Credentials are stored locally with restricted permissions, not encryption.
