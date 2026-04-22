# Copyright (c) 2026-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from polymath_code_standard.checker import CONFIG_DIR, CheckerGroup, Result, check_group


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
                run_clang_format(args.files),
                self._check('cpplint', [f'--config={tmp_path.name}', '--quiet', '--output=sed'], args.files),
            ]
        finally:
            tmp_path.unlink(missing_ok=True)
