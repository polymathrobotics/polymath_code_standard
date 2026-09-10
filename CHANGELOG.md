# Changelog

All notable changes to this project are documented in this file.
Releases follow semantic versioning as described in [DEVELOPING.md](./DEVELOPING.md).

## 2.6.0

New hooks for Go and the web stack.
Minor bump: new checks, no removals, and existing hooks keep their behavior.

### Added

- `polymath-go`: formats Go with gofumpt and goimports, lints with golangci-lint's standard set plus errorlint, misspell, revive, and unconvert, and checks that staged `go.mod` and `go.sum` are tidy.
  Requires Go 1.23 or newer on `PATH`.
  golangci-lint is downloaded on first use into the hook's own virtualenv, verified against pinned checksums.
- `polymath-javascript`: runs ESLint with `--fix` and then Prettier on JavaScript, JSX, TypeScript, and TSX.
  The rule set is `eslint:recommended`, typescript-eslint recommended, and React, React Hooks, and jsx-a11y rules for JSX/TSX files, with Prettier defaults for formatting.
  Next.js and Storybook rules are opt-in via `--framework next` and `--framework storybook`.
- `polymath-css`: runs Stylelint with `--fix` and then Prettier on CSS and SCSS, using `stylelint-config-standard` and `stylelint-config-standard-scss`.
- `polymath-html`: formats HTML with Prettier.
- `polymath-copyright` inserts and validates `//` style headers in Go, JavaScript, JSX, TypeScript, and TSX files.

### Changed

- Node.js is bundled as a Python dependency.
  The npm packages for the web hooks are installed once per hook revision on first use, and only when a web hook runs.
- Prettier ignores a consuming repo's `.editorconfig` and honors its `.gitignore` and `.prettierignore`.
- Checker configuration files live beside each checker in per-checker subpackages.

### Fixed

- The release tagging job no longer fails the workflow on merges that do not bump the version.
- `--relicense` on the copyright hook preserves Go `//go:build` and `// +build` directives.

### Upgrading

Add the new hook ids to `.pre-commit-config.yaml` as needed.
Repos using `polymath-copyright` with Go or web files will get headers inserted on the first run.
Stage the results and commit again.

## 2.5.0 and earlier

See the [GitHub releases](https://github.com/polymathrobotics/polymath_code_standard/releases).
