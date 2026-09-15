import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from .cache import CacheBackend, MemoryCache, cache_key
from .config import ScopusSettings
from .exceptions import (
    ScopusAPIError,
    ScopusAuthError,
    ScopusNetworkError,
    ScopusNotFoundError,
    ScopusRateLimitError,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.elsevier.com"


@dataclass
class _RateLimitState:
    limit: int = 0
    remaining: int = 9999
    reset_at: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        """Shape reported under the JSON envelope's ``meta.rate_limit``."""
        return {
            "limit": self.limit or None,
            "remaining": self.remaining if self.remaining != 9999 else None,
            "reset_at": self.reset_at.isoformat() if self.reset_at else None,
        }


class ScopusClient:
    """Async Scopus API client with caching, rate limiting, and retry logic.

    The cache backend is injected: the MCP server keeps the default in-memory
    one, while the CLI hands in a disk backend so results survive the process.
    """

    def __init__(
        self,
        settings: ScopusSettings,
        cache: CacheBackend | None = None,
        refresh: bool = False,
    ) -> None:
        self._settings = settings
        self._rate_state = _RateLimitState()
        self._cache: CacheBackend = cache if cache is not None else MemoryCache()
        self._refresh = refresh
        self._http: httpx.AsyncClient | None = None
        # Per-process counters so the CLI can report `cached` in its envelope.
        self.hits = 0
        self.misses = 0

    async def __aenter__(self) -> "ScopusClient":
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=self._build_headers(),
            timeout=httpx.Timeout(30.0),
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    @property
    def all_cached(self) -> bool:
        """True when every request this process made was served from cache."""
        return self.hits > 0 and self.misses == 0

    @property
    def rate_limit(self) -> dict[str, Any]:
        return self._rate_state.as_dict()

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "X-ELS-APIKey": self._settings.api_key,
            "Accept": "application/json",
        }
        if self._settings.inst_token:
            headers["X-ELS-Insttoken"] = self._settings.inst_token
        return headers

    @staticmethod
    def _cache_key(path: str, params: dict[str, Any] | None) -> str:
        # Secrets live in headers, so they never enter the key material.
        return cache_key(BASE_URL, "GET", path, params)

    def _redact(self, text: str) -> str:
        """Strip credentials out of an upstream error body.

        Elsevier echoes the offending key back in some error payloads
        ("APIKey <key> with IP address ... is unauthorized"), and that body is
        quoted into the error message an agent parses out of the JSON envelope
        and writes to a log. Redact before it ever leaves the client.
        """
        for secret in (self._settings.api_key, self._settings.inst_token):
            if secret:
                text = text.replace(secret, "***")
        return text

    def _update_rate_state(self, response: httpx.Response) -> None:
        try:
            limit = response.headers.get("X-RateLimit-Limit")
            remaining = response.headers.get("X-RateLimit-Remaining")
            reset = response.headers.get("X-RateLimit-Reset")
            if limit:
                self._rate_state.limit = int(limit)
            if remaining:
                self._rate_state.remaining = int(remaining)
            if reset:
                self._rate_state.reset_at = datetime.fromtimestamp(
                    int(reset), tz=timezone.utc
                )
        except (ValueError, TypeError):
            pass

    async def _wait_for_rate_limit(self) -> None:
        if self._rate_state.remaining <= 0 and self._rate_state.reset_at:
            now = datetime.now(tz=self._rate_state.reset_at.tzinfo)
            wait = (self._rate_state.reset_at - now).total_seconds()
            if wait > 0:
                logger.warning("Rate limit reached; sleeping %.1fs until reset.", wait + 1)
                await asyncio.sleep(wait + 1)

    async def request(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make an authenticated GET request to the Scopus API.

        Handles caching, rate limiting, and retries on 429.
        """
        assert self._http is not None, "ScopusClient must be used as async context manager"

        key = self._cache_key(path, params)
        if not self._refresh:
            cached = self._cache.get(key)
            if cached is not None:
                logger.debug("Cache hit: %s", path)
                self.hits += 1
                return cached
        self.misses += 1

        await self._wait_for_rate_limit()

        last_error: Exception | None = None
        for attempt in range(self._settings.max_retries + 1):
            try:
                response = await self._http.get(path, params=params)
            except httpx.TimeoutException as exc:
                raise ScopusNetworkError(f"Request timed out after 30s: {path}") from exc
            except httpx.TransportError as exc:
                raise ScopusNetworkError(f"Could not connect to Scopus API: {exc}") from exc

            self._update_rate_state(response)

            if response.status_code == 200:
                data: dict[str, Any] = response.json()
                self._cache.set(key, data, self._settings.cache_ttl, status=200)
                return data

            if response.status_code == 429:
                if attempt == self._settings.max_retries:
                    raise ScopusRateLimitError(
                        "Scopus rate limit exceeded after all retries. "
                        "Check your API quota at https://dev.elsevier.com/.",
                        status_code=429,
                    )
                retry_after = int(response.headers.get("Retry-After", 2 ** (attempt + 1)))
                logger.warning("Rate limited (429); retrying in %ds (attempt %d).", retry_after, attempt + 1)
                await asyncio.sleep(retry_after)
                last_error = ScopusRateLimitError("Rate limited", status_code=429)
                continue

            if response.status_code in (401, 403):
                # Never cached — an auth failure must not poison later runs.
                raise ScopusAuthError(
                    f"Scopus authentication failed ({response.status_code}). "
                    "Check your SCOPUS_API_KEY and SCOPUS_INST_TOKEN.",
                    status_code=response.status_code,
                )

            if response.status_code == 404:
                raise ScopusNotFoundError(
                    f"Resource not found in Scopus: {path}",
                    status_code=404,
                )

            raise ScopusAPIError(
                f"Scopus API error {response.status_code}: "
                f"{self._redact(response.text)[:200]}",
                status_code=response.status_code,
            )

        raise last_error or ScopusAPIError("Request failed after retries")
