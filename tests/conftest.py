"""Shared fixtures for the CLI test-suite — hermetic by construction.

Three things make every test in this suite safe to run anywhere:

* **No network.** Requests are served by an ``httpx.MockTransport`` injected
  into the client (see ``fake_scopus``).
* **No real credentials.** This repo has a working key in ``.env``; the
  ``settings`` fixture replaces ``get_settings`` with a fake so no test can
  read, assert on, or accidentally print the real one.
* **No real cache directory.** ``platformdirs.user_cache_dir`` is redirected
  at ``tmp_path`` so a test run never reads or clobbers the user's cache.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import httpx
import pytest

from importlib import import_module

from scopus_mcp import cache as cache_module
from scopus_mcp import client as client_module
from scopus_mcp.cli.main import main_cli
from scopus_mcp.cli.parser import build_parser
from scopus_mcp.config import ScopusSettings

# `scopus_mcp.cli.__init__` re-exports a function called `main`, which shadows
# the submodule of the same name on attribute access — reach for the module.
main_module = import_module("scopus_mcp.cli.main")

# Deliberately not a real key shape: if this string ever shows up in output,
# a cache file or an error message, the leak assertion should catch it.
FAKE_API_KEY = "test-key-not-real"
FAKE_INST_TOKEN = "test-inst-token-not-real"

RATE_HEADERS = {
    "X-RateLimit-Limit": "20000",
    "X-RateLimit-Remaining": "19998",
    "X-RateLimit-Reset": "1755700000",
}


# ── Payload builders ────────────────────────────────────────────────────────

def paper_entry(n: int, *, title: str | None = None, sid: int | str | None = None) -> dict:
    """One `entry` as Scopus returns it from /content/search/scopus."""
    ident = sid if sid is not None else 85000 + n
    return {
        "dc:identifier": f"SCOPUS_ID:{ident}",
        "eid": f"2-s2.0-{ident}",
        "dc:title": title or f"Paper {n}",
        "dc:creator": "Smith, J.",
        "prism:publicationName": "Nature",
        "prism:coverDate": "2024-01-01",
        "prism:doi": f"10.1000/test.{n}",
        "citedby-count": str(n),
        "openaccess": "0",
        "link": [],
    }


def search_payload(entries: list[dict], total: int | None = None, start: int = 0) -> dict:
    return {
        "search-results": {
            "opensearch:totalResults": str(len(entries) if total is None else total),
            "opensearch:itemsPerPage": str(len(entries)),
            "opensearch:startIndex": str(start),
            "entry": entries,
        }
    }


def ok_response(payload: Any, headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(200, json=payload, headers={**RATE_HEADERS, **(headers or {})})


# ── The fake upstream ───────────────────────────────────────────────────────

class FakeScopus:
    """A scripted api.elsevier.com: records every request, replies via handler."""

    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self._handler = handler
        self.requests: list[httpx.Request] = []
        self.transport = httpx.MockTransport(self._dispatch)

    def _dispatch(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._handler(request)

    @property
    def call_count(self) -> int:
        return len(self.requests)

    def params(self, index: int = -1) -> dict[str, str]:
        return dict(self.requests[index].url.params)

    def all_params(self, name: str) -> list[str]:
        return [dict(r.url.params).get(name, "") for r in self.requests]


@pytest.fixture
def settings() -> ScopusSettings:
    """Settings with a fake key. Every field is passed explicitly so that a
    stray real env var or the repo's own .env cannot leak into a test."""
    return ScopusSettings(
        SCOPUS_API_KEY=FAKE_API_KEY,
        SCOPUS_INST_TOKEN=FAKE_INST_TOKEN,
        SCOPUS_CACHE_TTL=300,
        SCOPUS_MAX_RETRIES=0,  # no retry sleeps in tests
        LOG_LEVEL="INFO",
    )


@pytest.fixture
def cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the platform cache location at tmp_path for the whole test."""
    target = tmp_path / "scopus-cache"
    monkeypatch.setattr(
        cache_module.platformdirs, "user_cache_dir", lambda *a, **k: str(target)
    )
    return target


@pytest.fixture
def fake_scopus(monkeypatch: pytest.MonkeyPatch) -> Callable[..., FakeScopus]:
    """Install a MockTransport into whatever AsyncClient ScopusClient builds.

    ScopusClient constructs its own httpx.AsyncClient inside ``__aenter__``, so
    the transport is injected by wrapping the class rather than by passing an
    argument — this keeps the production header/base_url construction under test
    instead of duplicating it here. monkeypatch restores the real class.
    """

    def install(handler: Callable[[httpx.Request], httpx.Response]) -> FakeScopus:
        api = FakeScopus(handler)
        real_cls = client_module.httpx.AsyncClient

        def factory(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
            kwargs["transport"] = api.transport
            return real_cls(*args, **kwargs)

        monkeypatch.setattr(client_module.httpx, "AsyncClient", factory)
        return api

    return install


@pytest.fixture
def cli(
    monkeypatch: pytest.MonkeyPatch, settings: ScopusSettings, cache_dir: Path
) -> Callable[..., int]:
    """Run the real CLI end to end: argv in, exit code out."""
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)

    def run(*argv: str) -> int:
        return main_cli(build_parser().parse_args(list(argv)))

    return run


@pytest.fixture
def stdout_json() -> Callable[[pytest.CaptureFixture], Any]:
    def parse(capsys: pytest.CaptureFixture) -> Any:
        return json.loads(capsys.readouterr().out)

    return parse
