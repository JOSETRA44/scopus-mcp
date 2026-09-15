"""Pluggable cache backends for Scopus API responses.

The MCP server is a long-lived process, so an in-memory dict is ideal there.
The CLI is a fresh short-lived process on every invocation, so an in-memory
cache would be useless to it — it gets a disk backend instead, which makes a
repeated research query instant across runs.

Both backends implement the same ``CacheBackend`` Protocol, so ``ScopusClient``
neither knows nor cares which one it was handed.

Security note: the cache key is derived from (base_url, method, path, sorted
query params) only. The Scopus API key and institutional token travel in the
``X-ELS-APIKey`` / ``X-ELS-Insttoken`` *headers*, so they are never part of the
key material and are never written into a cache file.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import platformdirs

APP_NAME = "scopus-mcp"


def cache_key(
    base_url: str,
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
) -> str:
    """SHA-256 of the request identity. Deliberately excludes every secret."""
    canonical = f"{method.upper()} {base_url.rstrip('/')}{path}"
    if params:
        pairs = sorted((str(k), str(v)) for k, v in params.items() if v is not None)
        canonical += "?" + urllib.parse.urlencode(pairs)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def default_cache_dir() -> Path:
    """Per-user cache location chosen by the platform, not by us."""
    return Path(platformdirs.user_cache_dir(APP_NAME))


@runtime_checkable
class CacheBackend(Protocol):
    """Minimal contract every cache backend must satisfy."""

    def get(self, key: str) -> Any | None:
        """Return the cached body for ``key``, or ``None`` if missing/expired."""
        ...

    def set(self, key: str, value: Any, ttl: int, status: int = 200) -> None:
        """Store ``value`` under ``key`` for ``ttl`` seconds (no-op if ttl <= 0)."""
        ...


class MemoryCache:
    """In-process cache. Fast, ephemeral — used by the long-lived MCP server."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry and time.time() < entry["expires"]:
            return entry["body"]
        self._store.pop(key, None)
        return None

    def set(self, key: str, value: Any, ttl: int, status: int = 200) -> None:
        if ttl > 0:
            self._store[key] = {"body": value, "expires": time.time() + ttl}


class NullCache:
    """Reads nothing, writes nothing — what ``--no-cache`` installs."""

    def get(self, key: str) -> Any | None:
        return None

    def set(self, key: str, value: Any, ttl: int, status: int = 200) -> None:
        return None


class DiskCache:
    """Filesystem cache. Persists between processes — used by the CLI.

    Each entry is a small JSON file named by its key, holding the response body
    plus absolute fetch/expiry timestamps and the HTTP status. Only successful
    (2xx) responses are ever written; auth failures never are.
    """

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        self.dir = Path(cache_dir) if cache_dir is not None else default_cache_dir()
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.dir / f"{key}.json"

    def get(self, key: str) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if time.time() >= entry.get("expires", 0):
            # Expired — clean it up opportunistically so `cache stats` stays honest.
            path.unlink(missing_ok=True)
            return None
        return entry.get("body")

    def set(self, key: str, value: Any, ttl: int, status: int = 200) -> None:
        if ttl <= 0 or not (200 <= status < 300):
            return
        now = time.time()
        entry = {
            "fetched_at": _iso(now),
            "expires_at": _iso(now + ttl),
            "expires": now + ttl,
            "status": status,
            "body": value,
        }
        try:
            self._path(key).write_text(
                json.dumps(entry, ensure_ascii=False), encoding="utf-8"
            )
        except (OSError, TypeError):
            # Caching is best-effort; never let a cache write break a query.
            pass

    # ── `cache` subcommand support ──────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Entry counts and total size on disk, split live vs expired."""
        now = time.time()
        live = expired = 0
        size = 0
        for path in self.dir.glob("*.json"):
            try:
                size += path.stat().st_size
                entry = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if now >= entry.get("expires", 0):
                expired += 1
            else:
                live += 1
        return {
            "path": str(self.dir),
            "entries": live + expired,
            "live": live,
            "expired": expired,
            "size_bytes": size,
        }

    def clear(self) -> int:
        """Delete every entry; return how many files were removed."""
        removed = 0
        for path in self.dir.glob("*.json"):
            try:
                path.unlink()
                removed += 1
            except OSError:
                continue
        return removed


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_cache(backend: str, cache_dir: str | Path | None = None) -> CacheBackend:
    """Factory: return the cache backend named by ``backend``."""
    if backend == "disk":
        return DiskCache(cache_dir)
    if backend == "none":
        return NullCache()
    return MemoryCache()
