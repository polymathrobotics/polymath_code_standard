# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
import argparse

from polymath_code_standard.checker import CONFIG_DIR, CheckerGroup, Result, check_group


@check_group
class AnsibleGroup(CheckerGroup):
    name = 'ansible'

    def run(self, args: argparse.Namespace) -> list[Result]:
        return [
            self._check(
                'python3',
                ['-m', 'ansiblelint', '-v', '--force-color', '-c', CONFIG_DIR / 'ansible-lint.yml'],
                args.files,
                name='ansible-lint',
                env={'ANSIBLE_COLLECTIONS_PATH': 'ansible/collections'},
            )
        ]
