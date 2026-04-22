# Copyright (c) 2026-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""Tests for the SPDX license header and full-text lookup module."""

import urllib.error
from unittest.mock import patch

import pytest

from polymath_code_standard import licenses
from polymath_code_standard.licenses import get_license_full_text, get_license_header

# ---------------------------------------------------------------------------
# Minimal mock SPDX payloads
# ---------------------------------------------------------------------------

_APACHE_DATA = {
    'licenseId': 'Apache-2.0',
    'licenseText': 'Apache License\nVersion 2.0, January 2004\nhttp://www.apache.org/licenses/\n',
    'standardLicenseHeader': (
        'Copyright [yyyy] [name of copyright owner]\n\n'
        'Licensed under the Apache License, Version 2.0 (the "License");\n'
        'you may not use this file except in compliance with the License.\n'
    ),
}

_MIT_DATA = {
    'licenseId': 'MIT',
    'licenseText': (
        'MIT License\n\nCopyright (c) <year> <copyright holders>\n\nPermission is hereby granted, free of charge...\n'
    ),
    # intentionally no standardLicenseHeader
}


def _mock_fetch(data: dict):
    return patch('polymath_code_standard.licenses._fetch_spdx_json', return_value=data)


def _mock_fetch_404(spdx_id: str = 'UNKNOWN-1.0'):
    exc = urllib.error.HTTPError(url=None, code=404, msg='Not Found', hdrs=None, fp=None)
    return patch('polymath_code_standard.licenses._fetch_spdx_json', side_effect=exc)


@pytest.fixture(autouse=True)
def clear_cache():
    licenses._fetch_spdx_json.cache_clear()
    yield
    licenses._fetch_spdx_json.cache_clear()


# ---------------------------------------------------------------------------
# get_license_header — REUSE-style (no network)
# ---------------------------------------------------------------------------


class TestGetLicenseHeaderReuseStyle:
    def test_proprietary_fills_org(self):
        result = get_license_header('proprietary', '2024', 'Acme Corp')
        assert 'Acme Corp' in result

    def test_proprietary_fills_year(self):
        result = get_license_header('proprietary', '2024', 'Acme Corp')
        assert '2024' in result

    def test_reuse_style_copyright_line(self):
        result = get_license_header('MIT', '2024', 'Acme Corp', reuse_style_header=True)
        assert 'SPDX-FileCopyrightText: 2024 Acme Corp' in result

    def test_reuse_style_identifier_line(self):
        result = get_license_header('MIT', '2024', 'Acme Corp', reuse_style_header=True)
        assert 'SPDX-License-Identifier: MIT' in result

    def test_reuse_style_works_for_any_id(self):
        result = get_license_header('GPL-3.0-only', '2024', 'Acme Corp', reuse_style_header=True)
        assert 'SPDX-License-Identifier: GPL-3.0-only' in result

    def test_reuse_style_does_not_fetch_network(self):
        with patch('polymath_code_standard.licenses._fetch_spdx_json') as mock_fetch:
            get_license_header('Apache-2.0', '2024', 'Acme Corp', reuse_style_header=True)
        mock_fetch.assert_not_called()


# ---------------------------------------------------------------------------
# get_license_header — network fetch (reuse_style_header=False)
# ---------------------------------------------------------------------------


class TestGetLicenseHeaderFetched:
    def test_uses_standard_license_header_when_present(self):
        with _mock_fetch(_APACHE_DATA):
            result = get_license_header('Apache-2.0', '2024', 'Acme Corp', reuse_style_header=False)
        assert 'Apache License' in result

    def test_substitutes_year_in_standard_header(self):
        with _mock_fetch(_APACHE_DATA):
            result = get_license_header('Apache-2.0', '2024', 'Acme Corp', reuse_style_header=False)
        assert '2024' in result
        assert '[yyyy]' not in result

    def test_substitutes_org_in_standard_header(self):
        with _mock_fetch(_APACHE_DATA):
            result = get_license_header('Apache-2.0', '2024', 'Acme Corp', reuse_style_header=False)
        assert 'Acme Corp' in result
        assert '[name of copyright owner]' not in result

    def test_falls_back_to_license_text_when_no_standard_header(self):
        with _mock_fetch(_MIT_DATA):
            result = get_license_header('MIT', '2024', 'Acme Corp', reuse_style_header=False)
        assert 'MIT License' in result

    def test_substitutes_year_in_fallback_license_text(self):
        with _mock_fetch(_MIT_DATA):
            result = get_license_header('MIT', '2024', 'Acme Corp', reuse_style_header=False)
        assert '2024' in result
        assert '<year>' not in result

    def test_substitutes_org_in_fallback_license_text(self):
        with _mock_fetch(_MIT_DATA):
            result = get_license_header('MIT', '2024', 'Acme Corp', reuse_style_header=False)
        assert 'Acme Corp' in result
        assert '<copyright holders>' not in result

    def test_unknown_id_raises(self):
        with _mock_fetch_404(), pytest.raises(ValueError, match='UNKNOWN-1.0'):
            get_license_header('UNKNOWN-1.0', '2024', 'Acme Corp', reuse_style_header=False)

    def test_result_is_cached(self):
        import json
        from unittest.mock import MagicMock

        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        resp.read.return_value = json.dumps(_MIT_DATA).encode()
        with patch('urllib.request.urlopen', return_value=resp) as mock_urlopen:
            get_license_header('MIT', '2024', 'Acme Corp', reuse_style_header=False)
            get_license_header('MIT', '2025', 'Other Corp', reuse_style_header=False)
        mock_urlopen.assert_called_once()


# ---------------------------------------------------------------------------
# get_license_full_text
# ---------------------------------------------------------------------------


class TestGetLicenseFullText:
    def test_proprietary_raises(self):
        with pytest.raises(ValueError, match='proprietary'):
            get_license_full_text('proprietary', '2024', 'Acme Corp')

    def test_returns_license_text(self):
        with _mock_fetch(_MIT_DATA):
            result = get_license_full_text('MIT', '2024', 'Acme Corp')
        assert 'MIT License' in result

    def test_substitutes_year(self):
        with _mock_fetch(_MIT_DATA):
            result = get_license_full_text('MIT', '2024', 'Acme Corp')
        assert '2024' in result
        assert '<year>' not in result

    def test_substitutes_org(self):
        with _mock_fetch(_MIT_DATA):
            result = get_license_full_text('MIT', '2024', 'Acme Corp')
        assert 'Acme Corp' in result
        assert '<copyright holders>' not in result

    def test_unknown_id_raises(self):
        with _mock_fetch_404(), pytest.raises(ValueError, match='UNKNOWN-1.0'):
            get_license_full_text('UNKNOWN-1.0', '2024', 'Acme Corp')
