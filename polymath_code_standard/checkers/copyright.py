# Copyright (c) 2026-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
import argparse
import datetime
import os
import tempfile

from polymath_code_standard.checker import CheckerGroup, Result, check_group, filter_files
from polymath_code_standard.licenses import get_license_header


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

    def run(self, args: argparse.Namespace) -> list[Result]:
        header_text = get_license_header(args.license_id, args.copyright_year, args.copyright_org)
        py_cmake_shell = filter_files(args.files, frozenset({'python', 'cmake', 'shell'}))
        cpp = filter_files(args.files, frozenset({'c', 'c++'}))

        fd, license_filepath = tempfile.mkstemp(suffix='.txt', prefix='polymath_license_')
        try:
            os.write(fd, header_text.encode('utf-8'))
            os.close(fd)
            return [
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
