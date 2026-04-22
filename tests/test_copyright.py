# Copyright (c) 2026-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""Tests for CopyrightGroup._check_license_file."""

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
