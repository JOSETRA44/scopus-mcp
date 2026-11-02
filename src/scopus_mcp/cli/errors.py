"""Exception → exit-code mapping (ARSENAL-SPEC §2).

The tools layer already raises precise exception types, so the CLI never has to
guess from a message string. Each mapping also carries the ``hint`` that goes
into the error envelope: what the caller should do next.
"""

from __future__ import annotations

from ..exceptions import (
    ScopusAPIError,
    ScopusAuthError,
    ScopusConfigError,
    ScopusNetworkError,
    ScopusNotFoundError,
    ScopusRateLimitError,
)
from ..services.author import AUTHOR_INST_NOTE
from ..services.citations import CITATIONS_INST_NOTE
from ..services.search import AFFILIATION_SEARCH_INST_NOTE, AUTHOR_SEARCH_INST_NOTE
from .render import (
    EXIT_API,
    EXIT_AUTH,
    EXIT_NETWORK,
    EXIT_NOT_FOUND,
    EXIT_RATE_LIMIT,
    EXIT_USAGE,
)

# Institutional-access notes double as the `hint` of an auth error envelope.
INST_NOTES: dict[str, str] = {
    "author": AUTHOR_INST_NOTE,
    "search-authors": AUTHOR_SEARCH_INST_NOTE,
    "search-affiliations": AFFILIATION_SEARCH_INST_NOTE,
    "citation-count": CITATIONS_INST_NOTE,
    "citations": CITATIONS_INST_NOTE,
}

DEFAULT_AUTH_HINT = (
    "Run `scopus setup`, or set SCOPUS_API_KEY in your environment. "
    "Get a key at https://dev.elsevier.com/."
)


def classify(exc: BaseException, command: str = "") -> tuple[int, str, str]:
    """Return (exit_code, error_code, hint) for ``exc``.

    Order matters: the auth / not-found / rate-limit / network types all
    subclass ScopusAPIError, so they must be tested before it.
    """
    if isinstance(exc, ScopusConfigError):
        return EXIT_AUTH, "auth", DEFAULT_AUTH_HINT
    if isinstance(exc, ScopusAuthError):
        return EXIT_AUTH, "auth", INST_NOTES.get(command, DEFAULT_AUTH_HINT)
    if isinstance(exc, ScopusNotFoundError):
        return EXIT_NOT_FOUND, "not_found", (
            "Check the identifier and its --type; "
            "use `scopus search` to find the right one."
        )
    if isinstance(exc, ScopusRateLimitError):
        return EXIT_RATE_LIMIT, "rate_limit", (
            "Scopus quota or per-second rate exceeded. Wait for the reset window, "
            "or re-run without --refresh so the cache can answer."
        )
    if isinstance(exc, ScopusNetworkError):
        return EXIT_NETWORK, "network", (
            "Check connectivity to api.elsevier.com and retry."
        )
    if isinstance(exc, ScopusAPIError):
        return EXIT_API, "api", (
            "Unexpected Scopus response; re-run with --refresh to bypass the cache."
        )
    if isinstance(exc, ValueError):
        return EXIT_USAGE, "usage", (
            "Check the arguments; run `scopus describe --json` for the manifest."
        )
    return EXIT_API, "internal", (
        "Unexpected failure; re-run with LOG_LEVEL=DEBUG for detail."
    )
