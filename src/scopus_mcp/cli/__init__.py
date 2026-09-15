"""Terminal CLI for scopus-mcp: run Scopus lookups directly from a shell.

This package powers the `scopus` / `scps` / `scopus-mcp` commands. Running an
entry point with NO subcommand keeps the original behavior of starting the MCP
stdio server (see main.main) — that path is untouched.
"""

from .main import main, main_cli, run_cli
from .parser import build_parser, get_version

__all__ = ["build_parser", "get_version", "main", "main_cli", "run_cli"]
