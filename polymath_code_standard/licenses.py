# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
"""SPDX license header and full-text lookup.

Supports any SPDX license ID via the spdx/license-list-data JSON API, plus the
special 'proprietary' ID which reads from the bundled copyright.txt template.

Two header modes:
  reuse_style_header=True  — two-line REUSE/SPDX header, no network required:
                               SPDX-FileCopyrightText: <year> <org>
                               SPDX-License-Identifier: <id>
  reuse_style_header=False — fetches standardLicenseHeader from SPDX; falls
                               back to licenseText when the field is absent.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path

_CONFIG_DIR = Path(__file__).parent / 'config'
_SPDX_BASE_URL = 'https://raw.githubusercontent.com/spdx/license-list-data/main/json/details/{id}.json'

PROPRIETARY = 'proprietary'


@lru_cache(maxsize=None)
def _fetch_spdx_json(spdx_id: str) -> dict:
    url = _SPDX_BASE_URL.format(id=spdx_id)
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _get_spdx_data(spdx_id: str) -> dict:
    try:
        return _fetch_spdx_json(spdx_id)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ValueError(f'Unknown SPDX license ID: {spdx_id!r}') from exc
        raise


def _substitute(text: str, year: str, org: str) -> str:
    for placeholder, value in (
        ('[yyyy]', year),
        ('[name of copyright owner]', org),
        ('<year>', year),
        ('<copyright holders>', org),
        ('<owner>', org),
    ):
        text = text.replace(placeholder, value)
    return text


def get_license_header(spdx_id: str, year: str, org: str, *, reuse_style_header: bool = True) -> str:
    """Return the undecorated header text for source files (no comment markers).

    For 'proprietary', reads and fills the bundled copyright.txt template;
    the reuse_style_header flag is ignored.
    """
    if spdx_id == PROPRIETARY:
        return _substitute((_CONFIG_DIR / 'copyright.txt').read_text(encoding='utf-8'), year, org)
    if reuse_style_header:
        return f'SPDX-FileCopyrightText: {year} {org}\nSPDX-License-Identifier: {spdx_id}\n'
    data = _get_spdx_data(spdx_id)
    raw = data.get('standardLicenseHeader') or data['licenseText']
    return _substitute(raw, year, org)


def get_license_full_text(spdx_id: str, year: str, org: str) -> str:
    """Return the full LICENSE file text."""
    if spdx_id == PROPRIETARY:
        raise ValueError("'proprietary' licenses do not have a LICENSE file")
    data = _get_spdx_data(spdx_id)
    return _substitute(data['licenseText'], year, org)
