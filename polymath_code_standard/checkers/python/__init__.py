# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
import argparse
import importlib.resources
import os
import shutil
import tempfile
from pathlib import Path

from polymath_code_standard.checker import CheckerGroup, Result, check_group

# Config files bundled alongside this checker
CONFIG_DIR = importlib.resources.files(__package__)


@check_group
class PythonGroup(CheckerGroup):
    name = 'python'

    def run(self, args: argparse.Namespace) -> list[Result]:
        # Allow subdirectories to override Ruff config by walking up from cwd.
        # The default config must be copied to the repo root since ruff doesn't
        # accept an absolute config path.
        # Write via a temp file + os.replace so concurrent pre-commit workers
        # never observe a partially-written .ruff.toml.
        target = Path.cwd() / '.ruff.toml'
        with tempfile.NamedTemporaryFile(dir=Path.cwd(), delete=False, suffix='.tmp') as tmp:
            tmp_path = tmp.name
        shutil.copy2(CONFIG_DIR / 'ruff.toml', tmp_path)
        os.replace(tmp_path, target)
        return [
            self._check('check-ast', [], args.files),
            self._check('ruff', ['format'], args.files, name='ruff-format'),
            self._check('ruff', ['check', '--fix'], args.files, name='ruff-lint'),
        ]
