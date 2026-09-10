# Development workflows

## Running pre-commit

`.pre-commit-config.yaml` in this repo is a `repo: .` dev config that runs the hook directly from the working tree.
Pre-commit will cache `HEAD` so your changes won't be checked against the local latest sources.

Run `just verify` after `commit --no-verify` to use your latest HEAD instead of any cached version.

## Updates

Releases follow semantic versioning:
- **Patch** -- bugfixes or nonfunctional dependency updates, must not require any manual changes from user
- **Minor** -- new checks, formatting changes, or new linting checks. May require fixing existing code.
- **Major** -- removed checks or other breaking changes to existing API

To bump the version, use `just bump` -- it updates `pyproject.toml` and syncs the README pin in one step:

```shell
just bump minor   # or major / patch
```

Then add a `## <version>` section to `CHANGELOG.md` describing the release.

CI fails PRs where the README pin or the changelog section is missing for the version in `pyproject.toml`.
On merge to main, CI pushes the tag and publishes a GitHub release whose notes are that changelog section.

## Testing

Add files to `test_files/` to validate linter settings work, if other files of that type are not present in this repo.
