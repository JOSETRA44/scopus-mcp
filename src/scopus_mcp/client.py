import asyncio
import hashlib
import json
import logging
import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
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
        self._rate_states: dict[str, _RateLimitState] = {}
        self.retrieved_at: str | None = None
        identity = json.dumps([settings.api_key, settings.inst_token], separators=(",", ":"))
        self._cache_namespace = hashlib.sha256(identity.encode()).hexdigest()
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

    @property
    def rate_limits(self) -> dict[str, dict[str, Any]]:
        """Observed quota headers, separated by API family."""
        return {endpoint: state.as_dict() for endpoint, state in self._rate_states.items()}

    @staticmethod
    def _endpoint(path: str) -> str:
        parts = path.strip("/").split("/")
        if parts[:2] == ["content", "search"]:
            return "/".join(parts[:3])
        if parts[:2] == ["content", "abstract"] and len(parts) > 2:
            if parts[2] in {"citations", "citation-count"}:
                return "/".join(parts[:3])
        return "/".join(parts[:2])

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "X-ELS-APIKey": self._settings.api_key,
            "Accept": "application/json",
        }
        if self._settings.inst_token:
            headers["X-ELS-Insttoken"] = self._settings.inst_token
        return headers

    def _cache_key(self, path: str, params: dict[str, Any] | None) -> str:
        request_key = cache_key(BASE_URL, "GET", path, params)
        return hashlib.sha256(f"{self._cache_namespace}:{request_key}".encode()).hexdigest()

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

    def _update_rate_state(self, response: httpx.Response, endpoint: str) -> None:
        state = self._rate_states.setdefault(endpoint, _RateLimitState())
        self._rate_state = state
        for header, attr in (("X-RateLimit-Limit", "limit"), ("X-RateLimit-Remaining", "remaining")):
            try:
                if header in response.headers:
                    setattr(state, attr, int(response.headers[header]))
            except (ValueError, TypeError):
                pass
        try:
            if "X-RateLimit-Reset" in response.headers:
                state.reset_at = datetime.fromtimestamp(int(response.headers["X-RateLimit-Reset"]), tz=timezone.utc)
        except (ValueError, TypeError, OverflowError, OSError):
            pass

    async def _wait_for_rate_limit(self, endpoint: str, budget: float) -> float:
        state = self._rate_states.get(endpoint)
        if state and state.remaining <= 0 and state.reset_at:
            now = datetime.now(tz=timezone.utc)
            wait = (state.reset_at - now).total_seconds()
            if wait > 0:
                if wait + 1 > budget:
                    raise ScopusRateLimitError(
                        f"Quota exhausted for {endpoint}; resets at {state.reset_at.isoformat()}. "
                        "Retry after the reset or request a larger quota.", status_code=429,
                    )
                await asyncio.sleep(wait + 1)
                return wait + 1
        return 0.0

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                seconds = float(value)
                if math.isfinite(seconds) and seconds >= 0:
                    return seconds
            except ValueError:
                try:
                    when = parsedate_to_datetime(value)
                    if when.tzinfo is None:
                        when = when.replace(tzinfo=timezone.utc)
                    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
                except (TypeError, ValueError, OverflowError):
                    pass
        return min(2 ** (attempt + 1), 16) + random.uniform(0, 0.5)

    async def request(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Fetch one JSON object within a bounded overall time budget."""
        max_wait = float(getattr(self._settings, "max_wait_seconds", 30))
        try:
            async with asyncio.timeout(30.0 + max_wait):
                return await self._request(path, params, max_wait)
        except TimeoutError as exc:
            raise ScopusNetworkError("Scopus request exceeded its total time budget.") from exc

    async def _request(self, path: str, params: dict[str, Any] | None, max_wait: float) -> dict[str, Any]:
        assert self._http is not None, "ScopusClient must be used as async context manager"
        self.retrieved_at = None
        endpoint = self._endpoint(path)
        key = self._cache_key(path, params)
        if not self._refresh and self._settings.cache_ttl > 0:
            get_entry = getattr(self._cache, "get_entry", None)
            entry = get_entry(key) if get_entry else None
            cached = entry.get("body") if entry else self._cache.get(key)
            if isinstance(cached, dict):
                logger.debug("Cache hit: %s", path)
                self.hits += 1
                self.retrieved_at = entry.get("fetched_at") if entry else None
                return cached
        self.misses += 1

        waited = await self._wait_for_rate_limit(endpoint, max_wait)

        last_error: Exception | None = None
        for attempt in range(self._settings.max_retries + 1):
            try:
                response = await self._http.get(path, params=params)
            except httpx.TimeoutException as exc:
                raise ScopusNetworkError(f"Request timed out after 30s: {path}") from exc
            except httpx.TransportError as exc:
                raise ScopusNetworkError(f"Could not connect to Scopus API: {self._redact(str(exc))}") from exc

            self._update_rate_state(response, endpoint)

            if response.status_code == 200:
                try:
                    data = response.json()
                except ValueError as exc:
                    raise ScopusAPIError("Scopus returned invalid JSON.", status_code=200) from exc
                if not isinstance(data, dict):
                    raise ScopusAPIError("Scopus returned an unexpected JSON structure; expected an object.", status_code=200)
                self.retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                self._cache.set(key, data, self._settings.cache_ttl, status=200)
                return data

            if response.status_code in (429, 500, 502, 503, 504):
                error_type = ScopusRateLimitError if response.status_code == 429 else ScopusAPIError
                if attempt == self._settings.max_retries:
                    raise error_type(
                        f"Scopus API returned {response.status_code} after all retries. Try again later.",
                        status_code=response.status_code,
                    )
                retry_after = self._retry_delay(response, attempt)
                if retry_after > max_wait - waited:
                    raise error_type(
                        f"Scopus API returned {response.status_code}; retry delay exceeds the wait budget. Try again later.",
                        status_code=response.status_code,
                    )
                logger.warning("Scopus returned %d; retrying in %.1fs (attempt %d).", response.status_code, retry_after, attempt + 1)
                await asyncio.sleep(retry_after)
                waited += retry_after
                last_error = error_type("Retry limit reached", status_code=response.status_code)
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
