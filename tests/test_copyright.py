# Copyright (c) 2026-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""Tests for CopyrightGroup._check_license_file and _strip_leading_comment_block."""

from unittest.mock import patch

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
