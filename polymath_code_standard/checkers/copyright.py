# Copyright (c) 2026-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
import argparse
import datetime
import os
import re
import tempfile
from pathlib import Path

from polymath_code_standard.checker import CheckerGroup, Result, check_group, filter_files
from polymath_code_standard.licenses import PROPRIETARY, get_license_full_text, get_license_header


@check_group
class CopyrightGroup(CheckerGroup):
    name = 'copyright'

    def register_args(self, subparser: argparse.ArgumentParser) -> None:
        super().register_args(subparser)
        subparser.add_argument(
            '--license',
            dest='license_id',
            required=True,
            metavar='SPDX_ID',
            help="SPDX license ID (e.g. MIT, Apache-2.0) or 'proprietary'",
        )
        subparser.add_argument(
            '--copyright-org',
            required=True,
            metavar='ORG',
            help='Organization name for the copyright line',
        )
        subparser.add_argument(
            '--copyright-year',
            default=str(datetime.date.today().year),
            metavar='YEAR',
            help='Copyright start year (default: current year)',
        )
        subparser.add_argument(
            '--reuse-style',
            action='store_true',
            help='Force REUSE-style 2-line copyright headers, even when a standard block is available',
        )
        subparser.add_argument(
            '--relicense',
            action='store_true',
            help='Strip any existing leading comment block before inserting the new header (for relicensing)',
        )

    def run(self, args: argparse.Namespace) -> list[Result]:
        header_text = get_license_header(
            args.license_id, args.copyright_year, args.copyright_org, reuse_style_header=args.reuse_style
        )
        py_cmake_shell = filter_files(args.files, frozenset({'python', 'cmake', 'shell'}))
        cpp = filter_files(args.files, frozenset({'c', 'c++'}))

        if args.relicense:
            for f in py_cmake_shell:
                self._strip_leading_comment_block(f, '#')
            for f in cpp:
                self._strip_leading_comment_block(f, '//')

        fd, license_filepath = tempfile.mkstemp(suffix='.txt', prefix='polymath_license_')
        try:
            os.write(fd, header_text.encode('utf-8'))
            os.close(fd)
            results = [
                self._check(
                    'polymath_copyright_header',
                    [
                        '--license-filepath',
                        license_filepath,
                        '--comment-style',
                        '#',
                        '--allow-past-years',
                        '--no-extra-eol',
                    ],
                    py_cmake_shell,
                    name='copyright (py/cmake/shell)',
                ),
                self._check(
                    'polymath_copyright_header',
                    ['--license-filepath', license_filepath, '--comment-style', '//', '--allow-past-years'],
                    cpp,
                    name='copyright (cpp)',
                ),
            ]
        finally:
            try:
                os.unlink(license_filepath)
            except OSError:
                pass

        results.append(self._check_license_file(args.license_id, args.copyright_year, args.copyright_org))
        return results

    @staticmethod
    def _strip_leading_comment_block(filepath: str, comment_prefix: str) -> None:
        """Remove the leading comment block from a file, preserving shebang/coding lines.

        Strips all contiguous comment lines (matching comment_prefix) starting after
        any shebang or encoding declaration, plus one following blank line.  Used so
        that a subsequent insert_license run can write a fresh header in their place.
        """
        path = Path(filepath)
        lines = path.read_text(encoding='utf-8', errors='replace').splitlines(keepends=True)
        idx = 0
        if lines and lines[0].startswith('#!'):
            idx = 1
        if idx < len(lines) and re.match(r'#\s*-\*-\s*coding', lines[idx]):
            idx += 1
        block_start = idx
        while idx < len(lines) and lines[idx].rstrip('\r\n').lstrip().startswith(comment_prefix):
            idx += 1
        if idx < len(lines) and not lines[idx].strip():
            idx += 1
        if idx > block_start:
            path.write_text(''.join(lines[:block_start] + lines[idx:]), encoding='utf-8')

    @staticmethod
    def _check_license_file(license_id: str, year: str, org: str) -> Result:
        if license_id == PROPRIETARY:
            return Result(name='LICENSE file', passed=True, skipped=True)
        license_file = Path.cwd() / 'LICENSE'
        try:
            expected = get_license_full_text(license_id, year, org)
        except Exception as exc:
            return Result(name='LICENSE file', passed=False, output=str(exc))
        current = license_file.read_text(encoding='utf-8') if license_file.exists() else None
        if current == expected:
            return Result(name='LICENSE file', passed=True)
        license_file.write_text(expected, encoding='utf-8')
        action = 'updated' if current is not None else 'created'
        return Result(
            name='LICENSE file',
            passed=False,
            output=f'LICENSE file {action} — please re-stage and recommit',
        )
