# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
import argparse

from polymath_code_standard.checker import CheckerGroup, Result, check_group
from polymath_code_standard.executor_lint import check_executor_threads


@check_group
class RosGroup(CheckerGroup):
    name = 'ros'

    def run(self, args: argparse.Namespace) -> list[Result]:
        return [check_executor_threads(args.files)]
