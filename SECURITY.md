# Security Policy

## Reporting a vulnerability

Please report security issues privately rather than in a public issue:
open a [security advisory](https://github.com/JOSETRA44/scopus-mcp/security/advisories/new) on this repository.

Include what you did, what happened, and what you expected. You can expect an
acknowledgement within a few days.

## What this server sends, and where

Outbound requests go only to:

- `api.elsevier.com`

No telemetry, no analytics, and no data is sent anywhere else.

## Credentials

This server reads `SCOPUS_API_KEY`, `SCOPUS_INST_TOKEN` from the environment.

- The credential is sent **only** to the upstream host listed above, as a
  request header — never in a URL or query string, where it would be logged.
- It is **never** written to the cache: cache keys are a SHA-256 of the
  request path and parameters only, and no cache file contains the key.
- It is **never** echoed in an error message or in the JSON error envelope.
- Keep it in a `.env` file that is git-ignored, or in your MCP client's
  environment block. Never commit it.

## Scope

This project is a client for a public data source. Vulnerabilities in the
upstream API itself are out of scope here — report those to its operator.
