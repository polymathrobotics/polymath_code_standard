verify:
  pre-commit clean
  pre-commit run --all-files

# Update the rev: pin in README.md to match the version in pyproject.toml.
# Run this whenever you bump the version.
sync-readme:
  #!/usr/bin/env python3
  import re, tomllib
  with open("pyproject.toml", "rb") as f:
      version = tomllib.load(f)["project"]["version"]
  with open("README.md") as f:
      content = f.read()
  updated = re.sub(r"(rev: v)\d+\.\d+\.\d+", rf"\g<1>{version}", content)
  with open("README.md", "w") as f:
      f.write(updated)
  print(f"README.md pinned to v{version}")

# Bump the package version and sync the README pin in one step.
# Usage: just bump minor  (or major / patch)
bump level:
  #!/usr/bin/env bash
  set -euo pipefail
  uv version --bump {{ level }}
  just sync-readme
