# Polymath Source Code Standard

[![CI](https://github.com/polymathrobotics/polymath_code_standard/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/polymathrobotics/polymath_code_standard/actions/workflows/test.yml)

Pre-commit hooks that enforce the Polymath Robotics Engineering formatting and linting standard for a variety of languages.
This is a low-configuration, opinionated set of hooks that take the guesswork out of formatting.
One hook is provided per file type, with all necessary settings bundled.
Consuming repositories reference this repo directly via `.pre-commit-config.yaml` -- no config files need to be copied or kept in sync.

See [DEVELOPING.md](./DEVELOPING.md) for development workflows.

## Prerequisites

> [!NOTE]
> Consider adding this prerequisites section to your own repository's `README.md`.

Install [pre-commit](https://pre-commit.com).
Our recommended approach is with [uv](https://github.com/astral-sh/uv).

```shell
uv tool install --with pre-commit-uv pre-commit
```

Set up pre-commit hooks in the repository:

```shell
pre-commit install
```

## Configuration

Add the following to your repository's `.pre-commit-config.yaml`.
Use only the hooks that apply to your project.

```yaml
---
repos:
  - repo: https://github.com/polymathrobotics/polymath_code_standard
    rev: v2.5.0
    hooks:
      # File hygiene for all staged files
      - id: polymath-general
      # Copyright headers and LICENSE file management
      - id: polymath-copyright
        args: [--license, Apache-2.0, --copyright-org, "Your Org Name"]
      # Language-specific checks
      - id: polymath-python
      - id: polymath-cpp
      - id: polymath-ros
      - id: polymath-shell
      - id: polymath-cmake
      - id: polymath-docker
      - id: polymath-markdown
      - id: polymath-xml
      - id: polymath-yaml
      - id: polymath-toml
      - id: polymath-json
      - id: polymath-ansible
```

See the [Hook Reference](#hook-reference) for details on each hook and its available arguments.

## First-time use

Apply your newly configured hooks to all existing files:

```shell
pre-commit run --all-files
```

Stage the reformatted files, then run again to surface any failures that require manual correction.

> [!NOTE]
> These formatters are not compatible with other formatting standards.
> In ROS projects, remove `ament_lint` in favor of these hooks.

> [!NOTE]
> After a large reformatting pass, add the commit hash to `.git-blame-ignore-revs` so `git blame` points back to the original authors rather than the reformatting commit.

## CI

Add the following GitHub Actions workflow to run pre-commit on every push and pull request:

```yaml
---
name: Lint

on:
  push:
    branches: [main]
  pull_request:

jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - uses: pre-commit/action@v3.0.1
```

## Hook Reference

### `polymath-general`

Applies file hygiene checks to all staged files.

- Prevents committing large files
- Detects filename case conflicts
- Detects merge conflict markers
- Ensures shebanged scripts are executable
- Validates symlinks
- Blocks git submodules
- Adds a trailing newline to files
- Normalizes line endings
- Removes trailing whitespace

No arguments.

---

### `polymath-copyright`

Inserts and validates copyright headers for Python, CMake, Shell, C, and C++ files.
Also creates or updates the `LICENSE` file (skipped for proprietary licenses).
Python, CMake, and Shell files use `#` comment style.
C and C++ files use `//` comment style.

**Required:**

- `--license SPDX_ID` -- SPDX license ID (e.g. `Apache-2.0`, `MIT`) or `proprietary`
- `--copyright-org ORG` -- Name of the copyright-holding organization (mutually exclusive with `--wildcard-copyright-org`)
- `--wildcard-copyright-org` -- Accept any copyright holder on the copyright line, for multi-contributor repos (mutually exclusive with `--copyright-org`)

**Optional:**

- `--copyright-year YEAR` -- Copyright start year (default: current year)
- `--reuse-style` -- Force REUSE-style 2-line copyright headers
- `--relicense` -- Strip any existing leading comment block before inserting the new header

Example:

```yaml
- id: polymath-copyright
  args: [--license, Apache-2.0, --copyright-org, "Polymath Robotics, Inc."]
```

---

### `polymath-python`

Runs `ruff format`, `ruff check --fix`, and Python AST validation.

> [!NOTE]
> This hook writes `/.ruff.toml` to the consuming repo root.
> Add `/.ruff.toml` to `.gitignore`.
> See [`.ruff.toml` note](#rufftoml-is-written-to-the-consuming-repo) for details.

No arguments.

---

### `polymath-cpp`

Runs `clang-format` and `cpplint` on C and C++ files using Polymath's bundled configuration.

No arguments.

---

### `polymath-ros`

Enforces ROS-specific C++ conventions.
Requires that multi-threaded executors (`MultiThreadedExecutor`, `EventsCBGExecutor`) specify an explicit thread count.
Suppress a check on a specific line with a trailing `// NOLINT` comment.

No arguments.

---

### `polymath-shell`

Runs `shellcheck` on shell scripts.
Detects scripts by shebang line, not just file extension.
Excludes `.envrc` files.

No arguments.

---

### `polymath-cmake`

Runs `cmakelint` on CMake files with a maximum line length of 140.

No arguments.

---

### `polymath-docker`

Runs `hadolint` on Dockerfiles.

No arguments.

---

### `polymath-markdown`

Runs `pymarkdown` with the line-length rule disabled and auto-fixes issues where possible.

No arguments.

---

### `polymath-xml`

Validates XML well-formedness and schema compliance.
Supports `xml-model` processing instructions and `xsi:noNamespaceSchemaLocation`.
Includes a bundled `package_format3.xsd` schema for ROS `package.xml` validation.

No arguments.

---

### `polymath-yaml`

Formats and validates YAML files using `yamlfix`.
By default, adds a `---` explicit document start marker.

**Optional:**

- `--no-explicit-start` -- Omit the `---` document start marker

---

### `polymath-toml`

Validates TOML syntax.

No arguments.

---

### `polymath-json`

Validates JSON and JSON5 syntax.
Excludes `.geojson` files.

No arguments.

---

### `polymath-ansible`

Installs Ansible collections and roles from `ansible/requirements.yml` and runs `ansible-lint` with Polymath's configuration.
Dependencies are cached in `.polymath-ansible/` (automatically gitignored) and only reinstalled when `requirements.yml` changes.

No arguments.

---

## `.ruff.toml` is written to the consuming repo

While `ruff` can take a `--config` argument to an absolute file, subdirectory overrides require Ruff to walk up the directory tree.
To support this, the baseline `.ruff.toml` is installed in the repo root for Ruff to find.
Because pre-commit can run the same hook in parallel on batches of files, cleaning up that file after running would introduce a race condition.

Add `/.ruff.toml` to `.gitignore` in the consuming repository.
