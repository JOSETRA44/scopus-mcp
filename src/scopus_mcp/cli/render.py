"""Unified output layer: one set of rows, five renderings.

Contract (ARSENAL-SPEC §1): **stdout carries data, stderr carries notes.**
A consumer running ``scopus search ... -f jsonl | jq`` must never see a banner,
a progress counter or an institutional-access note on stdout.
"""

from __future__ import annotations

import csv
import io
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

FORMATS = ("table", "json", "jsonl", "csv", "md")
SOURCE = "scopus"

# Exit codes — ARSENAL-SPEC §2.
EXIT_OK = 0
EXIT_API = 1
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3
EXIT_AUTH = 4
EXIT_RATE_LIMIT = 5
EXIT_NETWORK = 6

EXIT_CODES: dict[str, str] = {
    "0": "success (including an empty result set)",
    "1": "API returned an error / unexpected response",
    "2": "usage error (bad flag, bad argument, unknown format)",
    "3": "resource not found",
    "4": "auth or configuration error (missing/invalid API key)",
    "5": "rate limited or quota exhausted",
    "6": "network failure or timeout",
}

ERROR_CODES = ("usage", "not_found", "auth", "rate_limit", "network", "api", "internal")


def utcnow() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def force_utf8(streams: tuple[TextIO, ...] | None = None) -> None:
    """Force UTF-8 on the console streams (ARSENAL-SPEC §9).

    Windows consoles default to cp1252, which cannot encode the accented text
    Scopus returns (``Perú``, ``Côte d'Ivoire``) — without this, printing a
    perfectly correct result dies with UnicodeEncodeError. A no-op on POSIX.
    """
    for stream in streams if streams is not None else (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


# ── Envelopes ───────────────────────────────────────────────────────────────

def build_envelope(
    command: str,
    rows: list[dict],
    data: Any = None,
    meta: dict[str, Any] | None = None,
    cached: bool = False,
) -> dict[str, Any]:
    """The success envelope every ``--format json`` response is wrapped in."""
    return {
        "ok": True,
        "command": command,
        "source": SOURCE,
        "fetched_at": utcnow(),
        "cached": cached,
        "count": len(rows),
        "meta": {k: v for k, v in (meta or {}).items() if v is not None},
        "data": data if data is not None else {},
        "rows": rows,
    }


def build_error(command: str, code: str, message: str, hint: str) -> dict[str, Any]:
    """The failure envelope. Every error carries a hint: what to do next."""
    return {
        "ok": False,
        "command": command,
        "source": SOURCE,
        "fetched_at": utcnow(),
        "error": {"code": code, "message": message, "hint": hint},
    }


# ── Colour ──────────────────────────────────────────────────────────────────

class Style:
    """ANSI escapes, or empty strings when colour is off."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.reset = "\033[0m" if enabled else ""
        self.bold = "\033[1m" if enabled else ""
        self.dim = "\033[2m" if enabled else ""
        self.cyan = "\033[36m" if enabled else ""
        self.red = "\033[31m" if enabled else ""


def color_enabled(no_color: bool, stream: TextIO) -> bool:
    if no_color or os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


# ── Row rendering ───────────────────────────────────────────────────────────

def columns_of(rows: list[dict]) -> list[str]:
    """Union of keys, first-seen order — survives ragged rows."""
    cols: list[str] = []
    for row in rows:
        for key in row:
            if key not in cols:
                cols.append(key)
    return cols


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:,.4g}"
    return str(value)


def _truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    # Plain ASCII ellipsis — Windows consoles default to cp1252 and mangle "…".
    return text[: max(0, width - 3)].rstrip() + "..."


def render_table(rows: list[dict], style: Style, title: str = "") -> str:
    if not rows:
        return f"{style.dim}(no rows){style.reset}\n"
    cols = columns_of(rows)
    cells = [[_cell(row.get(c)) for c in cols] for row in rows]

    term = shutil.get_terminal_size(fallback=(120, 24)).columns
    widths = [max(len(c), *(len(r[i]) for r in cells)) for i, c in enumerate(cols)]
    # Give overflow back to the widest column rather than wrapping everything.
    budget = term - 2 * (len(cols) - 1) - 1
    if sum(widths) > budget:
        widest = widths.index(max(widths))
        widths[widest] = max(12, widths[widest] - (sum(widths) - budget))

    out = io.StringIO()
    if title:
        out.write(f"{style.bold}{title}{style.reset}\n")
    header = "  ".join(_truncate(c, w).ljust(w) for c, w in zip(cols, widths))
    out.write(f"{style.bold}{style.cyan}{header}{style.reset}\n")
    out.write(f"{style.dim}{'-' * min(term, len(header))}{style.reset}\n")
    for row in cells:
        out.write("  ".join(_truncate(v, w).ljust(w) for v, w in zip(row, widths)) + "\n")
    return out.getvalue()


def render_md(rows: list[dict]) -> str:
    if not rows:
        return "_(no rows)_\n"
    cols = columns_of(rows)
    out = io.StringIO()
    out.write("| " + " | ".join(cols) + " |\n")
    out.write("| " + " | ".join("---" for _ in cols) + " |\n")
    for row in rows:
        out.write(
            "| " + " | ".join(_cell(row.get(c)).replace("|", "\\|") for c in cols) + " |\n"
        )
    return out.getvalue()


def render_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=columns_of(rows), extrasaction="ignore")
    writer.writeheader()
    writer.writerows({k: _cell(v) for k, v in row.items()} for row in rows)
    return buf.getvalue()


def render_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in rows)


def to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n"


# ── The emitter ─────────────────────────────────────────────────────────────

class Emitter:
    """Owns the two streams and the format choice for one CLI invocation."""

    def __init__(
        self,
        fmt: str,
        output: Path | None = None,
        quiet: bool = False,
        no_color: bool = False,
    ) -> None:
        self.fmt = fmt
        self.output = output
        self.quiet = quiet
        self._fh: TextIO | None = None
        self._fields: list[str] = []
        self._writer: csv.DictWriter | None = None
        # Colour is decided against the *final* destination: a file never
        # gets escape codes even when the terminal would have.
        self.style = Style(color_enabled(no_color, sys.stdout) and output is None)

    def __enter__(self) -> "Emitter":
        if self.output is not None:
            self.output.parent.mkdir(parents=True, exist_ok=True)
            self._fh = self.output.open("w", encoding="utf-8", newline="")
        return self

    def __exit__(self, *exc: Any) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None
            if not self.quiet:
                self.note(f"Wrote {self.output}")

    @property
    def stream(self) -> TextIO:
        return self._fh if self._fh is not None else sys.stdout

    def note(self, text: str) -> None:
        """Progress, warnings and access notes — stderr only, never stdout."""
        if not self.quiet:
            print(text, file=sys.stderr)

    def warn(self, text: str) -> None:
        """Errors go to stderr even under --quiet."""
        print(f"{self.style.red}{text}{self.style.reset}", file=sys.stderr)

    def write(self, text: str) -> None:
        self.stream.write(text)

    # -- whole-result output ------------------------------------------------

    def emit(
        self,
        command: str,
        rows: list[dict],
        data: Any = None,
        meta: dict[str, Any] | None = None,
        cached: bool = False,
        title: str = "",
    ) -> None:
        if self.fmt == "json":
            self.write(to_json(build_envelope(command, rows, data, meta, cached)))
        elif self.fmt == "jsonl":
            self.write(render_jsonl(rows))
        elif self.fmt == "csv":
            self.write(render_csv(rows))
        elif self.fmt == "md":
            self.write(render_md(rows))
        else:
            self.write(render_table(rows, self.style, title))

    def emit_error(self, command: str, code: str, message: str, hint: str) -> None:
        """Machine formats get the envelope on stdout; humans get stderr."""
        if self.fmt in ("json", "jsonl"):
            sys.stdout.write(to_json(build_error(command, code, message, hint)))
        self.warn(f"Error [{code}]: {message}")
        if hint:
            print(f"Hint: {hint}", file=sys.stderr)

    # -- streaming output (bulk harvests) -----------------------------------

    def begin_stream(self, fields: list[str]) -> None:
        """Arm row-at-a-time output. Only jsonl and csv can truly stream."""
        self._fields = fields
        self._writer: csv.DictWriter | None = None

    def write_row(self, row: dict) -> None:
        if self.fmt == "jsonl":
            self.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        else:  # csv
            if self._writer is None:
                self._writer = csv.DictWriter(
                    self.stream, fieldnames=self._fields, extrasaction="ignore"
                )
                self._writer.writeheader()
            self._writer.writerow({k: _cell(v) for k, v in row.items()})
        self.stream.flush()
