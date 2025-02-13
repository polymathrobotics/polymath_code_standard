# Polymath Source Code Standard

Common configuration for the [Polymath Engineering Source Code Standard](https://www.notion.so/polymathrobotics/WIP-Polymath-Engineering-Standard-18fc0b1ac5fa80e3ae55c38cd4d0ef08?pvs=4#193c0b1ac5fa8002b88ccaaf44095396) - see that document for more details.

## Applying this standard to your repository

1. Copy [`.pre-commit-config.yaml`](./.pre-commit-config.yaml) to the top level of your repository
1. Copy [`.config`](./.config/) directory to the top level of your repository
1. Add the following block to the "Getting Started" or "Setup" section of your repository's `README.md`

    ```markdown
    ### Activating Code Standard Hooks

    Pre-commit hooks are provided to maintain code standards for this repository
    - [If you do not have pre-commit installed] `python3 -m pip install pre-commit`
    - `pre-commit install` to activate for this repository

    Now all git commits will be automatically gated by the configured checks.
    ```

1. Comment out blocks of `.pre-commit-config.yaml` where necessary when those standards have not yet been applied to the codebase. Aim to get to all of them, but you may need to go in phases for reviewability.
1. After merging a major reformatting/linting pass, add the commit hash to `.git-blame-ignore-revs` to have Git blames point back to the previous revision instead of blaming the reformatting.

## Updates

When there are updates to the settings in this standard - copy the files as above and apply the changes in a merge request.

Automation is not yet implemented for these updates, but we plan to try using something like <https://github.com/marketplace/actions/repo-file-sync-action> to automatically open merge requests.
