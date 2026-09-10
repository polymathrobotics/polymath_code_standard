# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Install the bundled Node tooling into this virtualenv and locate it.

Usable on its own:

    >>> from polymath_code_standard.checkers.web._node import ensure_node_modules, node_tool
    >>> node_dir = ensure_node_modules()
    >>> node_tool(node_dir, 'eslint')
"""

import fcntl
import hashlib
import importlib.resources
import os
import shutil
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from polymath_code_standard.checker import Result, run, tool

# Config files bundled alongside this checker
CONFIG_DIR = importlib.resources.files(__package__)

# Files copied into the install directory.
# Node resolves the configs' bare imports and extends from the config file's directory, so they sit
# beside node_modules.
BUNDLE = ('package.json', 'package-lock.json', 'eslint.config.mjs', 'prettier.config.mjs', 'stylelint.config.mjs')

# Inside the hook's virtualenv, so one install per hook revision.
INSTALL_DIR = Path(sys.prefix) / 'polymath-node'

STAMP_NAME = 'bundle-sha256'


def bundle_digest() -> str:
    """Return the sha256 over the bundled manifest and tool configs."""
    digest = hashlib.sha256()
    for name in BUNDLE:
        digest.update((CONFIG_DIR / name).read_bytes())
    return digest.hexdigest()


def node_tool(install_dir: Path, name: str) -> str:
    """Return the absolute path to an installed Node console script."""
    return str(install_dir / 'node_modules' / '.bin' / name)


def node_config(install_dir: Path, name: str) -> str:
    """Return the absolute path to an installed tool config."""
    return str(install_dir / name)


def node_env() -> dict:
    """Return the environment the installed console scripts need.

    They are `#!/usr/bin/env node` scripts, so they need `node` on PATH.
    """
    venv_bin = Path(sys.executable).parent
    return {'PATH': os.pathsep.join([str(venv_bin), os.environ.get('PATH', '')])}


def ensure_node_modules(install_dir: Path = INSTALL_DIR) -> Path | Result:
    """Install the bundled Node tooling into install_dir and return that directory.

    Reinstalls only when the bundle digest changes.
    Concurrent callers serialize on a lock file beside install_dir.
    Returns a failed Result carrying npm's output when the install fails.
    """
    digest = bundle_digest()
    stamp = install_dir / STAMP_NAME
    if _is_stamped(stamp, digest):
        return install_dir

    install_dir.mkdir(parents=True, exist_ok=True)
    with _exclusive(install_dir.with_name(f'{install_dir.name}.lock')):
        if _is_stamped(stamp, digest):
            return install_dir
        for name in BUNDLE:
            shutil.copy2(CONFIG_DIR / name, install_dir / name)
        result = run(
            'npm',
            [tool('npm'), 'ci', '--prefix', str(install_dir), '--no-audit', '--no-fund', '--loglevel=error'],
        )
        if not result.passed:
            return result
        stamp.write_text(f'{digest}\n')
    return install_dir


def _is_stamped(stamp: Path, digest: str) -> bool:
    return stamp.is_file() and stamp.read_text().strip() == digest


@contextmanager
def _exclusive(lock_path: Path) -> Iterator[None]:
    """Hold an exclusive advisory lock on lock_path for the duration of the block."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('w') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
