# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
import argparse

from polymath_code_standard.checker import CheckerGroup, Result, check_group


@check_group
class ShellGroup(CheckerGroup):
    name = 'shell'

    def run(self, args: argparse.Namespace) -> list[Result]:
        return [self._check('shellcheck', ['-e', 'SC1091'], args.files)]
