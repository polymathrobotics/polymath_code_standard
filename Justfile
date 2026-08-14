verify:
  pre-commit clean
  pre-commit run --all-files

# Bump the package version and sync the README pin in one step.
# Usage: just bump minor  (or major / patch)
bump level:
  #!/usr/bin/env python3
  import re, sys, tomllib, subprocess
  level = "{{level}}"
  if level not in ("major", "minor", "patch"):
      print(f"Invalid level '{level}'. Use major, minor, or patch.")
      sys.exit(1)
  with open("pyproject.toml", "rb") as f:
      data = tomllib.load(f)
  major, minor, patch = map(int, data["project"]["version"].split("."))
  if level == "major":
      major, minor, patch = major + 1, 0, 0
  elif level == "minor":
      minor, patch = minor + 1, 0
  else:
      patch = patch + 1
  new_version = f"{major}.{minor}.{patch}"
  with open("pyproject.toml") as f:
      content = f.read()
  updated = re.sub(r'^version = ".*"', f'version = "{new_version}"', content, flags=re.MULTILINE)
  with open("pyproject.toml", "w") as f:
      f.write(updated)
  print(f"Bumped to v{new_version}")
  subprocess.run(["just", "sync-readme"], check=True)

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
