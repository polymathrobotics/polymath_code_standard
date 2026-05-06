# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for wildcard copyright org matching and sentinel insertion in insert_license."""

from polymath_code_standard.insert_license import (
    COPYRIGHT_ORG_SENTINEL,
    LicenseInfo,
    _is_copyright_line,
    _license_line_matches,
    _normalize_copyright_line,
    any_copyright_line_found,
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

    def test_reuse_spdx_hash_style(self):
        assert _is_copyright_line('# SPDX-FileCopyrightText: 2026 Acme Corp')

    def test_reuse_spdx_slash_style(self):
        assert _is_copyright_line('// SPDX-FileCopyrightText: 2026 Acme Corp')

    def test_reuse_spdx_license_identifier_is_not_copyright(self):
        assert not _is_copyright_line('# SPDX-License-Identifier: Apache-2.0')


# ---------------------------------------------------------------------------
# _normalize_copyright_line
# ---------------------------------------------------------------------------


class TestNormalizeCopyrightLine:
    def test_strips_c_symbol(self):
        assert _normalize_copyright_line('# Copyright (c) 2026 Acme Corp') == '# Copyright 2026 Acme Corp'

    def test_strips_c_symbol_uppercase(self):
        assert _normalize_copyright_line('# Copyright (C) 2026 Acme Corp') == '# Copyright 2026 Acme Corp'

    def test_strips_present_suffix(self):
        assert _normalize_copyright_line('# Copyright 2025-present Acme Corp') == '# Copyright 2025 Acme Corp'

    def test_strips_all_rights_reserved(self):
        assert (
            _normalize_copyright_line('# Copyright 2026 Acme Corp. All rights reserved') == '# Copyright 2026 Acme Corp'
        )

    def test_strips_all_combined(self):
        result = _normalize_copyright_line('// Copyright (c) 2025-present Acme Corp. All rights reserved')
        assert result == '// Copyright 2025 Acme Corp'

    def test_leaves_plain_line_unchanged(self):
        assert _normalize_copyright_line('# Copyright 2026 Acme Corp') == '# Copyright 2026 Acme Corp'


# ---------------------------------------------------------------------------
# _license_line_matches — copyright decoration tolerance (no wildcard needed)
# ---------------------------------------------------------------------------


class TestLicenseLineMatchesDecoration:
    def test_c_symbol_matches_plain_template(self):
        assert _license_line_matches(
            '// Copyright 2026 Acme Corp',
            '// Copyright (c) 2026 Acme Corp',
            match_years_strictly=False,
        )

    def test_present_suffix_matches_plain_template(self):
        assert _license_line_matches(
            '// Copyright 2026 Acme Corp',
            '// Copyright 2025-present Acme Corp',
            match_years_strictly=False,
        )

    def test_all_rights_reserved_matches_plain_template(self):
        assert _license_line_matches(
            '// Copyright 2026 Acme Corp',
            '// Copyright 2026 Acme Corp. All rights reserved',
            match_years_strictly=False,
        )

    def test_all_decorations_combined(self):
        assert _license_line_matches(
            '// Copyright 2026 Acme Corp',
            '// Copyright (c) 2025-present Acme Corp. All rights reserved',
            match_years_strictly=False,
        )

    def test_wrong_org_still_fails(self):
        assert not _license_line_matches(
            '// Copyright 2026 Acme Corp',
            '// Copyright (c) 2025-present Other Corp. All rights reserved',
            match_years_strictly=False,
        )


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
# any_copyright_line_found
# ---------------------------------------------------------------------------


class TestAnyCopyrightLineFound:
    def test_finds_standard_copyright(self):
        content = ['# Copyright (c) 2025-present Acme Corp. All rights reserved\n', 'import foo\n']
        assert any_copyright_line_found(content, top_lines_count=5)

    def test_finds_cpp_style(self):
        content = ['// Copyright (c) 2025-present Acme Corp. All rights reserved\n', 'int x;\n']
        assert any_copyright_line_found(content, top_lines_count=5)

    def test_not_found_in_plain_code(self):
        content = ['import foo\n', 'x = 1\n']
        assert not any_copyright_line_found(content, top_lines_count=5)

    def test_sentinel_line_also_counts(self):
        content = [f'# Copyright 2026 {COPYRIGHT_ORG_SENTINEL}\n']
        assert any_copyright_line_found(content, top_lines_count=5)

    def test_beyond_top_lines_not_found(self):
        content = ['import foo\n', 'import bar\n', '# Copyright 2026 Acme\n']
        assert not any_copyright_line_found(content, top_lines_count=2)


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

    def test_reuse_style_replaced_org_not_duplicated(self, tmp_path):
        """After replacing the sentinel in a REUSE-style header, re-running should not insert a duplicate."""
        reuse_license_text = (
            f'SPDX-FileCopyrightText: 2026 {COPYRIGHT_ORG_SENTINEL}\nSPDX-License-Identifier: Apache-2.0\n'
        )
        lf = tmp_path / 'license.txt'
        lf.write_text(reuse_license_text, encoding='utf-8')

        # File already has the sentinel replaced with a real org
        src = self._write(
            tmp_path,
            'f.py',
            '# SPDX-FileCopyrightText: 2026 My Org\n# SPDX-License-Identifier: Apache-2.0\nimport foo\n',
        )
        original = src.read_text()
        ret = main([
            '--license-filepath',
            str(lf),
            '--comment-style',
            '#',
            '--allow-past-years',
            '--no-extra-eol',
            '--wildcard-copyright-org',
            str(src),
        ])
        assert ret == 0
        assert src.read_text() == original

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

    def test_single_line_copyright_passes_with_wildcard(self, tmp_path):
        # Existing repos often have a condensed copyright line without the full license block
        content = '// Copyright (c) 2025-present Polymath Robotics, Inc. All rights reserved\nint x = 0;\n'
        src = self._write(tmp_path, 'f.cpp', content)
        lf = self._license_file(tmp_path)
        ret = main([
            '--license-filepath',
            lf,
            '--comment-style',
            '//',
            '--allow-past-years',
            '--wildcard-copyright-org',
            str(src),
        ])
        assert ret == 0
        assert src.read_text() == content  # file untouched

    def test_single_line_copyright_with_sentinel_still_fails(self, tmp_path):
        content = f'// Copyright (c) 2025-present {COPYRIGHT_ORG_SENTINEL}\nint x = 0;\n'
        src = self._write(tmp_path, 'f.cpp', content)
        lf = self._license_file(tmp_path)
        ret = main([
            '--license-filepath',
            lf,
            '--comment-style',
            '//',
            '--allow-past-years',
            '--wildcard-copyright-org',
            str(src),
        ])
        assert ret == 1
        assert src.read_text() == content  # file still untouched (sentinel check doesn't modify)

    def test_no_copyright_at_all_inserts_sentinel(self, tmp_path):
        content = 'int x = 0;\n'
        src = self._write(tmp_path, 'f.cpp', content)
        lf = self._license_file(tmp_path)
        ret = main([
            '--license-filepath',
            lf,
            '--comment-style',
            '//',
            '--allow-past-years',
            '--wildcard-copyright-org',
            str(src),
        ])
        assert ret == 1
        assert COPYRIGHT_ORG_SENTINEL in src.read_text()
