# Public-release implementation plan

The package remains Python. Existing command names and the no-subcommand MCP
stdio entry point remain compatible. No release is published by this work.

## Implemented in this change

- [x] User-scoped `scopus setup`, hidden secret entry, English/Spanish wizard,
      explicit save, atomic private file replacement, noninteractive environment
      import and redacted status. Environment and project settings can override it.
- [x] Per-endpoint quotas, bounded waits, Retry-After handling and transient retries.
- [x] Credential-scoped, bounded/atomic cache and original retrieval timestamps.
- [x] Unknown metrics remain null; empty/error payloads do not become papers.
- [x] Services shared by CLI/MCP; typed MCP results, schemas and read-only hints.
- [x] Paginated authors/institutions, completeness metadata and search records.
- [x] Dynamic citation year, inclusive review years and optional citation analysis.
- [x] Independent endpoint diagnostics without cache, CLI and MCP.
- [x] Bounded batch abstracts with per-item errors.
- [x] References, citing-document search and bounded corpus aggregates with
      explicit completeness, entitlement and missing-metadata limitations.
- [x] RIS, BibTeX and CSL-JSON export with provenance-aware CLI envelopes.
- [x] CI configuration for Windows/Linux, Python 3.11/3.13, static checks,
      isolated packaging and real MCP stdio tests without external requests.

## Release gates

- Run all local tests and build/install the final wheel after integration.
- Run the configured CI matrix on GitHub; local Windows checks are not a
  substitute for results on other operating systems/Python versions.
- Exercise Elsevier endpoints with approved test credentials before claiming
  live API/entitlement compatibility. Offline fixtures prove contracts, not access.

## Deliberately separate follow-ups

- SDK v2 migration: retain tested `mcp>=1.28,<2` until a separate compatibility
  migration can validate the public client matrix. Do not simply remove the cap.
- Remote multi-user hosting: OAuth, per-user credential storage and operational
  telemetry belong to that deployment, not the current local stdio install.
- Search evaluations using a curated scientific corpus and measured retrieval
  quality. Unit tests do not establish scientific recall or research validity.
