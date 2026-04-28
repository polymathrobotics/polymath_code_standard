# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for wildcard copyright org matching and sentinel insertion in insert_license."""

from polymath_code_standard.insert_license import (
    COPYRIGHT_ORG_SENTINEL,
    LicenseInfo,
    _is_copyright_line,
    _license_line_matches,
    copyright_sentinel_found,
    find_license_header_index,
    main,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_APACHE_PREFIXED = [
    '# Copyright 2026 Polymath Robotics, Inc.\n',
    '#\n',
    '# Licensed under the Apache License, Version 2.0 (the "License");\n',
    '# you may not use this file except in compliance with the License.\n',
    '# You may obtain a copy of the License at\n',
    '#\n',
    '# http://www.apache.org/licenses/LICENSE-2.0\n',
    '#\n',
    '# Unless required by applicable law or agreed to in writing, software\n',
    '# distributed under the License is distributed on an "AS IS" BASIS,\n',
    '# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n',
    '# See the License for the specific language governing permissions and\n',
    '# limitations under the License.\n',
]

_LICENSE_INFO = LicenseInfo(
    prefixed_license=_APACHE_PREFIXED,
    plain_license=[line.lstrip('# ') for line in _APACHE_PREFIXED],
    eol='',
    comment_start=None,
    comment_prefix='#',
    comment_end=None,
    num_extra_lines=0,
)


def _file_with_header(org: str) -> list[str]:
    lines = list(_APACHE_PREFIXED)
    lines[0] = f'# Copyright 2024 {org}\n'
    return lines + ['import foo\n']


# ---------------------------------------------------------------------------
# _is_copyright_line
# ---------------------------------------------------------------------------


class TestIsCopyrightLine:
    def test_hash_style(self):
        assert _is_copyright_line('# Copyright 2026 Acme Corp')

    def test_slash_style(self):
        assert _is_copyright_line('// Copyright 2026 Acme Corp')

    def test_plain(self):
        assert _is_copyright_line('Copyright 2026 Acme Corp')

    def test_non_copyright(self):
        assert not _is_copyright_line('# Licensed under the Apache License')

    def test_blank_comment(self):
        assert not _is_copyright_line('#')


# ---------------------------------------------------------------------------
# _license_line_matches — wildcard_copyright_org
# ---------------------------------------------------------------------------


class TestLicenseLineMatchesWildcard:
    def test_different_org_matches_with_wildcard(self):
        assert _license_line_matches(
            '# Copyright 2026 Polymath Robotics, Inc.',
            '# Copyright 2023 Some Other Corp.',
            match_years_strictly=False,
            wildcard_copyright_org=True,
        )

    def test_different_org_fails_without_wildcard(self):
        assert not _license_line_matches(
            '# Copyright 2026 Polymath Robotics, Inc.',
            '# Copyright 2026 Some Other Corp.',
            match_years_strictly=False,
            wildcard_copyright_org=False,
        )

    def test_non_copyright_line_still_requires_exact_match(self):
        assert not _license_line_matches(
            '# Licensed under the Apache License, Version 2.0',
            '# Licensed under the MIT License',
            match_years_strictly=False,
            wildcard_copyright_org=True,
        )

    def test_non_copyright_line_matches_exactly(self):
        assert _license_line_matches(
            '# Licensed under the Apache License, Version 2.0',
            '# Licensed under the Apache License, Version 2.0',
            match_years_strictly=False,
            wildcard_copyright_org=True,
        )


# ---------------------------------------------------------------------------
# copyright_sentinel_found
# ---------------------------------------------------------------------------


class TestCopyrightSentinelFound:
    def test_detects_sentinel(self):
        content = [f'# Copyright 2026 {COPYRIGHT_ORG_SENTINEL}\n', '#\n', 'import foo\n']
        assert copyright_sentinel_found(content, top_lines_count=5)

    def test_no_sentinel(self):
        content = ['# Copyright 2026 Acme Corp\n', '#\n', 'import foo\n']
        assert not copyright_sentinel_found(content, top_lines_count=5)

    def test_sentinel_beyond_top_lines_not_detected(self):
        content = ['import foo\n', 'import bar\n', f'# {COPYRIGHT_ORG_SENTINEL}\n']
        assert not copyright_sentinel_found(content, top_lines_count=2)


# ---------------------------------------------------------------------------
# find_license_header_index — wildcard matching
# ---------------------------------------------------------------------------


class TestFindLicenseHeaderIndexWildcard:
    def test_matches_different_org_with_wildcard(self):
        content = _file_with_header('Contributor Corp.')
        idx = find_license_header_index(
            content, _LICENSE_INFO, top_lines_count=5, match_years_strictly=False, wildcard_copyright_org=True
        )
        assert idx == 0

    def test_rejects_different_org_without_wildcard(self):
        content = _file_with_header('Contributor Corp.')
        idx = find_license_header_index(
            content, _LICENSE_INFO, top_lines_count=5, match_years_strictly=False, wildcard_copyright_org=False
        )
        assert idx is None

    def test_matches_same_org_with_wildcard(self):
        content = _file_with_header('Polymath Robotics, Inc.')
        idx = find_license_header_index(
            content, _LICENSE_INFO, top_lines_count=5, match_years_strictly=False, wildcard_copyright_org=True
        )
        assert idx == 0

    def test_still_requires_correct_license_boilerplate(self):
        content = ['# Copyright 2026 Acme Corp\n', '# MIT License\n', 'import foo\n']
        idx = find_license_header_index(
            content, _LICENSE_INFO, top_lines_count=5, match_years_strictly=False, wildcard_copyright_org=True
        )
        assert idx is None


# ---------------------------------------------------------------------------
# End-to-end: main() with wildcard flag
# ---------------------------------------------------------------------------


class TestMainWildcard:
    def _write(self, tmp_path, name, content):
        p = tmp_path / name
        p.write_text(content, encoding='utf-8')
        return p

    def _license_file(self, tmp_path, org=COPYRIGHT_ORG_SENTINEL):
        lines = list(_APACHE_PREFIXED)
        lines[0] = f'# Copyright 2026 {org}\n'
        p = tmp_path / 'license.txt'
        p.write_text(''.join(line.lstrip('# ') for line in lines), encoding='utf-8')
        return str(p)

    def test_sentinel_in_file_fails(self, tmp_path):
        src = self._write(tmp_path, 'f.py', f'# Copyright 2026 {COPYRIGHT_ORG_SENTINEL}\n#\nimport foo\n')
        lf = self._license_file(tmp_path)
        ret = main([
            '--license-filepath',
            lf,
            '--comment-style',
            '#',
            '--allow-past-years',
            '--no-extra-eol',
            '--wildcard-copyright-org',
            str(src),
        ])
        assert ret == 1

    def test_any_org_passes_with_wildcard(self, tmp_path):
        src = self._write(tmp_path, 'f.py', ''.join(_file_with_header('Contributor Corp.')))
        lf = self._license_file(tmp_path, org='Polymath Robotics, Inc.')
        ret = main([
            '--license-filepath',
            lf,
            '--comment-style',
            '#',
            '--allow-past-years',
            '--no-extra-eol',
            '--wildcard-copyright-org',
            str(src),
        ])
        assert ret == 0

    def test_no_header_inserts_sentinel(self, tmp_path):
        src = self._write(tmp_path, 'f.py', 'import foo\n')
        lf = self._license_file(tmp_path)
        ret = main([
            '--license-filepath',
            lf,
            '--comment-style',
            '#',
            '--allow-past-years',
            '--no-extra-eol',
            '--wildcard-copyright-org',
            str(src),
        ])
        assert ret == 1
        assert COPYRIGHT_ORG_SENTINEL in src.read_text()

    def test_without_wildcard_rejects_different_org(self, tmp_path):
        src = self._write(tmp_path, 'f.py', ''.join(_file_with_header('Contributor Corp.')))
        lf = self._license_file(tmp_path, org='Polymath Robotics, Inc.')
        original = src.read_text()
        ret = main([
            '--license-filepath',
            lf,
            '--comment-style',
            '#',
            '--allow-past-years',
            '--no-extra-eol',
            str(src),
        ])
        assert ret == 1
        assert src.read_text() != original
