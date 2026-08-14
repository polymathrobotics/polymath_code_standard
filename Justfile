verify:
  pre-commit clean
  pre-commit run --all-files

# Update the rev: pin in README.md to match the current package version.
sync-readme:
  #!/usr/bin/env bash
  set -euo pipefail
  VERSION=$(uv version | awk '{print $2}')
  sed -i "s/rev: v[0-9]*\.[0-9]*\.[0-9]*/rev: v$VERSION/" README.md
  echo "README.md pinned to v$VERSION"

# Bump the package version and sync the README pin in one step.
# Usage: just bump minor  (or major / patch)
bump level:
  #!/usr/bin/env bash
  set -euo pipefail
  uv version --bump {{ level }}
  just sync-readme
