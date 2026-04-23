# Polymath Source Code Standard

Pre-commit hooks that enforce the Polymath Robotics Engineering formatting and linting standard for a variety of languages.

This is a low-configuration, highly opinionated set of hooks that take the guesswork out of formatting.

One check is provided per file type, with all necessary settings bundled within the hook.
Consuming repositories reference this repo directly via `.pre-commit-config.yaml` -- no config files need to be copied or kept in sync.

# Usage

## Prerequisites

> [!NOTE]
> You may want to add the following text from this prerequisites section to your own repository's `README.md`!

Install [pre-commit](https://pre-commit.com).
While there are several ways to do this, our favorit is with [uv](https://github.com/astral-sh/uv) - it's "scary fast".

```shell
uv tool install --with pre-commit-uv pre-commit
```

Set up pre-commit hooks in the repository:

```shell
pre-commit install
```

### Hooks

In your repository's `.pre-commit-config.yaml`, use these hooks.
See the following for a list of all available hooks.
Feel free to use only the ones that apply to your usage.

```yaml
---
repos:
    - repo: https://github.com/polymathrobotics/polymath_code_standard
    rev: v2.0.0
    hooks:
        # Basic checks and fixes that apply to any text file and the git repository itself
        - id: polymath-general
        # Enforce and insert copyright headers in source code for the project's license
        - id: polymath-copyright
        args: [--license, <SPDX_ID or 'proprietary'>, --copyright-org, <organization name>]
        # Specific languages
        - id: polymath-python
        - id: polymath-cpp
        - id: polymath-shell
        - id: polymath-cmake
        - id: polymath-docker
        - id: polymath-markdown
        - id: polymath-xml
        - id: polymath-yaml
        - id: polymath-toml
        - id: polymath-json
```

## First-time use

Apply your newly configured hooks to all sources with the following.
You should also do this whenever you update to a newer version.

```shell
pre-commit run --all-files
```

You may now want to stage the new changes, then run again to check for any failures that require manual correction.

> [!NOTE]
> These formatters are likely not compatible with other formatting standards, for example in ROS you will now want to remove `ament_lint` in favor of these hooks.

> [!NOTE]
> After a large reformatting pass, add the commit hash to `.git-blame-ignore-revs` so that `git blame` points back to the original authors rather than the reformatting commit.

## CI

See [.github/workflows/test.yml](./.github/workflows/test.yml) for a simple GitHub Actions configuration that runs pre-commit hooks.

## Updates

Releases follow semantic versioning:
- **Patch** -- bugfixes or nonfunctional dependency updates, must not require any manual changes from user
- **Minor** -- new checks, formatting changes, or new linting checks. May require fixing existing code.
- **Major** -- removed checks or other breaking changes to existing API

## Notes

### `.ruff.toml` is written to the consuming repo

While `ruff` can take a `--config` argument to an absolute file, we are currently allowing subdirectories of a repository to override Ruff configuration.

To enable this, we have to omit `--config` and let Ruff walk up the directory tree.
This means we need to install our baseline `.ruff.toml` configuration in the root of the repo for Ruff to find.
Because `pre-commit` can run the same hook in parallel on batches of files, there is a race condition if we try to clean up that file after running.

TL;DR Add `/.ruff.toml` to `.gitignore` for the repository to ignore that it's been put there.

### Developing this repository

`.pre-commit-config.yaml` in this repo is a `repo: .` dev config that runs the hook directly from the working tree.

To test your latest version as it will run in consuming repos:
1. Commit your latest changes
1. `pre-commit autoupdate` will change `.pre-commit-config` to point to the latest commit hash on your working copy
1. `pre-commit run --all-files`

Add files to `test_files/` to validate linter settings work, if other files of that type are not present in this repo.
