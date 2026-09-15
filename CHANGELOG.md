# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-22

### Added

- Conformance with [`ARSENAL-SPEC.md`](../ARSENAL-SPEC.md), the CLI contract shared
  by every research server in this workspace:
  - Five output formats: `table`, `json`, `jsonl`, `csv`, `md`.
  - A stable JSON envelope (`ok`, `command`, `source`, `fetched_at`, `cached`,
    `count`, `meta`, `data`, `rows`) and a matching error envelope carrying an
    actionable `hint`.
  - Seven documented exit codes, so a script can branch on *why* a call failed.
  - A disk cache shared across invocations, with `--refresh`, `--no-cache` and a
    `cache stats|clear|path` subcommand.
  - `describe --json`: a machine-readable manifest derived from the parser
    itself, so it cannot drift from the real commands.
  - UTF-8 output forced on Windows consoles, which default to a code page that
    cannot encode accented text.
- Offset pagination with quota reporting in the envelope's meta.
- `server.json` for the official MCP registry, plus `LICENSE`, `SECURITY.md` and
  `CONTRIBUTING.md`.

### Changed

- Data goes to stdout and notes to stderr, so piping to `jq` always yields
  parseable output.

[Unreleased]: https://github.com/JOSETRA44/scopus-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/JOSETRA44/scopus-mcp/releases/tag/v0.1.0
