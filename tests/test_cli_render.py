"""Output layer: the five formats, the two envelopes, and UTF-8 survival.

ARSENAL-SPEC §1 (output contract), §6.1/§6.2 (format + envelope tests) and
§9 (Windows console encoding).
"""

from __future__ import annotations

import csv
import io
import json

import pytest

from scopus_mcp.cli.render import (
    FORMATS,
    Emitter,
    Style,
    build_envelope,
    build_error,
    color_enabled,
    columns_of,
    force_utf8,
    render_csv,
    render_jsonl,
    render_md,
    render_table,
    to_json,
)

ROWS = [
    {"scopus_id": "85001", "title": "Machine Learning in Medicine", "cited_by_count": 42,
     "open_access": True},
    {"scopus_id": "85002", "title": "Deep Learning Survey", "cited_by_count": 120,
     "open_access": False},
]

# Ragged on purpose: real Scopus rows drop keys whose value is empty, so the
# renderers must cope with rows that do not share a key set.
RAGGED = [
    {"scopus_id": "85001", "title": "Has a DOI", "doi": "10.1000/a"},
    {"scopus_id": "85002", "country": "Peru"},
]

PLAIN = Style(enabled=False)


@pytest.fixture(autouse=True)
def fixed_terminal_width(monkeypatch: pytest.MonkeyPatch) -> None:
    """shutil.get_terminal_size honours COLUMNS — pin it so table widths are
    identical on a developer laptop and in CI."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.setenv("LINES", "50")


# ── table ───────────────────────────────────────────────────────────────────

class TestTableFormat:
    def test_table_prints_a_header_and_one_line_per_row(self) -> None:
        out = render_table(ROWS, PLAIN).splitlines()
        # title omitted -> header, rule, two data lines
        assert len(out) == 4
        assert out[0].split() == ["scopus_id", "title", "cited_by_count", "open_access"]
        assert "Machine Learning in Medicine" in out[2]
        assert "Deep Learning Survey" in out[3]

    def test_table_renders_booleans_as_yes_and_no(self) -> None:
        out = render_table(ROWS, PLAIN)
        assert "yes" in out and "no" in out

    def test_table_of_an_empty_row_list_says_no_rows_instead_of_crashing(self) -> None:
        assert render_table([], PLAIN) == "(no rows)\n"

    def test_table_of_ragged_rows_leaves_missing_cells_blank(self) -> None:
        out = render_table(RAGGED, PLAIN).splitlines()
        assert out[0].split() == ["scopus_id", "title", "doi", "country"]
        assert "Peru" in out[3]
        assert "10.1000/a" not in out[3]

    def test_table_includes_the_title_line_when_one_is_given(self) -> None:
        assert render_table(ROWS, PLAIN, title="Papers").startswith("Papers\n")


# ── csv ─────────────────────────────────────────────────────────────────────

class TestCsvFormat:
    def test_csv_header_and_values_match_the_rows(self) -> None:
        parsed = list(csv.DictReader(io.StringIO(render_csv(ROWS))))
        assert [r["scopus_id"] for r in parsed] == ["85001", "85002"]
        assert parsed[0]["title"] == "Machine Learning in Medicine"
        assert parsed[0]["cited_by_count"] == "42"

    def test_csv_of_an_empty_row_list_is_empty_not_a_bare_header(self) -> None:
        assert render_csv([]) == ""

    def test_csv_header_is_the_union_of_ragged_row_keys(self) -> None:
        parsed = list(csv.DictReader(io.StringIO(render_csv(RAGGED))))
        assert list(parsed[0]) == ["scopus_id", "title", "doi", "country"]
        assert parsed[1]["title"] == ""
        assert parsed[1]["country"] == "Peru"


# ── markdown ────────────────────────────────────────────────────────────────

class TestMarkdownFormat:
    def test_md_is_a_github_table_with_a_separator_row(self) -> None:
        lines = render_md(ROWS).splitlines()
        assert lines[0] == "| scopus_id | title | cited_by_count | open_access |"
        assert lines[1] == "| --- | --- | --- | --- |"
        assert lines[2].startswith("| 85001 | Machine Learning in Medicine | 42 | yes |")

    def test_md_of_an_empty_row_list_renders_a_placeholder(self) -> None:
        assert render_md([]) == "_(no rows)_\n"

    def test_md_ragged_rows_keep_the_column_count_stable(self) -> None:
        lines = render_md(RAGGED).splitlines()
        assert all(line.count("|") == 5 for line in lines)

    def test_md_escapes_a_pipe_inside_a_value_so_the_table_survives(self) -> None:
        assert "a \\| b" in render_md([{"title": "a | b"}])


# ── jsonl ───────────────────────────────────────────────────────────────────

class TestJsonlFormat:
    def test_jsonl_emits_one_json_object_per_row_and_nothing_else(self) -> None:
        lines = render_jsonl(ROWS).splitlines()
        assert len(lines) == 2
        assert [json.loads(line) for line in lines] == ROWS

    def test_jsonl_of_an_empty_row_list_is_the_empty_string(self) -> None:
        assert render_jsonl([]) == ""

    def test_jsonl_keeps_ragged_rows_exactly_as_given(self) -> None:
        assert [json.loads(line) for line in render_jsonl(RAGGED).splitlines()] == RAGGED


# ── shared behaviour ────────────────────────────────────────────────────────

def test_columns_of_is_the_union_of_keys_in_first_seen_order() -> None:
    assert columns_of(RAGGED) == ["scopus_id", "title", "doi", "country"]


def test_columns_of_an_empty_row_list_is_empty() -> None:
    assert columns_of([]) == []


@pytest.mark.parametrize("fmt", FORMATS)
def test_every_format_renders_the_same_rows_without_raising(fmt: str) -> None:
    emitter = Emitter(fmt=fmt, no_color=True)
    buf = io.StringIO()
    emitter.write = buf.write  # type: ignore[method-assign]
    emitter.emit("search", ROWS)
    assert "85001" in buf.getvalue()


@pytest.mark.parametrize("fmt", FORMATS)
def test_every_format_survives_an_empty_row_list(fmt: str) -> None:
    """An empty result set is not an error (ARSENAL-SPEC §2) — every renderer
    must produce something printable rather than blow up."""
    emitter = Emitter(fmt=fmt, no_color=True)
    buf = io.StringIO()
    emitter.write = buf.write  # type: ignore[method-assign]
    emitter.emit("search", [])
    rendered = buf.getvalue()
    if fmt == "json":
        assert json.loads(rendered)["rows"] == []
    else:
        assert isinstance(rendered, str)


def test_color_is_disabled_when_no_color_is_requested() -> None:
    assert color_enabled(True, io.StringIO()) is False


def test_color_is_disabled_when_the_NO_COLOR_env_var_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    assert color_enabled(False, io.StringIO()) is False


def test_color_is_disabled_when_the_stream_is_not_a_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert color_enabled(False, io.StringIO()) is False


# ── envelopes ───────────────────────────────────────────────────────────────

ENVELOPE_KEYS = {
    "ok", "command", "source", "fetched_at", "cached", "count", "meta", "data", "rows",
    "retrieved_at", "served_at",
}


class TestSuccessEnvelope:
    def test_envelope_carries_every_key_the_spec_requires(self) -> None:
        assert set(build_envelope("search", ROWS)) == ENVELOPE_KEYS

    def test_envelope_count_equals_the_number_of_rows(self) -> None:
        for rows in ([], ROWS, RAGGED):
            assert build_envelope("search", rows)["count"] == len(rows)

    def test_envelope_names_the_source_so_a_fanned_out_agent_can_attribute_it(
        self,
    ) -> None:
        assert build_envelope("search", ROWS)["source"] == "scopus"

    def test_envelope_ok_is_true_even_for_an_empty_result_set(self) -> None:
        empty = build_envelope("search", [])
        assert empty["ok"] is True and empty["rows"] == [] and empty["count"] == 0

    def test_envelope_fetched_at_is_utc_iso8601_with_a_z_suffix(self) -> None:
        stamp = build_envelope("search", ROWS)["fetched_at"]
        assert stamp.endswith("Z") and len(stamp) == 20

    def test_envelope_reports_the_cached_flag_it_was_handed(self) -> None:
        assert build_envelope("search", ROWS, cached=True)["cached"] is True

    def test_envelope_meta_drops_keys_whose_value_is_none(self) -> None:
        meta = build_envelope("search", ROWS, meta={"total": 7, "cursor": None})["meta"]
        assert meta == {"total": 7}

    def test_envelope_data_defaults_to_an_empty_object_not_null(self) -> None:
        assert build_envelope("search", ROWS)["data"] == {}


class TestErrorEnvelope:
    def test_error_envelope_has_ok_false_and_the_five_required_keys(self) -> None:
        env = build_error("abstract", "not_found", "no such paper", "check the id")
        assert set(env) == {"ok", "command", "source", "fetched_at", "error"}
        assert env["ok"] is False

    def test_error_envelope_names_the_source_so_failures_stay_attributable(self) -> None:
        assert build_error("abstract", "api", "boom", "retry")["source"] == "scopus"

    def test_error_envelope_carries_code_message_and_an_actionable_hint(self) -> None:
        error = build_error("abstract", "auth", "bad key", "Set SCOPUS_API_KEY")["error"]
        assert set(error) == {"code", "message", "hint"}
        assert error["code"] == "auth"
        assert error["hint"]

    def test_emit_error_writes_the_envelope_to_stdout_in_machine_formats(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        # A pipeline doing `scopus ... -f json | jq` must be able to parse the
        # failure, so the envelope goes to stdout and only the note to stderr.
        Emitter(fmt="json", no_color=True).emit_error(
            "abstract", "not_found", "missing", "check the id"
        )
        captured = capsys.readouterr()
        assert json.loads(captured.out)["error"]["code"] == "not_found"
        assert "missing" in captured.err

    def test_emit_error_keeps_stdout_clean_in_table_mode(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        Emitter(fmt="table", no_color=True).emit_error(
            "abstract", "not_found", "missing", "check the id"
        )
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "missing" in captured.err and "check the id" in captured.err


def test_notes_go_to_stderr_so_stdout_stays_machine_readable(
    capsys: pytest.CaptureFixture,
) -> None:
    emitter = Emitter(fmt="jsonl", no_color=True)
    emitter.note("harvested 10 rows")
    emitter.emit("search", ROWS)
    captured = capsys.readouterr()
    assert "harvested" in captured.err
    assert all(json.loads(line) for line in captured.out.splitlines())


def test_quiet_suppresses_notes_but_never_errors(capsys: pytest.CaptureFixture) -> None:
    emitter = Emitter(fmt="table", quiet=True, no_color=True)
    emitter.note("progress")
    emitter.warn("boom")
    captured = capsys.readouterr()
    assert "progress" not in captured.err
    assert "boom" in captured.err


# ── UTF-8 (ARSENAL-SPEC §9) ─────────────────────────────────────────────────

ACCENTED = [
    {"country": "Perú", "city": "Ñuñoa", "note": "Côte d'Ivoire"},
    {"country": "España", "city": "Málaga", "note": "Fauré, Gabriel"},
]


@pytest.mark.parametrize(
    "render",
    [render_md, render_csv, render_jsonl, lambda rows: render_table(rows, PLAIN)],
    ids=["md", "csv", "jsonl", "table"],
)
def test_accented_text_survives_every_format(render) -> None:
    rendered = render(ACCENTED)
    for token in ("Perú", "Ñuñoa", "Côte d'Ivoire", "España", "Málaga"):
        assert token in rendered


def test_json_keeps_accents_literal_instead_of_escaping_them_to_ascii() -> None:
    rendered = to_json(build_envelope("search", ACCENTED))
    assert "Perú" in rendered and "\\u00fa" not in rendered


def test_accented_rows_round_trip_through_jsonl_unchanged() -> None:
    assert [json.loads(l) for l in render_jsonl(ACCENTED).splitlines()] == ACCENTED


def test_accented_rows_round_trip_through_csv_unchanged() -> None:
    parsed = list(csv.DictReader(io.StringIO(render_csv(ACCENTED))))
    assert [dict(row) for row in parsed] == ACCENTED


def test_every_format_can_encode_accented_output_as_utf8_bytes() -> None:
    """The real failure mode on Windows is at *encode* time, not render time."""
    for fmt in FORMATS:
        emitter = Emitter(fmt=fmt, no_color=True)
        buf = io.StringIO()
        emitter.write = buf.write  # type: ignore[method-assign]
        emitter.emit("search", [{"title": row["country"], **row} for row in ACCENTED])
        assert "Perú".encode("utf-8") in buf.getvalue().encode("utf-8")


class _FakeStream:
    """Stands in for a cp1252 console: records how it was reconfigured."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def reconfigure(self, **kwargs) -> None:
        self.calls.append(kwargs)


def test_force_utf8_reconfigures_the_console_streams() -> None:
    streams = (_FakeStream(), _FakeStream())
    force_utf8(streams)
    for stream in streams:
        assert stream.calls == [{"encoding": "utf-8", "errors": "replace"}]


def test_force_utf8_is_a_no_op_on_a_stream_without_reconfigure() -> None:
    # Under pytest's capture (and on some POSIX setups) stdout is not a real
    # TextIOWrapper; forcing UTF-8 must not take the CLI down with it.
    force_utf8((io.StringIO(),))


def test_force_utf8_swallows_a_stream_that_refuses_to_be_reconfigured() -> None:
    class Stubborn(_FakeStream):
        def reconfigure(self, **kwargs) -> None:
            raise ValueError("detached buffer")

    force_utf8((Stubborn(),))
