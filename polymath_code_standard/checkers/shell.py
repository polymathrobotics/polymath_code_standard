# Copyright (c) 2026-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
import argparse

from polymath_code_standard.checker import CheckerGroup, Result, check_group


@check_group
class ShellGroup(CheckerGroup):
    name = 'shell'

    def run(self, args: argparse.Namespace) -> list[Result]:
        return [self._check('shellcheck', ['-e', 'SC1091'], args.files)]
