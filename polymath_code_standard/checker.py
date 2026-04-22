# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
import argparse
import functools
import importlib.resources
import os
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from identify.identify import tags_from_path

# Path to resource files which are config inputs to the various hooks
CONFIG_DIR = importlib.resources.files('polymath_code_standard') / 'config'


@functools.cache
def _file_tags(path: str) -> frozenset[str]:
    return frozenset(tags_from_path(path))


def filter_files(files: list[str], types: frozenset[str]) -> list[str]:
    """Return files that have at least one of the given identify type tags."""
    return [f for f in files if _file_tags(f) & types]


@dataclass
class Result:
    """Outcome of a single invocation of a tool."""

    name: str
    passed: bool
    skipped: bool = False
    output: str = ''
    cmd: list[str] | None = None

    def print(self) -> None:
        if self.output and not self.passed:
            for line in self.output.splitlines():
                print(f'  [{self.name}] {line}')


def tool(name: str) -> str:
    """Return the absolute path to a console script in this venv."""
    return str(Path(sys.executable).parent / name)


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


class CheckerGroup(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    def register_args(self, subparser: argparse.ArgumentParser) -> None:
        """Register subparser arguments. Override to add group-specific options."""
        subparser.add_argument('files', nargs='*', help='Staged files passed by pre-commit')

    @abstractmethod
    def run(self, args: argparse.Namespace) -> list[Result]: ...

    @classmethod
    def _check(
        cls, tool_name: str, args: list[str], files: list[str] | None, name: str = None, env: dict | None = None
    ) -> Result:
        return run(name or tool_name, [tool(tool_name)] + args, files, env=env)


_GROUPS: list[CheckerGroup] = []


def check_group(cls: type[CheckerGroup]) -> type[CheckerGroup]:
    """Decorator that registers a CheckerGroup with the global group list."""
    _GROUPS.append(cls())
    return cls
