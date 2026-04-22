# Copyright (c) 2026-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
import argparse

from polymath_code_standard.checker import CheckerGroup, Result, check_group


@check_group
class CMakeGroup(CheckerGroup):
    name = 'cmake'

    def run(self, args: argparse.Namespace) -> list[Result]:
        return [self._check('cmakelint', ['--linelength=140'], args.files)]
