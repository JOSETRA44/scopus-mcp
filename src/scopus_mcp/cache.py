"""Pluggable cache backends for Scopus API responses.

The MCP server is a long-lived process, so an in-memory dict is ideal there.
The CLI is a fresh short-lived process on every invocation, so an in-memory
cache would be useless to it — it gets a disk backend instead, which makes a
repeated research query instant across runs.

Both backends implement the same ``CacheBackend`` Protocol, so ``ScopusClient``
neither knows nor cares which one it was handed.

Credentials travel in headers only. The client namespaces request keys with
a credential digest so users with different entitlements never share data.
Raw credentials are never written into a cache file.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import urllib.parse
from collections import OrderedDict
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

    def __init__(self, max_entries: int = 1024) -> None:
        self.max_entries = max(1, max_entries)
        self._store: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        entry = self.get_entry(key)
        return entry["body"] if entry else None

    def get_entry(self, key: str) -> dict[str, Any] | None:
        entry = self._store.get(key)
        if entry and time.time() < entry["expires"]:
            self._store.move_to_end(key)
            return entry
        self._store.pop(key, None)
        return None

    def set(self, key: str, value: Any, ttl: int, status: int = 200) -> None:
        if ttl > 0 and 200 <= status < 300:
            now = time.time()
            self._store[key] = {"body": value, "expires": now + ttl, "fetched_at": _iso(now)}
            self._store.move_to_end(key)
            while len(self._store) > self.max_entries:
                self._store.popitem(last=False)


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
        entry = self.get_entry(key)
        return entry.get("body") if entry else None

    def get_entry(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if not isinstance(entry, dict) or not isinstance(entry.get("expires"), (int, float)):
            return None
        if time.time() >= entry["expires"]:
            # Expired — clean it up opportunistically so `cache stats` stays honest.
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return None
        return entry

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
        temp_path = None
        try:
            payload = json.dumps(entry, ensure_ascii=False)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.dir,
                                             suffix=".tmp", delete=False) as handle:
                temp_path = Path(handle.name)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self._path(key))
        except (OSError, TypeError):
            # Caching is best-effort; never let a cache write break a query.
            pass
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
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
            if not isinstance(entry, dict) or not isinstance(entry.get("expires"), (int, float)):
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
