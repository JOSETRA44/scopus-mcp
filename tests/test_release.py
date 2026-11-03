"""Release gates reject identities/tags that would publish the wrong package."""
import importlib.util
from pathlib import Path
import shutil
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_release", ROOT / "scripts/check_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def test_current_release_metadata_and_tag_match():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    assert release.validate_metadata(ROOT, f"v{version}") == version


def test_a_mismatched_release_tag_is_rejected():
    with pytest.raises(ValueError, match="Release tag"):
        release.validate_metadata(ROOT, "v9.9.9")


def test_old_distribution_name_is_rejected(tmp_path):
    for name in ("pyproject.toml", "server.json", "src/scopus_mcp/__init__.py"):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    project = tmp_path / "pyproject.toml"
    project.write_text(project.read_text(encoding="utf-8").replace('name = "josetra-scopus-mcp"', 'name = "scopus-mcp"'), encoding="utf-8")
    with pytest.raises(ValueError, match="pending PyPI publisher"):
        release.validate_metadata(tmp_path)


def test_upload_directory_rejects_old_or_extra_artifacts(tmp_path):
    (tmp_path / "scopus_mcp-0.1.0-py3-none-any.whl").touch()
    with pytest.raises(ValueError, match="exactly"):
        release.validate_distributions(tmp_path, "0.1.0")
