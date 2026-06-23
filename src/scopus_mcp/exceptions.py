class ScopusError(Exception):
    """Base exception for all Scopus MCP errors."""


class ScopusConfigError(ScopusError):
    """Raised at startup when required configuration (e.g. API key) is missing."""


class ScopusAPIError(ScopusError):
    """Raised when the Scopus API returns an unexpected HTTP error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ScopusAuthError(ScopusAPIError):
    """Raised on 401/403 — bad API key or quota exhausted."""


class ScopusNotFoundError(ScopusAPIError):
    """Raised on 404 — the requested resource does not exist in Scopus."""


class ScopusRateLimitError(ScopusAPIError):
    """Raised on 429 after all retry attempts are exhausted."""
