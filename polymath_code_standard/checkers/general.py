# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
import argparse
import subprocess

from polymath_code_standard.checker import CheckerGroup, Result, check_group, filter_files


@check_group
class GeneralGroup(CheckerGroup):
    name = 'general'

    def run(self, args: argparse.Namespace) -> list[Result]:
        text = filter_files(args.files, frozenset({'text'}))
        symlinks = filter_files(args.files, frozenset({'symlink'}))
        return [
            self._check('check-added-large-files', [], args.files),
            self._check('check-case-conflict', [], args.files),
            self._check('check-merge-conflict', [], text),
            self._check('check-shebang-scripts-are-executable', [], text),
            self._check('check-symlinks', [], symlinks),
            self.run_forbid_submodules(),
            self._check('end-of-file-fixer', [], text),
            self._check('mixed-line-ending', [], text),
            self._check('trailing-whitespace-fixer', [], text),
        ]

    @staticmethod
    def run_forbid_submodules() -> Result:
        """Detect git submodules by checking for mode 160000 in the index."""
        cmd = ['git', 'ls-files', '--stage']
        proc = subprocess.run(cmd, capture_output=True, text=True)
        submodules = [line.split('\t', 1)[-1] for line in proc.stdout.splitlines() if line.startswith('160000')]
        if submodules:
            listing = '\n'.join(f'  {s}' for s in submodules)
            return Result(
                name='forbid-submodules',
                passed=False,
                output=f'Submodule(s) detected — submodules are not allowed:\n{listing}',
                cmd=cmd,
            )
        return Result(name='forbid-submodules', passed=True, cmd=cmd)
