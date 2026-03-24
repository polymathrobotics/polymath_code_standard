# Copyright (c) 2025-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
import functools
import importlib.resources
from dataclasses import dataclass

from identify.identify import tags_from_path


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


# Path to resource files which are config inputs to the various hooks
CONFIG_DIR = importlib.resources.files('polymath_code_standard') / 'config'


@functools.cache
def _file_tags(path: str) -> frozenset[str]:
    return frozenset(tags_from_path(path))


def filter_files(files: list[str], types: frozenset[str]) -> list[str]:
    """Return files that have at least one of the given identify type tags."""
    return [f for f in files if _file_tags(f) & types]
