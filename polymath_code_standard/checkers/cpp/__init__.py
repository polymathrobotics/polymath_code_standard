# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
import argparse
import importlib.resources
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from polymath_code_standard.checker import CheckerGroup, Result, check_group, tool

# Config files bundled alongside this checker
CONFIG_DIR = importlib.resources.files(__package__)

_IWYU_RE = re.compile(r'^(.+?):(\d+):\s+Add (#include (?:<[^>]+>|"[^"]+")) for')


def _parse_iwyu_output(output: str) -> dict[str, set[str]]:
    missing: dict[str, set[str]] = {}
    for line in output.splitlines():
        m = _IWYU_RE.match(line)
        if m:
            filepath, _, directive = m.groups()
            missing.setdefault(filepath, set()).add(directive)
    return missing


def _insertion_point(lines: list[str]) -> int:
    """Return the line index after which to insert new #include directives."""
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].lstrip().startswith('#include'):
            return i + 1
    # No existing includes: skip past the top-of-file header, insert before first real code.
    in_block_comment = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if in_block_comment:
            if '*/' in stripped:
                in_block_comment = False
            continue
        if not stripped or stripped.startswith('//'):
            continue
        if stripped.startswith('/*'):
            if '*/' not in stripped[2:]:
                in_block_comment = True
            continue
        if stripped.startswith(('#pragma once', '#ifndef', '#define')):
            continue
        return i
    return len(lines)


def _insert_includes(filepath: str, directives: set[str]) -> None:
    path = Path(filepath)
    lines = path.read_text().splitlines(keepends=True)
    insert_at = _insertion_point(lines)
    lines[insert_at:insert_at] = [f'{d}\n' for d in sorted(directives)]
    path.write_text(''.join(lines))


def fix_iwyu(cpp_files: list[str], config_path: str) -> Result:
    """Run cpplint IWYU-only and auto-insert any missing #include directives."""
    if not cpp_files:
        return Result(name='iwyu-fix', passed=True, skipped=True)
    cmd = [tool('cpplint'), f'--config={config_path}', '--filter=-all,+build/include_what_you_use'] + cpp_files
    proc = subprocess.run(cmd, capture_output=True, text=True)
    missing = _parse_iwyu_output(proc.stdout + proc.stderr)
    if not missing:
        return Result(name='iwyu-fix', passed=True, cmd=cmd)
    for filepath, directives in missing.items():
        _insert_includes(filepath, directives)
    modified = sorted(missing.keys())
    return Result(
        name='iwyu-fix',
        passed=False,
        output=f'Inserted missing includes in: {", ".join(modified)}\n(files have been modified — please re-stage and recommit)',
        cmd=cmd,
    )


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


@check_group
class CppGroup(CheckerGroup):
    name = 'cpp'

    def run(self, args: argparse.Namespace) -> list[Result]:
        # cpplint walks up the directory tree for its config; use a per-process
        # temp file so parallel invocations don't race on a shared filename.
        fd, tmp_path_str = tempfile.mkstemp(dir=Path.cwd(), prefix='.cpplint_', suffix='.cfg')
        os.close(fd)
        tmp_path = Path(tmp_path_str)
        try:
            shutil.copy2(CONFIG_DIR / '.cpplint.cfg', tmp_path)
            return [
                fix_iwyu(args.files, tmp_path.name),
                run_clang_format(args.files),
                self._check('cpplint', [f'--config={tmp_path.name}', '--quiet', '--output=sed'], args.files),
            ]
        finally:
            tmp_path.unlink(missing_ok=True)
