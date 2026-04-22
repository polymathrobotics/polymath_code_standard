# Copyright (c) 2025-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""Polymath Code Standard pre-commit hook runner.

Invoked as: polymath_code_standard <group> [options] [files ...]

Files are pre-filtered by pre-commit's native type detection before arrival.
"""

from __future__ import annotations

import argparse
import importlib
import pkgutil
from pathlib import Path

from .checker import _GROUPS, CheckerGroup

for _mod in pkgutil.iter_modules([str(Path(__file__).parent / 'checkers')]):
    importlib.import_module(f'.checkers.{_mod.name}', package=__package__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='group', required=True, metavar='GROUP')

    group_map: dict[str, CheckerGroup] = {}
    for group in _GROUPS:
        sub = subs.add_parser(group.name, help=f'Run {group.name} checks')
        group.register_args(sub)
        group_map[group.name] = group

    args = parser.parse_args(argv)
    results = group_map[args.group].run(args)

    failed = [r for r in results if not r.passed and not r.skipped]
    for result in failed:
        result.print()
    return 1 if failed else 0
