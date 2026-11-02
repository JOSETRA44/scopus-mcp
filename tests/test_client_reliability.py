"""Hermetic checks for quota isolation, response integrity, and provenance."""
import json
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import AsyncMock

import httpx
import pytest

from scopus_mcp.cache import DiskCache, MemoryCache
from scopus_mcp.client import BASE_URL, ScopusClient
from scopus_mcp.config import ScopusSettings
from scopus_mcp.exceptions import ScopusAPIError, ScopusRateLimitError


def make_client(handler, cache=None, retries=2):
    settings = ScopusSettings(_env_file=None, api_key="fake", inst_token="fake", max_retries=retries)
    client = ScopusClient(settings, cache=cache)
    client._http = httpx.AsyncClient(base_url=BASE_URL, transport=httpx.MockTransport(handler))
    return client


async def test_exhausted_search_does_not_block_author(monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr("scopus_mcp.client.asyncio.sleep", sleep)
    client = make_client(lambda request: httpx.Response(200, json={"ok": True}))
    reset = int((datetime.now(timezone.utc) + timedelta(days=2)).timestamp())
    client._update_rate_state(httpx.Response(200, headers={
        "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset),
    }), "content/search/scopus")
    try:
        assert await client.request("/content/author/author_id/123") == {"ok": True}
        with pytest.raises(ScopusRateLimitError, match="Quota exhausted"):
            await client.request("/content/search/scopus")
        sleep.assert_not_awaited()
    finally:
        await client.__aexit__()


@pytest.mark.parametrize("header", ["86400", format_datetime(datetime.now(timezone.utc) + timedelta(days=2))])
async def test_large_retry_after_fails_fast(header, monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr("scopus_mcp.client.asyncio.sleep", sleep)
    client = make_client(lambda request: httpx.Response(429, headers={"Retry-After": header}))
    try:
        with pytest.raises(ScopusRateLimitError, match="wait budget"):
            await client.request("/content/search/scopus")
        sleep.assert_not_awaited()
    finally:
        await client.__aexit__()


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
async def test_transient_failure_retries_and_recovers(status, monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr("scopus_mcp.client.asyncio.sleep", sleep)
    responses = iter([httpx.Response(status, headers={"Retry-After": "invalid"}), httpx.Response(200, json={"ok": True})])
    client = make_client(lambda request: next(responses))
    try:
        assert await client.request("/content/search/scopus") == {"ok": True}
        assert 2 <= sleep.call_args.args[0] <= 2.5
    finally:
        await client.__aexit__()


@pytest.mark.parametrize("payload", [b"not-json", b"[]", b"null", b'"text"'])
async def test_invalid_success_body_is_not_cached(payload):
    cache = MemoryCache()
    client = make_client(lambda request: httpx.Response(200, content=payload), cache)
    try:
        with pytest.raises(ScopusAPIError):
            await client.request("/content/search/scopus")
        assert len(cache._store) == 0
    finally:
        await client.__aexit__()


async def test_cached_retrieval_time_survives_next_process(tmp_path):
    cache = DiskCache(tmp_path)
    client = make_client(lambda request: httpx.Response(200, json={"ok": True}), cache)
    try:
        await client.request("/content/search/scopus")
    finally:
        await client.__aexit__()
    path = next(tmp_path.glob("*.json"))
    entry = json.loads(path.read_text())
    entry["fetched_at"] = "2020-01-01T00:00:00Z"
    path.write_text(json.dumps(entry))
    def no_network(request):
        raise AssertionError("Cache hit should not access network")
    second = make_client(no_network, cache)
    try:
        await second.request("/content/search/scopus")
        assert second.retrieved_at == "2020-01-01T00:00:00Z"
        assert second.all_cached
    finally:
        await second.__aexit__()


def test_memory_cache_is_bounded_and_keeps_recently_used():
    cache = MemoryCache(max_entries=2)
    cache.set("first", {"v": 1}, 60)
    cache.set("second", {"v": 2}, 60)
    assert cache.get("first") == {"v": 1}
    cache.set("third", {"v": 3}, 60)
    assert cache.get("second") is None
    assert len(cache._store) == 2


@pytest.mark.parametrize("content", ["[]", '{"expires": "oops"}', "null"])
def test_disk_cache_ignores_structurally_invalid_entries(tmp_path, content):
    (tmp_path / "bad.json").write_text(content)
    cache = DiskCache(tmp_path)
    assert cache.get("bad") is None
    assert cache.stats()["entries"] == 0


def test_atomic_cache_replace_failure_preserves_previous_entry(tmp_path, monkeypatch):
    cache = DiskCache(tmp_path)
    cache.set("key", {"v": 1}, 60)
    def fail(*args):
        raise OSError("simulated replacement failure")
    monkeypatch.setattr("scopus_mcp.cache.os.replace", fail)
    cache.set("key", {"v": 2}, 60)
    assert cache.get("key") == {"v": 1}
    assert list(tmp_path.glob("*.tmp")) == []


async def test_zero_ttl_bypasses_existing_cache():
    cache = MemoryCache()
    client = make_client(lambda request: httpx.Response(200, json={"value": "fresh"}), cache)
    cache.set(client._cache_key("/content/search/scopus", None), {"value": "old"}, 60)
    client._settings.cache_ttl = 0
    try:
        assert await client.request("/content/search/scopus") == {"value": "fresh"}
        assert client.hits == 0
        assert cache.get(client._cache_key("/content/search/scopus", None)) == {"value": "old"}
    finally:
        await client.__aexit__()
