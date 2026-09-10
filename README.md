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
    rev: v2.6.0
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
      - id: polymath-go
      - id: polymath-javascript
      - id: polymath-css
      - id: polymath-html
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

Inserts and validates copyright headers for Python, CMake, Shell, C, C++, Go, JavaScript, JSX, TypeScript, and TSX files.
Also creates or updates the `LICENSE` file (skipped for proprietary licenses).
Python, CMake, and Shell files use `#` comment style.
C, C++, Go, JavaScript, JSX, TypeScript, and TSX files use `//` comment style.

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

### `polymath-go`

Runs `golangci-lint` on Go files using Polymath's bundled configuration, and `go mod tidy -diff` on staged `go.mod` and `go.sum` files.

- Formatting with `gofumpt` and `goimports`.
  Files that need it are rewritten in place and the hook fails so you re-stage them.
- Linting with `errcheck`, `govet`, `ineffassign`, `staticcheck`, `unused`, `errorlint`, `misspell`, `revive`, and `unconvert`.
- Module tidiness: staged module files must match what `go mod tidy` would produce.

Go files are grouped by their nearest ancestor `go.mod`, and each group is checked from that module root.
A `.go` file with no `go.mod` above it fails the hook.
Files under `vendor/` are skipped.

> [!NOTE]
> Requires Go 1.23 or newer on `PATH`.
> Install it from [go.dev/dl](https://go.dev/dl).

On its first run the hook downloads a pinned `golangci-lint` release, verified against a checksum pinned in this repo, into its own pre-commit virtualenv.
Nothing is written to your repository, and later runs reuse the download.

---

### `polymath-javascript`

Runs `eslint --fix` and then `prettier` on JavaScript, JSX, TypeScript, and TSX files using Polymath's bundled configuration.
The rule set is `eslint:recommended`, `typescript-eslint` recommended, and for `.jsx`/`.tsx` files the recommended rules of `eslint-plugin-react`, `eslint-plugin-react-hooks`, and `eslint-plugin-jsx-a11y`.
`eslint-config-prettier` is applied last, so ESLint enforces no formatting rules.

Framework rule sets are opt-in, because they report on patterns that are only wrong inside those frameworks.

**Optional:**

- `--framework next` -- Add the `recommended` and `core-web-vitals` rules from `@next/eslint-plugin-next`
- `--framework storybook` -- Add the `flat/recommended` rules from `eslint-plugin-storybook`, which apply to story files

Repeat `--framework` to enable more than one:

```yaml
- id: polymath-javascript
  args: [--framework, next, --framework, storybook]
```

> [!NOTE]
> The first run of this hook downloads its npm packages.
> See [Node tooling is installed on first use](#node-tooling-is-installed-on-first-use).

> [!NOTE]
> Whole-program type checking is not part of this hook.
> `tsc --noEmit` needs your repo's installed `node_modules` and is not a per-file check, so keep it in your own CI.

---

### `polymath-css`

Runs `stylelint --fix` and then `prettier` on CSS and SCSS files.
CSS uses `stylelint-config-standard` and SCSS uses `stylelint-config-standard-scss`.

No arguments.

---

### `polymath-html`

Runs `prettier` on HTML files.

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

## Node tooling is installed on first use

`polymath-javascript`, `polymath-css`, and `polymath-html` run ESLint, Stylelint, and Prettier, none of which pip can install.
Node itself comes from the `nodejs-wheel` PyPI package, so no system Node installation is required.

The first time one of these hooks runs, it installs its pinned npm packages with `npm ci` into `polymath-node/` inside the hook's own pre-commit virtualenv, then stamps a digest of the bundled lockfile and configs beside them.
Expect that first run to take a minute.
Later runs reuse the install, which is shared by every repo on the machine using the same hook revision.
Nothing is written into your repository, so no `.gitignore` entry is needed.

Prettier runs only on the file types these three hooks accept.
JSON, YAML, and Markdown belong to `polymath-json`, `polymath-yaml`, and `polymath-markdown`, and Prettier never sees them.

Prettier honors `.gitignore` and `.prettierignore` in your repository root, which can only narrow the set of files these hooks format.

An `.editorconfig` in your repository is ignored.
These hooks pin indentation and line width to the bundled configuration, so formatting does not change from repo to repo.

---

## `.ruff.toml` is written to the consuming repo

While `ruff` can take a `--config` argument to an absolute file, subdirectory overrides require Ruff to walk up the directory tree.
To support this, the baseline `.ruff.toml` is installed in the repo root for Ruff to find.
Because pre-commit can run the same hook in parallel on batches of files, cleaning up that file after running would introduce a race condition.

Add `/.ruff.toml` to `.gitignore` in the consuming repository.
