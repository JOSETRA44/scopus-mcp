"""Validate the exact metadata and artifacts that will be uploaded to PyPI."""
import argparse
from email.parser import BytesParser
from pathlib import Path
import json
import re
import tarfile
import tomllib
import zipfile

PROJECT = "josetra-scopus-mcp"


def validate_metadata(root: Path, tag: str | None = None) -> str:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = project["version"]
    if project["name"] != PROJECT:
        raise ValueError(f"Project name must match the pending PyPI publisher: {PROJECT}")
    if tag is not None and tag != f"v{version}":
        raise ValueError(f"Release tag must be v{version}; got {tag!r}")
    manifest = json.loads((root / "server.json").read_text(encoding="utf-8"))
    package = manifest["packages"][0]
    if package["identifier"] != PROJECT or package["version"] != version or manifest["version"] != version:
        raise ValueError("server.json package name/version does not match pyproject.toml")
    init = (root / "src/scopus_mcp/__init__.py").read_text(encoding="utf-8")
    if not re.search(rf'^__version__ = "{re.escape(version)}"$', init, re.M):
        raise ValueError("Python module version does not match the release")
    scripts = project["scripts"]
    for name in (PROJECT, "scopus-mcp", "scopus", "scps"):
        if scripts.get(name) != "scopus_mcp.cli:main":
            raise ValueError(f"Missing expected console entry point: {name}")
    return version


def validate_distributions(directory: Path, version: str) -> None:
    stem = f"josetra_scopus_mcp-{version}"
    expected = {f"{stem}-py3-none-any.whl", f"{stem}.tar.gz"}
    files = {p.name for p in directory.iterdir()}
    if files != expected:
        raise ValueError(f"Upload directory must contain exactly {sorted(expected)}; found {sorted(files)}")
    for filename in sorted(expected):
        path = directory / filename
        if filename.endswith(".whl"):
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                candidates = [n for n in names if n.endswith(".dist-info/METADATA")]
                if len(candidates) != 1:
                    raise ValueError("Wheel must contain one METADATA file")
                metadata = archive.read(candidates[0])
        else:
            with tarfile.open(path) as archive:
                names = archive.getnames()
                item = archive.extractfile(f"{stem}/PKG-INFO")
                if item is None:
                    raise ValueError("Source distribution has no PKG-INFO")
                metadata = item.read()
        for name in names:
            parts = Path(name).parts
            if any(p in {".env", "credentials.env", ".venv", ".git"} for p in parts):
                raise ValueError(f"Private/local file included in artifact: {name}")
        parsed = BytesParser().parsebytes(metadata)
        if parsed["Name"] != PROJECT or parsed["Version"] != version:
            raise ValueError(f"Wrong distribution identity in {filename}")
    print(f"Validated {PROJECT} {version}: wheel and sdist ready.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="GitHub release tag; must equal v<package version>")
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    version = validate_metadata(Path(__file__).resolve().parents[1], args.tag)
    if not args.metadata_only:
        validate_distributions(args.dist, version)


if __name__ == "__main__":
    main()
