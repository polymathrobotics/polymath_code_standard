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

## Testing

Add files to `test_files/` to validate linter settings work, if other files of that type are not present in this repo.
