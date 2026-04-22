# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
import argparse
import shutil
from pathlib import Path

from polymath_code_standard.checker import CONFIG_DIR, CheckerGroup, Result, check_group


@check_group
class PythonGroup(CheckerGroup):
    name = 'python'

    def run(self, args: argparse.Namespace) -> list[Result]:
        # Allow subdirectories to override Ruff config by walking up from cwd.
        # The default config must be copied to the repo root since ruff doesn't
        # accept an absolute config path.
        shutil.copy2(CONFIG_DIR / 'ruff.toml', Path.cwd() / '.ruff.toml')
        return [
            self._check('check-ast', [], args.files),
            self._check('ruff', ['format'], args.files, name='ruff-format'),
            self._check('ruff', ['check', '--fix'], args.files, name='ruff-lint'),
        ]
