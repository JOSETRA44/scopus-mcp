"""Tabular output, provenance envelopes, and bibliographic exports.

Contract (ARSENAL-SPEC §1): **stdout carries data, stderr carries notes.**
A consumer running ``scopus search ... -f jsonl | jq`` must never see a banner,
a progress counter or an institutional-access note on stdout.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

BIBLIOGRAPHIC_FORMATS = ("ris", "bibtex", "csl-json")
FORMATS = ("table", "json", "jsonl", "csv", "md", *BIBLIOGRAPHIC_FORMATS)
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
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    """The success envelope every ``--format json`` response is wrapped in."""
    served_at = utcnow()
    # An old/custom cache may not have retrieval metadata. Do not claim its
    # contents were fetched from Elsevier just because they were served now.
    retrieved_at = retrieved_at or (None if cached else served_at)
    return {
        "ok": True,
        "command": command,
        "source": SOURCE,
        "fetched_at": retrieved_at,
        "retrieved_at": retrieved_at,
        "served_at": served_at,
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


# Bibliographic export uses full records, not the lossy table projection.
# Unknown publication types stay generic; a source title is not proof that a
# record is a journal article. Names remain literal rather than guessing how
# an international or corporate author's name should be split.
def _single_line(value: Any) -> str:
    return " ".join(str(value).split()) if value is not None else ""


def bibliographic_records(command: str, rows: list[dict], data: Any = None) -> list[dict]:
    if command not in {"search", "abstract"}:
        raise ValueError(
            "Bibliographic formats (ris, bibtex, csl-json) support search and abstract only. "
            "Use --format json or csv for this command."
        )
    if isinstance(data, dict):
        if command == "abstract":
            return [data] if data else []
        if "papers" in data:
            return data["papers"] or []
        if "rows" in data:
            return data["rows"] or []
    return rows


def _record_id(record: dict) -> str:
    ident = record.get("scopus_id") or record.get("doi") or record.get("eid")
    if ident:
        return _single_line(ident)
    # This is a local citation key, not a claimed identifier from Scopus.
    digest = hashlib.sha256(json.dumps(record, sort_keys=True, default=str).encode()).hexdigest()[:16]
    return f"record-{digest}"


def _authors(record: dict) -> tuple[list[str], bool]:
    authors = record.get("authors")
    if isinstance(authors, list):
        names = [_single_line(a.get("name")) if isinstance(a, dict) else _single_line(a)
                 for a in authors]
        names = [name for name in names if name]
        if names:
            return names, False
    first = _single_line(record.get("first_author"))
    return ([first], True) if first else ([], False)


def _date_parts(record: dict) -> list[int]:
    raw = str(record.get("cover_date") or record.get("year") or "")
    if not re.fullmatch(r"\d{4}(?:-\d{2}){0,2}", raw):
        return []
    parts = [int(part) for part in raw.split("-")]
    try:
        datetime(parts[0], parts[1] if len(parts) > 1 else 1,
                 parts[2] if len(parts) > 2 else 1)
    except ValueError:
        return []
    return parts


def _publication_types(record: dict) -> tuple[str, str, str]:
    kind = str(record.get("document_type") or record.get("aggregation_type") or "").lower()
    return {
        "article": ("JOUR", "article", "article-journal"),
        "journal": ("JOUR", "article", "article-journal"),
        "ar": ("JOUR", "article", "article-journal"),
        "conference paper": ("CPAPER", "inproceedings", "paper-conference"),
        "cp": ("CPAPER", "inproceedings", "paper-conference"),
        "book": ("BOOK", "book", "book"),
        "book chapter": ("CHAP", "incollection", "chapter"),
    }.get(kind, ("GEN", "misc", "document"))


def _export_note(record: dict, partial_authors: bool) -> str:
    notes = []
    if partial_authors:
        notes.append("Only the first author was available in this search record; retrieve the abstract record for additional author metadata.")
    if record.get("access_note"):
        notes.append(_single_line(record["access_note"]))
    return " ".join(notes)


def render_ris(records: list[dict]) -> str:
    entries = []
    for record in records:
        fields = [("TY", _publication_types(record)[0]), ("ID", _record_id(record))]
        fields += [(tag, record.get(key)) for tag, key in (
            ("TI", "title"), ("T2", "publication"), ("DO", "doi"),
            ("UR", "scopus_url"), ("VL", "volume"), ("IS", "issue"), ("AB", "abstract"))]
        names, partial = _authors(record)
        fields += [("AU", name) for name in names]
        date = _date_parts(record)
        if date:
            fields.append(("PY", str(date[0])))
            if len(date) > 1:
                fields.append(("DA", "/".join([str(date[0]), *(f"{n:02d}" for n in date[1:])])))
        pages = str(record.get("page_range") or "")
        if pages:
            ends = re.split(r"[-–]", pages, maxsplit=1)
            fields.append(("SP", ends[0]))
            if len(ends) == 2:
                fields.append(("EP", ends[1]))
        keywords = record.get("keywords") or []
        if isinstance(keywords, list):
            fields += [("KW", keyword) for keyword in keywords]
        fields.append(("N1", _export_note(record, partial)))
        entries.append("\n".join(f"{tag}  - {_single_line(value)}" for tag, value in fields
                                 if value is not None and value != "") + "\nER  - \n")
    return "\n".join(entries)


def _bibtex_escape(value: Any) -> str:
    replacements = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}",
                    "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
                    "_": r"\_", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(replacements.get(char, char) for char in _single_line(value))


def render_bibtex(records: list[dict]) -> str:
    entries = []
    used: set[str] = set()
    for record in records:
        ident = _record_id(record)
        key = re.sub(r"[^A-Za-z0-9_:-]", "_", ident)
        base = key or "record"
        suffix = 1
        while key in used:
            suffix += 1
            key = f"{base}_{suffix}"
        used.add(key)
        kind = _publication_types(record)[1]
        container_field = "journal" if kind == "article" else "booktitle" if kind in {"inproceedings", "incollection"} else "howpublished"
        fields = {out: _bibtex_escape(record[source]) for out, source in (
            ("title", "title"), (container_field, "publication"), ("doi", "doi"),
            ("url", "scopus_url"), ("volume", "volume"), ("number", "issue"),
            ("pages", "page_range"), ("abstract", "abstract")) if record.get(source)}
        names, partial = _authors(record)
        if names:
            fields["author"] = " and ".join("{" + _bibtex_escape(name) + "}" for name in names)
        date = _date_parts(record)
        if date:
            fields["year"] = str(date[0])
        note = _export_note(record, partial)
        if note:
            fields["note"] = _bibtex_escape(note)
        entries.append(f"@{kind}{{{key},\n" + ",\n".join(
            f"  {name} = {{{value}}}" for name, value in fields.items()) + "\n}\n")
    return "\n".join(entries)


def render_csl_json(records: list[dict]) -> str:
    items = []
    used: set[str] = set()
    for record in records:
        ident = _record_id(record)
        base = ident
        suffix = 1
        while ident in used:
            suffix += 1
            ident = f"{base}_{suffix}"
        used.add(ident)
        item: dict[str, Any] = {"id": ident, "type": _publication_types(record)[2]}
        for dest, source in (("title", "title"), ("container-title", "publication"),
                             ("DOI", "doi"), ("URL", "scopus_url"), ("volume", "volume"),
                             ("issue", "issue"), ("page", "page_range"), ("abstract", "abstract"),
                             ("language", "language")):
            if record.get(source):
                item[dest] = str(record[source])
        names, partial = _authors(record)
        if names:
            item["author"] = [{"literal": name} for name in names]
        date = _date_parts(record)
        if date:
            item["issued"] = {"date-parts": [date]}
        note = _export_note(record, partial)
        if note:
            item["note"] = note
        items.append(item)
    return to_json(items)


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
        retrieved_at: str | None = None,
    ) -> None:
        if self.fmt == "json":
            self.write(to_json(build_envelope(command, rows, data, meta, cached, retrieved_at)))
        elif self.fmt == "jsonl":
            self.write(render_jsonl(rows))
        elif self.fmt == "csv":
            self.write(render_csv(rows))
        elif self.fmt == "md":
            self.write(render_md(rows))
        elif self.fmt in BIBLIOGRAPHIC_FORMATS:
            records = bibliographic_records(command, rows, data)
            render = {"ris": render_ris, "bibtex": render_bibtex, "csl-json": render_csl_json}[self.fmt]
            self.write(render(records))
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
