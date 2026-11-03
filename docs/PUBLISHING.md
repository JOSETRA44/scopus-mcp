# Publish josetra-scopus-mcp to PyPI

The first official distribution is **josetra-scopus-mcp 0.1.0**. The repository
and import name remain `scopus-mcp` and `scopus_mcp`. Console scripts are
`josetra-scopus-mcp`, `scopus-mcp`, `scopus` and `scps`.

## Trusted Publisher configuration

The pending publisher on **pypi.org** must match these values exactly:

| Field | Value |
|---|---|
| Pending project name | `josetra-scopus-mcp` |
| Owner | `JOSETRA44` |
| Repository | `scopus-mcp` |
| Workflow filename | `publish.yml` |
| Environment name | `pypi` |

In GitHub, open **Settings → Environments → New environment**, create `pypi`,
and optionally configure required reviewers or release-tag restrictions.
The workflow uses `id-token: write` only in the publishing job. No PyPI API token,
password, `PYPI_TOKEN` or `TWINE_PASSWORD` secret is needed.

The pending project becomes a normal PyPI project on its first successful upload.
Creating a pending publisher alone does not upload a package or make installation
available. See [PyPI's pending-publisher documentation](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).

## Validate before releasing

Commit and push the prepared files to the default branch, including
`.github/workflows/publish.yml`. Run **Actions → Publish to PyPI → Run workflow**.
This manual run executes the test matrix, builds and checks the artifacts, and
stores `pypi-distributions` for inspection. **Manual runs do not upload to PyPI.**

The workflow checks:

- Windows/Ubuntu on Python 3.11/3.13, static checks and clean wheel installation.
- Distribution name, Python module version, console scripts and MCP metadata.
- Exactly one wheel and one source distribution, with the expected name/version.
- Distribution metadata and README rendering via `twine check --strict`.

For local validation without mixing old artifacts into `dist`:

```sh
uv sync --group dev
uv run pytest
uv run python scripts/check_release.py --metadata-only --tag v0.1.0
uv run python -m build --outdir build/pypi
uv run python scripts/check_release.py --dist build/pypi --tag v0.1.0
uv run python -m twine check --strict build/pypi/*
```

Use an empty output directory for each release. The verifier intentionally rejects
old or extra files, including artifacts from the unrelated `scopus-mcp` name.

## Publish the first release

1. Ensure the commits containing this workflow and package changes are pushed.
2. In **GitHub → Releases → Draft a new release**, create/select tag **`v0.1.0`**
   on that commit. A release from an older commit will not contain the workflow.
3. Add release notes and choose **Publish release**. Saving a draft or pushing
   a tag alone does not publish the package.
4. The `Publish to PyPI` workflow runs validation and builds the artifacts. If
   environment reviewers are configured, approve the `pypi` deployment.
5. The isolated publishing job downloads those artifacts and uploads through
   PyPI Trusted Publishing, with attestations. It does not rebuild the package.
6. Confirm version `0.1.0` at https://pypi.org/project/josetra-scopus-mcp/.

Publishing a GitHub release is the action that authorizes this workflow's upload.
This preparation does not create a release, push a tag or upload anything.

## Verify the published package

```sh
uvx josetra-scopus-mcp@0.1.0 --version
uvx josetra-scopus-mcp@0.1.0 setup --help
uv tool install josetra-scopus-mcp
uv tool update-shell
```

Reopen the terminal, then run `scopus setup` and `scopus check`. For an MCP client:

```json
{
  "mcpServers": {
    "scopus": {"command": "uvx", "args": ["josetra-scopus-mcp"]}
  }
}
```

After confirming the first upload, remove the pending-release notice in README.

## Later releases and failures

Update versions together in `pyproject.toml`, `src/scopus_mcp/__init__.py` and both
version fields in `server.json`; update CHANGELOG and publish tag `v<version>`.
The workflow rejects a tag that differs from package metadata.

- **Invalid publisher:** check owner, repository, `publish.yml` and environment
  `pypi` against the PyPI configuration; do not add a token as a workaround.
- **Version already exists:** PyPI files cannot be overwritten. Inspect the
  existing release and increment the version for a replacement release.
- **Environment approval pending:** approve the deployment in GitHub if required.
- **Manual job skipped publishing:** expected; only a published GitHub release
  triggers an upload.

The workflow targets production PyPI. TestPyPI would require its own separately
configured trusted publisher. MCP Registry publication is also a separate step.

References: [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/),
[official PyPA publishing action](https://github.com/pypa/gh-action-pypi-publish).
