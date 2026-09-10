# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
import argparse
from pathlib import Path

from polymath_code_standard.checker import CheckerGroup, Result, check_group, run
from polymath_code_standard.checkers.web._node import (
    ensure_node_modules,
    node_config,
    node_env,
    node_tool,
)

# Rule sets a repo opts into with --framework.
FRAMEWORKS = ('next', 'storybook')

RESTAGE = '(files have been reformatted — please re-stage and recommit)'


def run_eslint(node_dir: Path, files: list[str], frameworks: list[str]) -> Result:
    """Lint and auto-fix, with the named framework rule sets enabled.

    Exits non-zero only when errors remain after the fix pass.
    """
    return run(
        'eslint',
        [
            node_tool(node_dir, 'eslint'),
            '--config',
            node_config(node_dir, 'eslint.config.mjs'),
            '--no-config-lookup',
            '--no-warn-ignored',
            '--fix',
        ],
        files,
        env={**node_env(), 'POLYMATH_ESLINT_FRAMEWORKS': ','.join(frameworks)},
    )


def run_prettier(node_dir: Path, files: list[str]) -> Result:
    """Dry-run to detect issues, then fix in place if needed.

    Prettier skips paths matched by the working directory's .gitignore or .prettierignore.
    """
    if not files:
        return Result(name='prettier', passed=True, skipped=True)
    # --no-editorconfig: a consumer's .editorconfig overrides indent and line width even
    # when --config names an absolute file.
    base = [
        node_tool(node_dir, 'prettier'),
        '--config',
        node_config(node_dir, 'prettier.config.mjs'),
        '--no-editorconfig',
    ]
    env = node_env()
    check = run('prettier', base + ['--check'], files, env=env)
    if check.passed:
        return check
    write = run('prettier', base + ['--write'], files, env=env)
    output = f'{check.output}\n{RESTAGE}' if write.passed else check.output
    return Result(name='prettier', passed=False, output=output, cmd=check.cmd)


def run_stylelint(node_dir: Path, files: list[str]) -> Result:
    """Lint and auto-fix stylesheets."""
    return run(
        'stylelint',
        [node_tool(node_dir, 'stylelint'), '--config', node_config(node_dir, 'stylelint.config.mjs'), '--fix'],
        files,
        env=node_env(),
    )


def _skipped(*names: str) -> list[Result]:
    return [Result(name=name, passed=True, skipped=True) for name in names]


@check_group
class JavascriptGroup(CheckerGroup):
    name = 'javascript'

    def register_args(self, subparser: argparse.ArgumentParser) -> None:
        super().register_args(subparser)
        subparser.add_argument(
            '--framework',
            action='append',
            choices=FRAMEWORKS,
            default=[],
            metavar='NAME',
            help=f'Enable a framework rule set ({", ".join(FRAMEWORKS)}). Repeatable.',
        )

    def run(self, args: argparse.Namespace) -> list[Result]:
        if not args.files:
            return _skipped('eslint', 'prettier')
        node_dir = ensure_node_modules()
        if isinstance(node_dir, Result):
            return [node_dir]
        return [
            run_eslint(node_dir, args.files, args.framework),
            run_prettier(node_dir, args.files),
        ]


@check_group
class CssGroup(CheckerGroup):
    name = 'css'

    def run(self, args: argparse.Namespace) -> list[Result]:
        if not args.files:
            return _skipped('stylelint', 'prettier')
        node_dir = ensure_node_modules()
        if isinstance(node_dir, Result):
            return [node_dir]
        return [
            run_stylelint(node_dir, args.files),
            run_prettier(node_dir, args.files),
        ]


@check_group
class HtmlGroup(CheckerGroup):
    name = 'html'

    def run(self, args: argparse.Namespace) -> list[Result]:
        if not args.files:
            return _skipped('prettier')
        node_dir = ensure_node_modules()
        if isinstance(node_dir, Result):
            return [node_dir]
        return [run_prettier(node_dir, args.files)]
