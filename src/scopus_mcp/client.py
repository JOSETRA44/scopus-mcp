import asyncio
import hashlib
import logging
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import httpx

from .config import ScopusSettings
from .exceptions import (
    ScopusAPIError,
    ScopusAuthError,
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


@dataclass
class _CacheEntry:
    data: dict[str, Any]
    expires_at: datetime


class _TTLCache:
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, _CacheEntry] = {}

    def get(self, key: str) -> dict[str, Any] | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if datetime.now() >= entry.expires_at:
            del self._store[key]
            return None
        return entry.data

    def set(self, key: str, data: dict[str, Any]) -> None:
        self._store[key] = _CacheEntry(
            data=data,
            expires_at=datetime.now() + timedelta(seconds=self._ttl),
        )

    def clear_expired(self) -> None:
        now = datetime.now()
        expired = [k for k, e in self._store.items() if now >= e.expires_at]
        for k in expired:
            del self._store[k]


class ScopusClient:
    """Async Scopus API client with caching, rate limiting, and retry logic."""

    def __init__(self, settings: ScopusSettings) -> None:
        self._settings = settings
        self._rate_state = _RateLimitState()
        self._cache = _TTLCache(settings.cache_ttl)
        self._http: httpx.AsyncClient | None = None

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
        canonical = path
        if params:
            canonical += "?" + urllib.parse.urlencode(sorted(params.items()))
        return hashlib.sha256(canonical.encode()).hexdigest()

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
                self._rate_state.reset_at = datetime.fromtimestamp(int(reset))
        except (ValueError, TypeError):
            pass

    async def _wait_for_rate_limit(self) -> None:
        if self._rate_state.remaining <= 0 and self._rate_state.reset_at:
            wait = (self._rate_state.reset_at - datetime.now()).total_seconds()
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
        cached = self._cache.get(key)
        if cached is not None:
            logger.debug("Cache hit: %s", path)
            return cached

        await self._wait_for_rate_limit()

        last_error: Exception | None = None
        for attempt in range(self._settings.max_retries + 1):
            try:
                response = await self._http.get(path, params=params)
            except httpx.TimeoutException as exc:
                raise ScopusAPIError(f"Request timed out after 30s: {path}") from exc
            except httpx.ConnectError as exc:
                raise ScopusAPIError(f"Could not connect to Scopus API: {exc}") from exc

            self._update_rate_state(response)

            if response.status_code == 200:
                data: dict[str, Any] = response.json()
                self._cache.set(key, data)
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
                f"Scopus API error {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            )

        raise last_error or ScopusAPIError("Request failed after retries")
