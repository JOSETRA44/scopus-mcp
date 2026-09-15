"""Agent discovery: turn the live argparse parser into a JSON manifest.

Nothing here is hand-maintained — the command list, arguments, options, types
and defaults are all read back off the parser object, so a subcommand added in
``parser.py`` shows up in ``describe --json`` without a second edit. Only the
row shapes and examples come from ``registry.py``.
"""

from __future__ import annotations

import argparse
from typing import Any

from .parser import get_version
from .registry import COMMANDS
from .render import EXIT_CODES, FORMATS

SOURCE = {
    "api": "Elsevier Scopus",
    "base_url": "https://api.elsevier.com",
    "auth": "required (SCOPUS_API_KEY; SCOPUS_INST_TOKEN for author/citation endpoints)",
}

_TYPE_NAMES = {int: "integer", float: "number", str: "string"}


def _subparsers(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    return {}


def _type_of(action: argparse.Action) -> str:
    if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
        return "boolean"
    if action.type is not None:
        return _TYPE_NAMES.get(action.type, getattr(action.type, "__name__", "string"))
    return "string"


def _visible(action: argparse.Action) -> bool:
    """Skip -h and every deliberately hidden alias (help=SUPPRESS)."""
    if isinstance(action, argparse._HelpAction):
        return False
    return action.help != argparse.SUPPRESS


def _describe_action(action: argparse.Action) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "name": action.option_strings[0] if action.option_strings else action.dest,
        "type": _type_of(action),
        "help": (action.help or "").strip(),
    }
    if action.option_strings:
        entry["flags"] = list(action.option_strings)
        entry["required"] = bool(action.required)
        entry["repeatable"] = action.nargs in ("*", "+") or isinstance(
            action, argparse._AppendAction
        )
    else:
        entry["required"] = action.nargs not in ("?", "*")
    if action.default is not argparse.SUPPRESS:
        entry["default"] = action.default
    if action.choices:
        entry["choices"] = list(action.choices)
    return entry


def describe_command(name: str, sub: argparse.ArgumentParser) -> dict[str, Any]:
    """One manifest entry, merging parser introspection with registry metadata."""
    spec = COMMANDS.get(name)
    arguments: list[dict[str, Any]] = []
    options: list[dict[str, Any]] = []
    for action in sub._actions:
        if not _visible(action):
            continue
        (options if action.option_strings else arguments).append(_describe_action(action))
    return {
        "name": name,
        "summary": (sub.description or "").strip(),
        "arguments": arguments,
        "options": options,
        "row_fields": list(spec.row_fields) if spec else [],
        "supports_all": bool(spec.supports_all) if spec else False,
        "examples": list(spec.examples) if spec else [],
    }


def build_manifest(
    parser: argparse.ArgumentParser, target: str | None = None
) -> dict[str, Any]:
    """The full ``describe --json`` payload, or a single-command slice of it."""
    subs = _subparsers(parser)
    if target is not None and target not in subs:
        raise KeyError(target)
    names = [target] if target else list(subs)

    globals_ = [
        _describe_action(a)
        for a in parser._actions
        if _visible(a) and a.option_strings and not isinstance(a, argparse._SubParsersAction)
    ]

    return {
        "name": "scopus",
        "version": get_version(),
        "source": SOURCE,
        "formats": list(FORMATS),
        "exit_codes": dict(EXIT_CODES),
        "global_options": globals_,
        "commands": [describe_command(n, subs[n]) for n in names],
    }


def manifest_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Tabular projection of a manifest — what ``describe`` prints for a human."""
    return [
        {
            "name": c["name"],
            "summary": c["summary"],
            "supports_all": c["supports_all"],
        }
        for c in manifest["commands"]
    ]
