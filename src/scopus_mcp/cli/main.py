"""Command dispatch: argparse namespace in, rendered output and exit code out.

Every command keeps calling the same ``tools/*.py`` coroutines the MCP server
calls — this module never talks to httpx itself. Its jobs are: pick a cache
backend, run the tool, project rows, render, and map exceptions to exit codes.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any, AsyncIterator, Callable

from ..cache import DiskCache, build_cache, default_cache_dir
from ..client import ScopusClient
from ..config import ScopusSettings, get_settings
from ..exceptions import ScopusAPIError, ScopusAuthError, ScopusConfigError
from ..tools.abstract import do_get_abstract
from ..tools.author import do_get_author
from ..tools.citations import do_get_citation_count, do_get_citations_overview
from ..tools.search import (
    do_scopus_search,
    do_scopus_search_affiliations,
    do_scopus_search_authors,
    iter_scopus_search,
    iter_scopus_search_affiliations,
    iter_scopus_search_authors,
)
from .describe import build_manifest, manifest_rows
from .errors import classify
from .parser import build_parser, get_version
from .registry import COMMANDS
from .render import (
    EXIT_API,
    EXIT_AUTH,
    EXIT_NETWORK,
    EXIT_NOT_FOUND,
    EXIT_OK,
    EXIT_USAGE,
    Emitter,
    force_utf8,
    render_jsonl,
    render_table,
    to_json,
)
from .rows import project_affiliation, project_author, project_paper

# name -> (async row iterator factory, per-row projector)
_BULK: dict[str, tuple[Callable[..., AsyncIterator[dict]], Callable[[dict], dict]]] = {
    "search": (iter_scopus_search, project_paper),
    "search-authors": (iter_scopus_search_authors, project_author),
    "search-affiliations": (iter_scopus_search_affiliations, project_affiliation),
}


# ── Offline commands (no API call, no key required) ─────────────────────────

def _cmd_cache(args: argparse.Namespace, emitter: Emitter) -> int:
    cache = DiskCache()
    action = getattr(args, "action", "stats") or "stats"
    if action == "path":
        data: dict[str, Any] = {"path": str(default_cache_dir())}
    elif action == "clear":
        removed = cache.clear()
        data = {"path": str(cache.dir), "removed": removed}
        emitter.note(f"Cleared {removed} cache entries.")
    else:
        data = cache.stats()
    spec = COMMANDS["cache"]
    emitter.emit("cache", spec.rows_from(data), data=data, title=spec.title)
    return EXIT_OK


def _cmd_describe(args: argparse.Namespace, emitter: Emitter) -> int:
    parser = build_parser()
    target = getattr(args, "target", None)
    try:
        manifest = build_manifest(parser, target)
    except KeyError:
        emitter.emit_error(
            "describe", "usage", f"Unknown command: {target}",
            "Run `scopus describe --json` to list every command.",
        )
        return EXIT_USAGE
    rows = manifest_rows(manifest)
    # The manifest is the payload here, so json/jsonl emit it directly rather
    # than nesting it inside a result envelope.
    if emitter.fmt == "json":
        emitter.write(to_json(manifest))
    elif emitter.fmt == "jsonl":
        emitter.write(render_jsonl(manifest["commands"]))
    else:
        emitter.emit("describe", rows, data=manifest, title=f"scopus {manifest['version']}")
    return EXIT_OK


# ── Live commands ───────────────────────────────────────────────────────────

async def _probe(coro: Any) -> str:
    """Run a cheap live call and classify the result for the capability report."""
    try:
        await coro
        return "ok"
    except ScopusAuthError:
        return "requires SCOPUS_INST_TOKEN"
    except ScopusAPIError as exc:
        return f"FAIL: {exc}"


async def _cmd_check(client: ScopusClient, settings: ScopusSettings) -> dict[str, Any]:
    masked = (
        f"{settings.api_key[:8]}...{settings.api_key[-4:]}"
        if len(settings.api_key) > 12
        else "****"
    )
    # Live probes reflect the *actual* current entitlements of this API key —
    # Elsevier's per-endpoint access tiers vary independently of each other,
    # so a static guess table would be misleading.
    capabilities = {
        "search": await _probe(do_scopus_search(client, "TITLE(test)", count=1)),
        "abstract": "adaptive — tries full view, falls back to metadata-only per paper",
        "author / search-authors": await _probe(
            do_scopus_search_authors(client, "AUTHLASTNAME(Smith)", count=1)
        ),
        "search-affiliations": await _probe(
            do_scopus_search_affiliations(client, "AFFIL(MIT)", count=1)
        ),
        "citation-count / citations": await _probe(
            do_get_citation_count(client, scopus_id="85180904906")
        ),
    }
    return {
        "api_key": masked,
        "inst_token_configured": bool(settings.inst_token),
        "capabilities": capabilities,
    }


async def _dispatch(client: ScopusClient, args: argparse.Namespace) -> dict[str, Any]:
    """Single page / single record commands — the same coroutines MCP calls."""
    command = args.command
    if command == "search":
        return await do_scopus_search(client, args.query, args.count, args.start, args.view)
    if command == "abstract":
        return await do_get_abstract(client, args.identifier_type, args.identifier)
    if command == "author":
        return await do_get_author(client, args.author_id)
    if command == "search-authors":
        return await do_scopus_search_authors(client, args.query, args.count)
    if command == "search-affiliations":
        return await do_scopus_search_affiliations(client, args.query, args.count)
    if command == "citation-count":
        return await do_get_citation_count(client, args.scopus_id, args.doi)
    if command == "citations":
        return await do_get_citations_overview(
            client, args.scopus_id, args.start_year, args.end_year
        )
    raise ValueError(f"Unhandled command: {command}")


async def _run_bulk(
    client: ScopusClient, args: argparse.Namespace, emitter: Emitter
) -> int:
    """Harvest a paginated endpoint, streaming rows where the format allows."""
    command = args.command
    spec = COMMANDS[command]
    make_iter, project = _BULK[command]
    max_rows = max(1, int(args.max_rows))

    def on_page(emitted: int, total: int) -> None:
        emitter.note(f"[{command}] {emitted}/{min(total, max_rows)} rows harvested...")

    kwargs: dict[str, Any] = {
        "max_rows": max_rows,
        "start": getattr(args, "start", 0),
        "on_page": on_page,
    }
    if command == "search":
        kwargs["view"] = args.view

    streaming = emitter.fmt in ("jsonl", "csv")
    if streaming:
        emitter.begin_stream(spec.row_fields)
    buffered: list[dict] = []
    count = 0
    async for raw_row in make_iter(client, args.query, **kwargs):
        row = project(raw_row)
        count += 1
        if streaming:
            emitter.write_row(row)
        else:
            buffered.append(row)

    if not streaming:
        meta = {"query": args.query, "harvested": count, "max": max_rows,
                "rate_limit": client.rate_limit}
        if emitter.fmt == "json":
            emitter.emit(command, buffered, data={"rows": buffered}, meta=meta,
                         cached=client.all_cached)
        elif emitter.fmt == "md":
            emitter.emit(command, buffered, title=spec.title)
        else:
            emitter.write(render_table(buffered, emitter.style, spec.title))
    emitter.note(f"[{command}] done — {count} rows.")
    return EXIT_OK


async def run_cli(args: argparse.Namespace, emitter: Emitter) -> int:
    command: str = args.command

    if command == "cache":
        return _cmd_cache(args, emitter)
    if command == "describe":
        return _cmd_describe(args, emitter)

    settings = get_settings()
    backend = "none" if getattr(args, "no_cache", False) else "disk"
    cache = build_cache(backend)

    async with ScopusClient(settings, cache=cache, refresh=args.refresh) as client:
        if command == "check":
            data = await _cmd_check(client, settings)
            spec = COMMANDS["check"]
            rows = spec.rows_from(data)
            emitter.emit("check", rows, data=data, cached=client.all_cached,
                         title=spec.title)
            return EXIT_OK if data["capabilities"]["search"] == "ok" else EXIT_API

        if getattr(args, "fetch_all", False):
            return await _run_bulk(client, args, emitter)

        spec = COMMANDS[command]
        data = await _dispatch(client, args)
        rows = spec.rows_from(data)
        meta = spec.meta_from(data)
        meta["rate_limit"] = client.rate_limit
        if data.get("access_note"):
            emitter.note(f"Note: {data['access_note']}")
        emitter.emit(command, rows, data=data, meta=meta, cached=client.all_cached,
                     title=spec.title)
        return EXIT_OK


def main_cli(args: argparse.Namespace) -> int:
    """Entry point used by the console scripts. Owns the error boundary."""
    fmt = getattr(args, "format", "table") or "table"
    output = getattr(args, "output", None)
    emitter = Emitter(
        fmt=fmt,
        output=Path(output) if output else None,
        quiet=getattr(args, "quiet", False),
        no_color=getattr(args, "no_color", False),
    )
    try:
        with emitter:
            return asyncio.run(run_cli(args, emitter))
    except KeyboardInterrupt:
        emitter.warn("Interrupted.")
        return EXIT_USAGE
    except BaseException as exc:  # noqa: BLE001 - the CLI's error boundary
        if isinstance(exc, SystemExit):
            raise
        code, error_code, hint = classify(exc, getattr(args, "command", ""))
        emitter.emit_error(getattr(args, "command", ""), error_code, str(exc), hint)
        return code


def main() -> None:
    """Console-script entry: subcommand → CLI, no subcommand → MCP stdio server."""
    from dotenv import load_dotenv

    force_utf8()

    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        print(get_version())
        return

    load_dotenv()

    if args.command is not None:
        raise SystemExit(main_cli(args))

    # No subcommand: start the MCP stdio server (for use by an MCP client).
    # Imported lazily so plain CLI runs never pay for the FastMCP import.
    from ..server import create_app

    try:
        app = create_app()
    except ScopusConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        raise SystemExit(EXIT_AUTH) from exc

    app.run(transport="stdio")
