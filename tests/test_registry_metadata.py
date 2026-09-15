"""The registry metadata must stay consistent with what actually ships.

The official MCP registry proves package ownership by matching the ``mcp-name``
marker inside the published README against ``server.json``'s ``name``, and it
rejects a submission whose declared version differs from the released package.
Both are easy to break by bumping one file and forgetting the other, and the
failure only shows up at publish time — so it is asserted here instead.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((ROOT / "server.json").read_text(encoding="utf-8"))


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.M)
    assert match, "no version in pyproject.toml"
    return match.group(1)


def test_server_json_has_the_required_keys(manifest: dict) -> None:
    for key in ("$schema", "name", "version", "packages"):
        assert key in manifest, f"server.json is missing {key!r}"


def test_name_is_reverse_dns(manifest: dict) -> None:
    assert re.fullmatch(r"io\.github\.[\w-]+/[\w.-]+", manifest["name"]), manifest["name"]


def test_readme_marker_matches_the_manifest_name(manifest: dict) -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    found = re.search(r"mcp-name:\s*(\S+)", readme)
    assert found, "README.md carries no 'mcp-name:' ownership marker"
    assert found.group(1) == manifest["name"]


def test_manifest_version_matches_the_package(manifest: dict) -> None:
    assert manifest["version"] == project_version()


def test_the_packaged_version_matches_the_manifest_version(manifest: dict) -> None:
    # A mismatch between these two is the most common publish-time rejection.
    assert manifest["packages"][0]["version"] == manifest["version"]


def test_registry_base_url_is_one_the_registry_trusts(manifest: dict) -> None:
    trusted = {
        "pypi": "https://pypi.org",
        "npm": "https://registry.npmjs.org",
        "nuget": "https://api.nuget.org/v3/index.json",
    }
    package = manifest["packages"][0]
    assert package["registryBaseUrl"] == trusted[package["registryType"]]


def test_every_secret_is_flagged_and_has_no_default(manifest: dict) -> None:
    # A default on a secret is how credentials end up committed to a config file.
    for variable in manifest["packages"][0].get("environmentVariables", []):
        if variable.get("isSecret"):
            assert "default" not in variable, variable["name"]
        assert variable.get("description"), f"{variable['name']} has no description"


def test_a_license_file_exists() -> None:
    # Registries refuse to list a server without a detectable licence.
    assert (ROOT / "LICENSE").is_file()
