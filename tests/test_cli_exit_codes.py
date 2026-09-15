"""Exception → exit-code mapping (ARSENAL-SPEC §2, §6.3).

Two layers are checked: ``classify`` on its own (the pure mapping), and the
whole CLI driven end to end against a mock transport that returns the HTTP
status which produces each exception. Assertions are on the *code*, never on
message text, so wording changes never break the contract.
"""

from __future__ import annotations

import json
from typing import Callable

import httpx
import pytest

from scopus_mcp.cli.errors import classify
from scopus_mcp.cli.parser import build_parser
from scopus_mcp.cli.render import (
    ERROR_CODES,
    EXIT_API,
    EXIT_AUTH,
    EXIT_CODES,
    EXIT_NETWORK,
    EXIT_NOT_FOUND,
    EXIT_OK,
    EXIT_RATE_LIMIT,
    EXIT_USAGE,
)
from scopus_mcp.exceptions import (
    ScopusAPIError,
    ScopusAuthError,
    ScopusConfigError,
    ScopusNetworkError,
    ScopusNotFoundError,
    ScopusRateLimitError,
)

from .conftest import main_module, ok_response, paper_entry, search_payload


# ── the pure mapping ────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("exc", "exit_code", "error_code"),
    [
        (ScopusConfigError("no key"), EXIT_AUTH, "auth"),
        (ScopusAuthError("401", status_code=401), EXIT_AUTH, "auth"),
        (ScopusNotFoundError("404", status_code=404), EXIT_NOT_FOUND, "not_found"),
        (ScopusRateLimitError("429", status_code=429), EXIT_RATE_LIMIT, "rate_limit"),
        (ScopusNetworkError("dns"), EXIT_NETWORK, "network"),
        (ScopusAPIError("500", status_code=500), EXIT_API, "api"),
        (ValueError("bad argument"), EXIT_USAGE, "usage"),
        (RuntimeError("something else"), EXIT_API, "internal"),
    ],
    ids=[
        "config->4", "auth->4", "not_found->3", "rate_limit->5",
        "network->6", "api->1", "usage->2", "unknown->internal",
    ],
)
def test_classify_maps_each_exception_to_its_spec_exit_code(
    exc: BaseException, exit_code: int, error_code: str
) -> None:
    code, err, hint = classify(exc)
    assert (code, err) == (exit_code, error_code)
    assert hint, "every error must carry an actionable hint"


def test_classify_error_codes_stay_within_the_spec_vocabulary() -> None:
    for exc in (
        ScopusConfigError("x"), ScopusAuthError("x"), ScopusNotFoundError("x"),
        ScopusRateLimitError("x"), ScopusNetworkError("x"), ScopusAPIError("x"),
        ValueError("x"), RuntimeError("x"),
    ):
        assert classify(exc)[1] in ERROR_CODES


def test_classify_checks_subclasses_before_the_ScopusAPIError_base() -> None:
    """Auth/not-found/rate-limit all subclass ScopusAPIError; an isinstance
    chain in the wrong order would silently collapse them all to exit 1."""
    assert classify(ScopusAuthError("x"))[0] != classify(ScopusAPIError("x"))[0]
    assert classify(ScopusNotFoundError("x"))[0] != classify(ScopusAPIError("x"))[0]
    assert classify(ScopusRateLimitError("x"))[0] != classify(ScopusAPIError("x"))[0]


def test_classify_prefers_the_per_command_hint_when_one_exists() -> None:
    generic = classify(ScopusAuthError("x"))[2]
    specific = classify(ScopusAuthError("x"), command="search-authors")[2]
    assert specific != generic and "SCOPUS_INST_TOKEN" in specific


# ── end to end through the CLI ──────────────────────────────────────────────

def _status(code: int, body: str = "{}") -> Callable[[httpx.Request], httpx.Response]:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(code, text=body)

    return handler


def test_a_successful_search_exits_zero(cli, fake_scopus) -> None:
    fake_scopus(lambda r: ok_response(search_payload([paper_entry(1)])))
    assert cli("search", "TITLE(x)", "-f", "json") == EXIT_OK


def test_an_empty_result_set_is_not_an_error_and_exits_zero(
    cli, fake_scopus, capsys
) -> None:
    fake_scopus(lambda r: ok_response(search_payload([], total=0)))
    assert cli("search", "TITLE(nothing)", "-f", "json") == EXIT_OK
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["ok"] is True and envelope["count"] == 0 and envelope["rows"] == []


def test_an_api_error_response_exits_one(cli, fake_scopus) -> None:
    fake_scopus(_status(500, "upstream exploded"))
    assert cli("search", "TITLE(x)", "-f", "json") == EXIT_API


def test_an_unknown_describe_target_is_a_usage_error_and_exits_two(cli) -> None:
    assert cli("describe", "no-such-command", "-f", "json") == EXIT_USAGE


def test_an_unknown_format_is_rejected_by_the_parser_with_exit_two() -> None:
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["search", "TITLE(x)", "-f", "bogus"])
    assert excinfo.value.code == EXIT_USAGE


def test_a_missing_required_argument_exits_two() -> None:
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["abstract", "10.1000/x"])  # --type is required
    assert excinfo.value.code == EXIT_USAGE


def test_a_404_from_scopus_exits_three(cli, fake_scopus) -> None:
    fake_scopus(_status(404))
    assert cli("abstract", "10.1000/nope", "--type", "doi", "-f", "json") == EXIT_NOT_FOUND


@pytest.mark.parametrize("status", [401, 403])
def test_an_auth_failure_exits_four(cli, fake_scopus, status: int) -> None:
    fake_scopus(_status(status))
    assert cli("search", "TITLE(x)", "-f", "json") == EXIT_AUTH


def test_a_missing_api_key_is_a_config_error_and_exits_four(
    cli, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode() -> None:
        raise ScopusConfigError("Missing required environment variable(s): api_key")

    monkeypatch.setattr(main_module, "get_settings", explode)
    assert cli("search", "TITLE(x)", "-f", "json") == EXIT_AUTH


def test_being_rate_limited_exits_five(cli, fake_scopus) -> None:
    # settings fixture sets max_retries=0, so the 429 is terminal and no test
    # ever sleeps through a retry backoff.
    fake_scopus(_status(429))
    assert cli("search", "TITLE(x)", "-f", "json") == EXIT_RATE_LIMIT


def test_a_transport_failure_exits_six(cli, fake_scopus) -> None:
    def unreachable(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("name or service not known")

    fake_scopus(unreachable)
    assert cli("search", "TITLE(x)", "-f", "json") == EXIT_NETWORK


def test_a_timeout_exits_six(cli, fake_scopus) -> None:
    def slow(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow")

    fake_scopus(slow)
    assert cli("search", "TITLE(x)", "-f", "json") == EXIT_NETWORK


def test_a_failure_prints_a_parseable_error_envelope_on_stdout(
    cli, fake_scopus, capsys
) -> None:
    fake_scopus(_status(404))
    code = cli("abstract", "10.1000/nope", "--type", "doi", "-f", "json")
    captured = capsys.readouterr()
    envelope = json.loads(captured.out)
    assert code == EXIT_NOT_FOUND
    assert envelope["ok"] is False
    assert envelope["source"] == "scopus"
    assert envelope["command"] == "abstract"
    assert envelope["error"]["code"] == "not_found"
    assert envelope["error"]["hint"]
    assert captured.err  # the human one-liner still goes to stderr


def test_the_documented_exit_code_table_covers_zero_through_six() -> None:
    assert sorted(int(k) for k in EXIT_CODES) == [0, 1, 2, 3, 4, 5, 6]
