# Copyright (c) 2026-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
import argparse

from polymath_code_standard.checker import CheckerGroup, Result, check_group


@check_group
class DockerGroup(CheckerGroup):
    name = 'docker'

    def run(self, args: argparse.Namespace) -> list[Result]:
        return [self._check('hadolint', ['--ignore', 'SC1091', '--ignore', 'DL3006', '--ignore', 'DL3008'], args.files)]
