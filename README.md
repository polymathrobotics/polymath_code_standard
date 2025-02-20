# Polymath Source Code Standard

Common configuration for the [Polymath Engineering Source Code Standard](https://www.notion.so/polymathrobotics/WIP-Polymath-Engineering-Standard-18fc0b1ac5fa80e3ae55c38cd4d0ef08?pvs=4#193c0b1ac5fa8002b88ccaaf44095396) - see that document for more details.

## Applying this standard to your repository

1. Copy the following to the top level of the repository:
    1. [`.pre-commit-config.yaml`](./.pre-commit-config.yaml)
    1. [`.config/`](./.config/)
    1. [`.cpplint.cfg`](./.cpplint.cfg)
1. Add the following block to the "Getting Started" or "Setup" section of your repository's `README.md`

    ````markdown
    ### Activating Code Standard Hooks

    [Pre-commit](https://pre-commit.com) hooks are provided to maintain code standards for this repository.

    1. If you do not have pre-commit installed, run `python3 -m pip install pre-commit`
    1. For preexisting repositories, you must run `pre-commit install` in that repository
    1. You can automatically install pre-commit for newly cloned repositories by running
        ```
        $ git config --global init.templateDir ~/.git-template
        $ pre-commit init-templatedir ~/.git-template
        pre-commit installed at /home/asottile/.git-template/hooks/pre-commit
        ```

    Now all git commits will be automatically gated by the configured checks.
    ````

1. Add the following to `.gitlab-ci.yaml` (add the one entry to existing `include:` section if you have it)

    ```yaml
    include:
      # Runs precommit checks
      - project: "polymathrobotics/ci/ci_templates"
        ref: main
        file: "/common/pre-commit.yml"
    ```
1. To apply to pre-existing sources: `pre-commit run --all-files`. Once established, `git commit` will automatically check only the relevant changed files.
1. Comment out blocks of `.pre-commit-config.yaml` where necessary when those standards have not yet been applied to the codebase. Aim to get to all of them, but you may need to go in phases for reviewability.
1. After merging a major reformatting/linting pass, add the commit hash to `.git-blame-ignore-revs` to have Git blames point back to the previous revision instead of blaming the reformatting.

## Updates

When there are updates to the settings in this standard - copy the files as above and apply the changes in a merge request.

Automation is not yet implemented for these updates, but we plan to try using something like <https://github.com/marketplace/actions/repo-file-sync-action> to automatically open merge requests.
