# Polymath Source Code Standard

Common configuration for the [Polymath Engineering Source Code Standard](https://www.notion.so/polymathrobotics/WIP-Polymath-Engineering-Standard-18fc0b1ac5fa80e3ae55c38cd4d0ef08?pvs=4#193c0b1ac5fa8002b88ccaaf44095396) -- see that document for more details.

One check is provided per file type, with all necessary settings bundled within the hook.
Consuming repositories reference this repo directly via `.pre-commit-config.yaml` -- no config files need to be copied or kept in sync.

## Applying this standard to a repository

1. Create a `.pre-commit-config.yaml` in the target repository root with the following content,
   updating `rev` to the latest release tag.
   Remove any hook IDs that don't apply to your repo's languages.

    ```yaml
    ---
    repos:
      - repo: https://gitlab.com/polymathrobotics/polymath_code_standard
        rev: v1.1.1
        hooks:
          - id: polymath-general
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
          - id: polymath-copyright
    ```

1. Install the hook:

    ```sh
    pre-commit install
    ```

1. Add the following block to the "Getting Started" or "Setup" section of the target repository's `README.md`:

    ````markdown
    ### Code Standard Hooks

    [Pre-commit](https://pre-commit.com) hooks enforce the Polymath code standard on every commit.

    1. Install pre-commit if you don't have it (highly recommended to use `pipx` and the uv-injection to speed it up)
       ```bash
       pipx install pre-commit
       pipx inject pre-commit pre-commit-uv
       ```
    1. Install the hooks: `pre-commit install`

    Commits are now automatically gated by the configured checks.
    You can also run all checks manually with `pre-commit run --all-files`.
    ````

1. Add the following to `.gitlab-ci.yml` (merge into an existing `include:` section if present):

    ```yaml
    include:
      - component: gitlab.com/polymathrobotics/polymath_core/pre-commit@ci-1.3
    ```

1. Apply to pre-existing sources:

    ```sh
    pre-commit run --all-files
    ```

    Some checks auto-fix files (formatters, copyright headers).
    Review the changes, then `git add` and recommit.
    Use `--all-files` again until all checks pass.

1. (ROS only) Remove `ament_lint_common` and individual ament linters from `package.xml`
   and `CMakeLists.txt` -- the Polymath formatters supersede the ROS 2 core style.

1. After a large reformatting pass, add the commit hash to `.git-blame-ignore-revs` so
   that `git blame` points back to the original authors rather than the reformatting commit.

## Upgrading

When this repository releases a new version, update `rev` in the consuming repo's
`.pre-commit-config.yaml` and run `pre-commit run --all-files` to apply any new rules.

Releases follow semantic versioning:
- **Patch** -- dependency version bumps, no behavior change
- **Minor** -- new checks or stricter rules (may require fixing existing code)
- **Major** -- removed checks or breaking changes to existing behavior

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
