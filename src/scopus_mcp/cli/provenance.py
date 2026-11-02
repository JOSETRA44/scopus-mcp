"""Explicit, portable search records. Credentials are never part of a record."""
import json
import os
from pathlib import Path
import tempfile

from .parser import get_version
from .render import utcnow


def write_record(args, meta: dict, retrieved_at: str | None, count: int) -> None:
    if not getattr(args, "record", None):
        return
    path = Path(args.record)
    if getattr(args, "output", None) and path.resolve() == Path(args.output).resolve():
        raise ValueError("--record and --output must refer to different files.")
    parameters = {key: getattr(args, key) for key in (
        "query", "identifier", "identifier_type", "scopus_id", "doi", "author_id",
        "count", "start", "view", "fetch_all", "max_rows", "start_year", "end_year",
    ) if hasattr(args, key)}
    record = {"schema_version": 1, "source": "scopus", "software_version": get_version(),
              "command": args.command, "parameters": parameters,
              "retrieved_at": retrieved_at, "recorded_at": utcnow(), "count": count, "meta": meta}
    descriptor, name = tempfile.mkstemp(prefix=".scopus-record-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
