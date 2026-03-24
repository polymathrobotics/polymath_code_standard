# Copyright (c) 2025-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""Polymath Code Standard pre-commit hook runner.

Invoked as: polymath_code_standard --group NAME [files ...]

Files are pre-filtered by pre-commit's native type detection before arrival.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .types import CONFIG_DIR, Result, filter_files
from .xml import run_group_xml


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------
def tool(name: str) -> str:
    """Return the absolute path to a console script in this venv."""
    VENV_BIN = Path(sys.executable).parent
    return str(VENV_BIN / name)


def run(name: str, cmd: list[str], files: list[str] | None = None, env: dict | None = None) -> Result:
    """Run a check as a subprocess.

    files=[]  → skipped (no applicable files for this type)
    files=None → run with no extra arguments
    env → merged on top of os.environ when provided
    """
    if files is not None and not files:
        return Result(name=name, passed=True, skipped=True)
    full_cmd = cmd + (files or [])
    merged_env = {**os.environ, **env} if env else None
    proc = subprocess.run(full_cmd, capture_output=True, text=True, env=merged_env)
    output = (proc.stdout + proc.stderr).strip()
    return Result(name=name, passed=proc.returncode == 0, output=output, cmd=full_cmd)


def run_clang_format(cpp_files: list[str]) -> Result:
    """Dry-run to detect issues, then fix in place if needed."""

    if not cpp_files:
        return Result(name='clang-format', passed=True, skipped=True)

    config = CONFIG_DIR / 'clang-format'
    style = f'--style=file:{config}'
    check_cmd = ['clang-format', '--dry-run', '--Werror', style] + cpp_files
    check = subprocess.run(check_cmd, capture_output=True, text=True)
    if check.returncode == 0:
        return Result(name='clang-format', passed=True, cmd=check_cmd)

    subprocess.run(['clang-format', '-i', style] + cpp_files, capture_output=True)
    output = (check.stdout + check.stderr).strip()
    return Result(
        name='clang-format',
        passed=False,
        output=output + '\n(files have been reformatted — please re-stage and recommit)',
        cmd=check_cmd,
    )


def run_forbid_submodules() -> Result:
    """Detect git submodules by checking for mode 160000 in the index.

    The pre-commit-hooks repository version works as a hook by filtering on type 'directory'
    we can't do that here because we are grouping together several checks.
    This 160000 mode check is what their forbid-new-submodules check performs.
    """
    cmd = ['git', 'ls-files', '--stage']
    proc = subprocess.run(cmd, capture_output=True, text=True)
    submodules = [line.split('\t', 1)[-1] for line in proc.stdout.splitlines() if line.startswith('160000')]
    if submodules:
        listing = '\n'.join(f'  {s}' for s in submodules)
        return Result(
            name='forbid-submodules',
            passed=False,
            output=f'Submodule(s) detected — submodules are not allowed:\n{listing}',
            cmd=cmd,
        )
    return Result(name='forbid-submodules', passed=True, cmd=cmd)


# ---------------------------------------------------------------------------
# Check groups
# Files are pre-filtered by pre-commit's native type detection before arrival.
# ---------------------------------------------------------------------------


def _check(
    tool_name: str, args: list[str], files: list[str] | None, name: str = None, env: dict | None = None
) -> Result:
    return run(name or tool_name, [tool(tool_name)] + args, files, env=env)


def run_group_general(files: list[str]) -> list[Result]:
    text = filter_files(files, frozenset({'text'}))
    symlinks = filter_files(files, frozenset({'symlink'}))
    return [
        _check('check-added-large-files', [], files),
        _check('check-case-conflict', [], files),
        _check('check-merge-conflict', [], text),
        _check('check-shebang-scripts-are-executable', [], text),
        _check('check-symlinks', [], symlinks),
        run_forbid_submodules(),
        _check('end-of-file-fixer', [], text),
        _check('mixed-line-ending', [], text),
        _check('trailing-whitespace-fixer', [], text),
    ]


def run_group_python(files: list[str]) -> list[Result]:
    # Special case: allow subdirectories of the repo to have their own overriding Ruff config
    # To do so, we need to let Ruff find the config on its own by walking up the cwd
    # To find the default Ruff config, then, we have to copy it into the repo root
    # we can't specify an absolute path to the config file, and therefore must copy it into
    # the repo root.
    config_file = CONFIG_DIR / 'ruff.toml'
    dest_file = Path.cwd() / '.ruff.toml'
    shutil.copy2(config_file, dest_file)
    return [
        _check('check-ast', [], files),
        _check('ruff', ['format'], files, name='ruff-format'),
        _check('ruff', ['check', '--fix'], files, name='ruff-lint'),
    ]


def run_group_cpp(files: list[str]) -> list[Result]:
    # cpplint has no flag for an absolute config path — it walks up the
    # directory tree looking for the config basename. Use a per-process
    # temp file so parallel hook invocations don't race on a shared filename.
    fd, tmp_path_str = tempfile.mkstemp(dir=Path.cwd(), prefix='.cpplint_', suffix='.cfg')
    os.close(fd)
    tmp_path = Path(tmp_path_str)
    try:
        shutil.copy2(CONFIG_DIR / '.cpplint.cfg', tmp_path)
        results = [
            run_clang_format(files),
            _check('cpplint', [f'--config={tmp_path.name}', '--quiet', '--output=sed'], files),
        ]
    finally:
        tmp_path.unlink(missing_ok=True)
    return results


def run_group_shell(files: list[str]) -> list[Result]:
    return [_check('shellcheck', ['-e', 'SC1091'], files)]


def run_group_cmake(files: list[str]) -> list[Result]:
    return [_check('cmakelint', ['--linelength=140'], files)]


def run_group_docker(files: list[str]) -> list[Result]:
    return [
        _check(
            'hadolint',
            ['--ignore', 'SC1091', '--ignore', 'DL3006', '--ignore', 'DL3008'],
            files,
        )
    ]


def run_group_markdown(files: list[str]) -> list[Result]:
    return [_check('pymarkdown', ['-d', 'MD013', 'fix'], files)]


def run_group_yaml(files: list[str]) -> list[Result]:
    # pre-commit hook definition carries exclude: '\.gitlab-ci\.yml$'
    return [_check('yamllint', ['-d', '{extends: default, rules: {line-length: {max: 256}, commas: false}}'], files)]


def run_group_toml(files: list[str]) -> list[Result]:
    return [_check('check-toml', [], files)]


def run_group_json(files: list[str]) -> list[Result]:
    return [_check('check-json5', [], files)]


def run_group_copyright(files: list[str]) -> list[Result]:
    """Insert copyright headers, splitting by comment style."""
    copyright_notice = str(CONFIG_DIR / 'copyright.txt')
    py_cmake_shell = filter_files(files, frozenset({'python', 'cmake', 'shell'}))
    cpp = filter_files(files, frozenset({'c', 'c++'}))

    return [
        _check(
            'polymath_copyright_header',
            [
                '--license-filepath',
                copyright_notice,
                '--comment-style',
                '#',
                '--allow-past-years',
                '--no-extra-eol',
            ],
            py_cmake_shell,
            name='copyright (py/cmake/shell)',
        ),
        _check(
            'polymath_copyright_header',
            [
                '--license-filepath',
                copyright_notice,
                '--comment-style',
                '//',
                '--allow-past-years',
            ],
            cpp,
            name='copyright (cpp)',
        ),
    ]


def run_group_ansible(files: list[str]) -> list[Result]:
    return [
        _check(
            'python3',
            ['-m', 'ansiblelint', '-v', '--force-color'],
            files,
            name='ansible-lint',
            env={'ANSIBLE_COLLECTIONS_PATH': 'ansible/collections'},
        )
    ]


# ---------------------------------------------------------------------------
# Group registry — order matters for meta-hook output
# ---------------------------------------------------------------------------
ALL_GROUPS: dict[str, object] = {
    'general': run_group_general,
    'python': run_group_python,
    'cpp': run_group_cpp,
    'shell': run_group_shell,
    'cmake': run_group_cmake,
    'docker': run_group_docker,
    'markdown': run_group_markdown,
    'xml': run_group_xml,
    'yaml': run_group_yaml,
    'toml': run_group_toml,
    'json': run_group_json,
    'copyright': run_group_copyright,
    'ansible': run_group_ansible,
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='*', help='Staged files passed by pre-commit')
    parser.add_argument(
        '--group',
        choices=list(ALL_GROUPS),
        required=True,
        help='Check group to run (set by individual hook entry)',
    )
    args = parser.parse_args(argv)

    results = ALL_GROUPS[args.group](args.files)
    failed = [r for r in results if not r.passed and not r.skipped]
    for result in failed:
        result.print()
    return 1 if failed else 0
