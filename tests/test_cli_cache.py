"""Persistent cache behaviour and — above all — secret hygiene.

ARSENAL-SPEC §3 and §6.4. This repo ships a *working* Scopus key in ``.env``,
so the leak assertions here are the ones that matter: the key must never reach
the cache key material, a cache file, or any rendered error. Every test drives
a fake key (``test-key-not-real``) through the real code path; nothing ever
reads the real one.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import httpx
import pytest

from scopus_mcp import cache as cache_module
from scopus_mcp.cache import (
    DiskCache,
    MemoryCache,
    NullCache,
    build_cache,
    cache_key,
    default_cache_dir,
)
from scopus_mcp.client import BASE_URL

from .conftest import FAKE_API_KEY, FAKE_INST_TOKEN, ok_response, paper_entry, search_payload

SEARCH_PATH = "/content/search/scopus"


def _one_paper(_request: httpx.Request) -> httpx.Response:
    return ok_response(search_payload([paper_entry(1)], total=1))


def _cache_files(cache_dir: Path) -> list[Path]:
    return sorted(cache_dir.glob("*.json")) if cache_dir.exists() else []


# ── key material ────────────────────────────────────────────────────────────

class TestCacheKey:
    def test_key_is_a_sha256_hex_digest(self) -> None:
        key = cache_key(BASE_URL, "GET", SEARCH_PATH, {"query": "x"})
        assert re.fullmatch(r"[0-9a-f]{64}", key)

    def test_key_is_stable_across_parameter_ordering(self) -> None:
        a = cache_key(BASE_URL, "GET", SEARCH_PATH, {"query": "x", "count": 5})
        b = cache_key(BASE_URL, "GET", SEARCH_PATH, {"count": 5, "query": "x"})
        assert a == b

    def test_key_changes_when_a_parameter_changes(self) -> None:
        a = cache_key(BASE_URL, "GET", SEARCH_PATH, {"query": "x"})
        b = cache_key(BASE_URL, "GET", SEARCH_PATH, {"query": "y"})
        assert a != b

    def test_key_changes_when_the_path_changes(self) -> None:
        assert cache_key(BASE_URL, "GET", "/a") != cache_key(BASE_URL, "GET", "/b")

    def test_none_valued_parameters_are_dropped_from_the_key(self) -> None:
        assert cache_key(BASE_URL, "GET", SEARCH_PATH, {"query": "x", "view": None}) == (
            cache_key(BASE_URL, "GET", SEARCH_PATH, {"query": "x"})
        )


# ── backends ────────────────────────────────────────────────────────────────

class TestBackends:
    def test_build_cache_returns_the_named_backend(self, tmp_path: Path) -> None:
        assert isinstance(build_cache("disk", tmp_path), DiskCache)
        assert isinstance(build_cache("none"), NullCache)
        assert isinstance(build_cache("memory"), MemoryCache)

    def test_disk_cache_round_trips_a_body(self, tmp_path: Path) -> None:
        cache = DiskCache(tmp_path)
        cache.set("k" * 8, {"hello": "world"}, ttl=60)
        assert cache.get("k" * 8) == {"hello": "world"}

    def test_disk_cache_miss_returns_none(self, tmp_path: Path) -> None:
        assert DiskCache(tmp_path).get("nothing-here") is None

    def test_disk_cache_entry_expires_once_its_ttl_has_passed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cache = DiskCache(tmp_path)
        cache.set("key", {"v": 1}, ttl=60)
        later = time.time() + 3600
        monkeypatch.setattr(cache_module.time, "time", lambda: later)
        assert cache.get("key") is None

    def test_an_expired_entry_is_deleted_so_cache_stats_stay_honest(
        self, tmp_path: Path
    ) -> None:
        cache = DiskCache(tmp_path)
        cache.set("key", {"v": 1}, ttl=60)
        path = tmp_path / "key.json"
        entry = json.loads(path.read_text(encoding="utf-8"))
        entry["expires"] = 0  # pretend it aged out
        path.write_text(json.dumps(entry), encoding="utf-8")
        assert cache.get("key") is None
        assert not path.exists()

    def test_a_zero_ttl_writes_nothing(self, tmp_path: Path) -> None:
        DiskCache(tmp_path).set("key", {"v": 1}, ttl=0)
        assert _cache_files(tmp_path) == []

    def test_only_2xx_responses_are_written(self, tmp_path: Path) -> None:
        """An auth failure must never be cached — it would poison later runs."""
        cache = DiskCache(tmp_path)
        for status in (401, 403, 404, 429, 500):
            cache.set(f"key{status}", {"v": status}, ttl=60, status=status)
        assert _cache_files(tmp_path) == []

    def test_entry_records_fetched_at_expires_at_and_status(self, tmp_path: Path) -> None:
        DiskCache(tmp_path).set("key", {"v": 1}, ttl=60)
        entry = json.loads((tmp_path / "key.json").read_text(encoding="utf-8"))
        assert entry["status"] == 200
        assert entry["fetched_at"].endswith("Z") and entry["expires_at"].endswith("Z")
        assert entry["body"] == {"v": 1}

    def test_null_cache_reads_nothing_and_writes_nothing(self, tmp_path: Path) -> None:
        cache = NullCache()
        cache.set("key", {"v": 1}, ttl=60)
        assert cache.get("key") is None
        assert _cache_files(tmp_path) == []

    def test_disk_cache_survives_a_corrupt_entry(self, tmp_path: Path) -> None:
        (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
        assert DiskCache(tmp_path).get("bad") is None
        assert DiskCache(tmp_path).stats()["entries"] == 0

    def test_clear_removes_every_entry_and_reports_the_count(self, tmp_path: Path) -> None:
        cache = DiskCache(tmp_path)
        for i in range(3):
            cache.set(f"key{i}", {"v": i}, ttl=60)
        assert cache.clear() == 3
        assert _cache_files(tmp_path) == []


# ── end to end through the CLI ──────────────────────────────────────────────

class TestCacheThroughTheCli:
    def test_a_cold_run_calls_the_api_and_writes_one_entry(
        self, cli, fake_scopus, cache_dir: Path, capsys
    ) -> None:
        api = fake_scopus(_one_paper)
        assert cli("search", "TITLE(x)", "-f", "json") == 0
        envelope = json.loads(capsys.readouterr().out)
        assert api.call_count == 1
        assert envelope["cached"] is False
        assert len(_cache_files(cache_dir)) == 1

    def test_a_repeat_run_is_served_from_disk_without_touching_the_api(
        self, cli, fake_scopus, capsys
    ) -> None:
        api = fake_scopus(_one_paper)
        cli("search", "TITLE(x)", "-f", "json")
        capsys.readouterr()
        assert cli("search", "TITLE(x)", "-f", "json") == 0
        envelope = json.loads(capsys.readouterr().out)
        assert api.call_count == 1, "second run must not hit the network"
        assert envelope["cached"] is True
        assert envelope["count"] == 1, "the cached answer carries the same rows"

    def test_a_different_query_is_a_different_entry(
        self, cli, fake_scopus, cache_dir: Path
    ) -> None:
        api = fake_scopus(_one_paper)
        cli("search", "TITLE(x)", "-f", "json")
        cli("search", "TITLE(y)", "-f", "json")
        assert api.call_count == 2
        assert len(_cache_files(cache_dir)) == 2

    def test_an_expired_entry_is_refetched(
        self, cli, fake_scopus, cache_dir: Path, capsys
    ) -> None:
        api = fake_scopus(_one_paper)
        cli("search", "TITLE(x)", "-f", "json")
        # Age the entry out by rewriting its absolute expiry, rather than by
        # sleeping or by patching the clock out from under asyncio.
        entry_path = _cache_files(cache_dir)[0]
        entry = json.loads(entry_path.read_text(encoding="utf-8"))
        entry["expires"] = 0
        entry_path.write_text(json.dumps(entry), encoding="utf-8")
        capsys.readouterr()

        assert cli("search", "TITLE(x)", "-f", "json") == 0
        assert api.call_count == 2
        assert json.loads(capsys.readouterr().out)["cached"] is False

    def test_refresh_ignores_the_cached_answer_and_rewrites_it(
        self, cli, fake_scopus, cache_dir: Path, capsys
    ) -> None:
        api = fake_scopus(_one_paper)
        cli("search", "TITLE(x)", "-f", "json")
        capsys.readouterr()

        assert cli("search", "TITLE(x)", "--refresh", "-f", "json") == 0
        envelope = json.loads(capsys.readouterr().out)
        assert api.call_count == 2, "--refresh must refetch"
        assert envelope["cached"] is False
        assert len(_cache_files(cache_dir)) == 1, "--refresh rewrites the same entry"

    def test_no_cache_neither_reads_nor_writes(
        self, cli, fake_scopus, cache_dir: Path
    ) -> None:
        api = fake_scopus(_one_paper)
        assert cli("search", "TITLE(x)", "--no-cache", "-f", "json") == 0
        assert _cache_files(cache_dir) == [], "--no-cache must not write"

        assert cli("search", "TITLE(x)", "--no-cache", "-f", "json") == 0
        assert api.call_count == 2, "--no-cache must not read"

    def test_no_cache_cannot_be_served_by_an_entry_a_previous_run_wrote(
        self, cli, fake_scopus
    ) -> None:
        api = fake_scopus(_one_paper)
        cli("search", "TITLE(x)", "-f", "json")
        cli("search", "TITLE(x)", "--no-cache", "-f", "json")
        assert api.call_count == 2

    def test_a_failed_request_leaves_no_cache_entry_behind(
        self, cli, fake_scopus, cache_dir: Path
    ) -> None:
        fake_scopus(lambda r: httpx.Response(401, text="denied"))
        assert cli("search", "TITLE(x)", "-f", "json") == 4
        assert _cache_files(cache_dir) == []


class TestCacheSubcommand:
    def test_cache_path_reports_the_platform_cache_directory(
        self, cli, cache_dir: Path, capsys
    ) -> None:
        assert cli("cache", "path", "-f", "json") == 0
        envelope = json.loads(capsys.readouterr().out)
        assert envelope["data"]["path"] == str(cache_dir) == str(default_cache_dir())

    def test_cache_stats_counts_live_entries(self, cli, fake_scopus, capsys) -> None:
        fake_scopus(_one_paper)
        cli("search", "TITLE(x)", "-f", "json")
        capsys.readouterr()
        assert cli("cache", "stats", "-f", "json") == 0
        data = json.loads(capsys.readouterr().out)["data"]
        assert data["entries"] == 1 and data["live"] == 1 and data["size_bytes"] > 0

    def test_cache_clear_empties_the_directory(
        self, cli, fake_scopus, cache_dir: Path, capsys
    ) -> None:
        fake_scopus(_one_paper)
        cli("search", "TITLE(x)", "-f", "json")
        capsys.readouterr()
        assert cli("cache", "clear", "-f", "json") == 0
        assert json.loads(capsys.readouterr().out)["data"]["removed"] == 1
        assert _cache_files(cache_dir) == []

    def test_the_cache_subcommand_needs_no_api_key(
        self, monkeypatch: pytest.MonkeyPatch, cli
    ) -> None:
        """`cache path` answers from local state, so it must work even when the
        configuration would fail — an agent uses it to diagnose that failure."""
        from .conftest import main_module

        def explode() -> None:
            raise AssertionError("cache must not resolve settings")

        monkeypatch.setattr(main_module, "get_settings", explode)
        assert cli("cache", "path", "-f", "json") == 0


# ── secret hygiene ──────────────────────────────────────────────────────────

class TestTheApiKeyNeverLeaks:
    def test_the_key_travels_in_a_header_not_in_the_query_string(
        self, cli, fake_scopus
    ) -> None:
        """Baseline for every leak test below: this is *how* the key is threaded
        through client.py, and the reason it can be kept out of the cache key."""
        api = fake_scopus(_one_paper)
        cli("search", "TITLE(x)", "-f", "json")
        request = api.requests[0]
        assert request.headers["X-ELS-APIKey"] == FAKE_API_KEY
        assert request.headers["X-ELS-Insttoken"] == FAKE_INST_TOKEN
        assert FAKE_API_KEY not in str(request.url)
        assert FAKE_INST_TOKEN not in str(request.url)

    def test_two_different_api_keys_have_isolated_cache_entries(
        self, cli, fake_scopus, settings, cache_dir: Path
    ) -> None:
        """Changing credentials cannot reuse data from another entitlement."""
        api = fake_scopus(_one_paper)
        cli("search", "TITLE(x)", "-f", "json")
        settings.api_key = "a-completely-different-key"
        cli("search", "TITLE(x)", "-f", "json")
        assert api.call_count == 2
        assert len(_cache_files(cache_dir)) == 2

    def test_no_cache_file_name_or_body_contains_the_key(
        self, cli, fake_scopus, cache_dir: Path
    ) -> None:
        fake_scopus(_one_paper)
        cli("search", "TITLE(x)", "-f", "json")
        cli("search-authors", "AUTHLASTNAME(Smith)", "-f", "json")
        files = _cache_files(cache_dir)
        assert files, "expected the runs above to populate the cache"
        for path in files:
            assert re.fullmatch(r"[0-9a-f]{64}", path.stem), "file name is the digest"
            blob = path.read_text(encoding="utf-8")
            assert FAKE_API_KEY not in blob
            assert FAKE_INST_TOKEN not in blob

    def test_nothing_under_the_cache_dir_contains_the_key(
        self, cli, fake_scopus, cache_dir: Path
    ) -> None:
        # Belt and braces: scan every byte written anywhere under the cache
        # root, not just the *.json entries we know about.
        fake_scopus(_one_paper)
        cli("search", "TITLE(x)", "-f", "json")
        needle = FAKE_API_KEY.encode()
        for path in cache_dir.rglob("*"):
            if path.is_file():
                assert needle not in path.read_bytes()

    @pytest.mark.parametrize("status", [401, 403, 429, 500])
    def test_an_error_envelope_never_echoes_the_key(
        self, cli, fake_scopus, capsys, status: int
    ) -> None:
        # The upstream body deliberately quotes the key back at us — a naive
        # `response.text[:200]` in an error message would carry it straight
        # into the envelope an agent logs.
        fake_scopus(
            lambda r: httpx.Response(status, text=f"rejected key {FAKE_API_KEY}")
        )
        cli("search", "TITLE(x)", "-f", "json")
        captured = capsys.readouterr()
        assert FAKE_API_KEY not in captured.err
        assert FAKE_INST_TOKEN not in captured.err
        envelope = json.loads(captured.out)
        assert FAKE_API_KEY not in json.dumps(envelope)

    def test_the_check_command_only_ever_prints_a_masked_key(
        self, cli, fake_scopus, capsys
    ) -> None:
        fake_scopus(_one_paper)
        cli("check", "-f", "json")
        out = capsys.readouterr().out
        assert FAKE_API_KEY not in out
        assert "..." in json.loads(out)["data"]["api_key"]
