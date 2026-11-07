# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
import argparse
import subprocess

from polymath_code_standard.checker import CheckerGroup, Result, check_group, filter_files

LFS_POINTER_PREFIX = b'version https://git-lfs'


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
            self.run_lfs_pointers(args.files),
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

    @staticmethod
    def run_lfs_pointers(files: list[str]) -> Result:
        """Require staged files that .gitattributes assigns `filter=lfs` to be staged as Git LFS pointers.

        Reads the index through git, so it works without git-lfs installed.
        Files that are not staged are skipped.
        """
        name = 'lfs-pointers'
        if not files:
            return Result(name=name, passed=True, skipped=True)
        attrs = subprocess.run(
            ['git', 'check-attr', '-z', '--stdin', 'filter'],
            input=''.join(f'{f}\0' for f in files),
            capture_output=True,
            text=True,
        )
        if attrs.returncode != 0:
            return Result(name=name, passed=False, output=attrs.stderr.strip())
        # Each record is path, attribute and value.
        records = attrs.stdout.split('\0')
        lfs = [path for path, value in zip(records[0::3], records[2::3]) if value == 'lfs']
        if not lfs:
            return Result(name=name, passed=True)
        staged = subprocess.run(['git', 'ls-files', '--stage', '-z', '--', *lfs], capture_output=True, text=True)
        plain = []
        for entry in filter(None, staged.stdout.split('\0')):
            info, path = entry.split('\t', 1)
            blob = subprocess.run(['git', 'cat-file', 'blob', info.split()[1]], capture_output=True).stdout
            if not blob.startswith(LFS_POINTER_PREFIX):
                plain.append(path)
        if not plain:
            return Result(name=name, passed=True)
        listing = '\n'.join(f'  {p}' for p in plain)
        return Result(
            name=name,
            passed=False,
            output=(
                f'These files belong in Git LFS, per .gitattributes, but are staged as plain files:\n{listing}\n'
                'Install git-lfs, enable it with `git lfs install`, and restage them:\n'
                f'  git add --renormalize {" ".join(plain)}'
            ),
        )
