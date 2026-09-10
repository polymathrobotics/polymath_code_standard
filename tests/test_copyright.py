# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for CopyrightGroup: LICENSE file management, leading comment stripping, and header insertion."""

import argparse
from unittest.mock import patch

import pytest

from polymath_code_standard.checker import Result
from polymath_code_standard.checkers.copyright import CopyrightGroup

_check = CopyrightGroup._check_license_file

_MOCK_LICENSE_TEXT = 'MIT License\n\nCopyright (c) 2024 Test Corp\n'


def _mock_full_text(text=_MOCK_LICENSE_TEXT):
    return patch('polymath_code_standard.checkers.copyright.get_license_full_text', return_value=text)


class TestCheckLicenseFile:
    def test_proprietary_is_skipped(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = _check('proprietary', '2024', 'Test Corp')
        assert result.skipped
        assert result.passed

    def test_proprietary_does_not_create_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _check('proprietary', '2024', 'Test Corp')
        assert not (tmp_path / 'LICENSE').exists()

    def test_creates_missing_license_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with _mock_full_text():
            _check('MIT', '2024', 'Test Corp')
        assert (tmp_path / 'LICENSE').read_text() == _MOCK_LICENSE_TEXT

    def test_returns_failed_when_file_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with _mock_full_text():
            result = _check('MIT', '2024', 'Test Corp')
        assert not result.passed
        assert 'created' in result.output

    def test_passes_when_license_file_correct(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / 'LICENSE').write_text(_MOCK_LICENSE_TEXT)
        with _mock_full_text():
            result = _check('MIT', '2024', 'Test Corp')
        assert result.passed
        assert not result.skipped

    def test_updates_stale_license_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / 'LICENSE').write_text('old content\n')
        with _mock_full_text():
            _check('MIT', '2024', 'Test Corp')
        assert (tmp_path / 'LICENSE').read_text() == _MOCK_LICENSE_TEXT

    def test_returns_failed_when_file_updated(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / 'LICENSE').write_text('old content\n')
        with _mock_full_text():
            result = _check('MIT', '2024', 'Test Corp')
        assert not result.passed
        assert 'updated' in result.output

    def test_fetch_error_returns_failed(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch(
            'polymath_code_standard.checkers.copyright.get_license_full_text',
            side_effect=ValueError('Unknown SPDX license ID: BOGUS'),
        ):
            result = _check('BOGUS', '2024', 'Test Corp')
        assert not result.passed
        assert 'BOGUS' in result.output


class TestWildcardOrgSkipsLicenseFile:
    def test_license_file_not_modified_with_wildcard_org(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        license_file = tmp_path / 'LICENSE'
        original_content = 'Apache License 2.0\n\nCopyright Acme Corp\n'
        license_file.write_text(original_content)

        args = argparse.Namespace(
            license_id='Apache-2.0',
            copyright_year='2026',
            copyright_org=None,
            wildcard_copyright_org=True,
            reuse_style=True,
            relicense=False,
            files=[],
        )
        with patch.object(CopyrightGroup, '_check_license_file') as mock_check:
            CopyrightGroup().run(args)
            mock_check.assert_not_called()

        assert license_file.read_text() == original_content


_strip = CopyrightGroup._strip_leading_comment_block


class TestStripLeadingCommentBlock:
    def _write(self, tmp_path, name, content):
        p = tmp_path / name
        p.write_text(content, encoding='utf-8')
        return p

    def test_removes_hash_comment_block(self, tmp_path):
        p = self._write(tmp_path, 'f.py', '# Copyright 2024 Acme\n# All rights reserved\nx = 1\n')
        _strip(str(p), '#')
        assert p.read_text() == 'x = 1\n'

    def test_removes_slash_comment_block(self, tmp_path):
        p = self._write(tmp_path, 'f.cpp', '// Copyright 2024 Acme\n// All rights reserved\nint x;\n')
        _strip(str(p), '//')
        assert p.read_text() == 'int x;\n'

    def test_removes_trailing_blank_line_after_block(self, tmp_path):
        p = self._write(tmp_path, 'f.py', '# Copyright 2024\n\nx = 1\n')
        _strip(str(p), '#')
        assert p.read_text() == 'x = 1\n'

    def test_preserves_shebang(self, tmp_path):
        p = self._write(tmp_path, 'f.sh', '#!/bin/bash\n# Copyright 2024\necho hi\n')
        _strip(str(p), '#')
        assert p.read_text() == '#!/bin/bash\necho hi\n'

    def test_preserves_coding_declaration(self, tmp_path):
        p = self._write(tmp_path, 'f.py', '# -*- coding: utf-8 -*-\n# Copyright 2024\nx = 1\n')
        _strip(str(p), '#')
        assert p.read_text() == '# -*- coding: utf-8 -*-\nx = 1\n'

    def test_no_comment_block_leaves_file_unchanged(self, tmp_path):
        content = 'x = 1\n'
        p = self._write(tmp_path, 'f.py', content)
        _strip(str(p), '#')
        assert p.read_text() == content

    def test_empty_file_unchanged(self, tmp_path):
        p = self._write(tmp_path, 'f.py', '')
        _strip(str(p), '#')
        assert p.read_text() == ''

    def test_only_comment_block_leaves_empty_file(self, tmp_path):
        p = self._write(tmp_path, 'f.py', '# Copyright 2024\n')
        _strip(str(p), '#')
        assert p.read_text() == ''

    def test_does_not_strip_non_matching_comment_style(self, tmp_path):
        content = '// Copyright 2024\nint x;\n'
        p = self._write(tmp_path, 'f.cpp', content)
        _strip(str(p), '#')  # wrong prefix — should leave file untouched
        assert p.read_text() == content

    def test_preserves_go_build_constraint(self, tmp_path):
        p = self._write(tmp_path, 'f.go', '// Copyright 2024\n\n//go:build linux\n\npackage main\n')
        _strip(str(p), '//')
        assert p.read_text() == '//go:build linux\n\npackage main\n'

    def test_leading_go_build_constraint_leaves_file_unchanged(self, tmp_path):
        content = '//go:build linux\n\npackage main\n'
        p = self._write(tmp_path, 'f.go', content)
        _strip(str(p), '//')
        assert p.read_text() == content

    def test_preserves_legacy_go_build_constraint(self, tmp_path):
        p = self._write(tmp_path, 'f.go', '// Copyright 2024\n// +build linux\n\npackage main\n')
        _strip(str(p), '//')
        assert p.read_text() == '// +build linux\n\npackage main\n'


_SLASH_STYLE_SOURCES = [
    ('main.cpp', 'int x;\n'),
    ('main.go', 'package main\n'),
    ('index.js', 'export const x = 1;\n'),
    ('App.jsx', 'export const App = () => null;\n'),
    ('index.ts', 'export const x = 1;\n'),
    ('App.tsx', 'export const App = () => null;\n'),
]

_SLASH_STYLE_RESULT_NAME = 'copyright (c/cpp/go/js/ts)'

_REUSE_HEADER = '// SPDX-FileCopyrightText: 2024 Test Corp\n// SPDX-License-Identifier: Apache-2.0\n\n'


def _run_copyright(files):
    """Run the group over files, with LICENSE file management stubbed out."""
    args = argparse.Namespace(
        license_id='Apache-2.0',
        copyright_year='2024',
        copyright_org='Test Corp',
        wildcard_copyright_org=False,
        reuse_style=True,
        relicense=False,
        files=[str(f) for f in files],
    )
    with patch.object(CopyrightGroup, '_check_license_file', return_value=Result(name='LICENSE file', passed=True)):
        results = CopyrightGroup().run(args)
    return next(r for r in results if r.name == _SLASH_STYLE_RESULT_NAME)


@pytest.mark.parametrize(('name', 'body'), _SLASH_STYLE_SOURCES)
class TestSlashCommentStyleFiles:
    def test_header_is_inserted(self, tmp_path, name, body):
        src = tmp_path / name
        src.write_text(body, encoding='utf-8')
        result = _run_copyright([src])
        assert not result.passed
        assert src.read_text() == _REUSE_HEADER + body

    def test_second_run_passes(self, tmp_path, name, body):
        src = tmp_path / name
        src.write_text(body, encoding='utf-8')
        _run_copyright([src])
        assert _run_copyright([src]).passed

    def test_existing_correct_header_passes(self, tmp_path, name, body):
        src = tmp_path / name
        src.write_text(_REUSE_HEADER + body, encoding='utf-8')
        result = _run_copyright([src])
        assert result.passed
        assert src.read_text() == _REUSE_HEADER + body
