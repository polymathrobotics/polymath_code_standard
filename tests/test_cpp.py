# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
import os
import shutil
import tempfile
import uuid
from pathlib import Path

import pytest

from polymath_code_standard.checker import CONFIG_DIR
from polymath_code_standard.checkers.cpp import _insert_includes, _insertion_point, _parse_iwyu_output, fix_iwyu

_PROJECT_ROOT = Path(__file__).parent.parent


# --- _parse_iwyu_output ---


def test_parse_single_header():
    output = 'file.cpp:0:  Add #include <string> for string  [build/include_what_you_use] [4]'
    assert _parse_iwyu_output(output) == {'file.cpp': {'#include <string>'}}


def test_parse_multiple_headers_same_file():
    output = (
        'a.cpp:0:  Add #include <string> for string  [build/include_what_you_use] [4]\n'
        'a.cpp:0:  Add #include <vector> for vector<>  [build/include_what_you_use] [4]\n'
    )
    assert _parse_iwyu_output(output) == {'a.cpp': {'#include <string>', '#include <vector>'}}


def test_parse_multiple_files():
    output = (
        'a.cpp:0:  Add #include <string> for string  [build/include_what_you_use] [4]\n'
        'b.cpp:0:  Add #include <vector> for vector<>  [build/include_what_you_use] [4]\n'
    )
    assert _parse_iwyu_output(output) == {'a.cpp': {'#include <string>'}, 'b.cpp': {'#include <vector>'}}


def test_parse_quoted_header():
    output = 'file.cpp:0:  Add #include "my_header.hpp" for MyClass  [build/include_what_you_use] [4]'
    assert _parse_iwyu_output(output) == {'file.cpp': {'#include "my_header.hpp"'}}


def test_parse_ignores_unrelated_errors():
    output = 'file.cpp:5:  Some other lint error  [some/category] [3]\n'
    assert _parse_iwyu_output(output) == {}


def test_parse_empty_output():
    assert _parse_iwyu_output('') == {}


# --- _insertion_point ---


def test_insertion_point_after_last_include():
    lines = ['#include <iostream>\n', '#include <string>\n', '\n', 'void f() {}\n']
    assert _insertion_point(lines) == 2


def test_insertion_point_single_include():
    lines = ['#include <iostream>\n', '\n', 'void f() {}\n']
    assert _insertion_point(lines) == 1


def test_insertion_point_no_includes_skips_comment_header():
    lines = ['// License header\n', '// More comments\n', '\n', 'void f() {}\n']
    # Should insert before first real code (index 3)
    assert _insertion_point(lines) == 3


def test_insertion_point_no_includes_skips_pragma_once():
    lines = ['// License\n', '#pragma once\n', '\n', 'void f() {}\n']
    assert _insertion_point(lines) == 3


def test_insertion_point_empty_file():
    assert _insertion_point([]) == 0


# --- _insert_includes ---


def test_insert_after_last_include(tmp_path):
    f = tmp_path / 'test.cpp'
    f.write_text('#include <iostream>\n\nvoid f() {}\n')
    _insert_includes(str(f), {'#include <string>'})
    lines = f.read_text().splitlines()
    assert lines[0] == '#include <iostream>'
    assert lines[1] == '#include <string>'


def test_insert_multiple_sorted(tmp_path):
    f = tmp_path / 'test.cpp'
    f.write_text('#include <iostream>\n\nvoid f() {}\n')
    _insert_includes(str(f), {'#include <vector>', '#include <string>'})
    lines = f.read_text().splitlines()
    inserted = [line for line in lines if line.startswith('#include <s') or line.startswith('#include <v')]
    assert inserted == ['#include <string>', '#include <vector>']


def test_insert_no_existing_includes(tmp_path):
    f = tmp_path / 'test.cpp'
    f.write_text('// License header\n\nvoid f() {}\n')
    _insert_includes(str(f), {'#include <string>'})
    assert '#include <string>' in f.read_text()


# --- fix_iwyu integration ---


@pytest.fixture
def project_files():
    """Create temp files inside the project root. cpplint --config requires a bare filename
    with no directory components, so the config and source files must live in cwd (project root)."""
    created = []

    def _make(name: str, content: str) -> str:
        d = _PROJECT_ROOT / f'.pytest_tmp_{uuid.uuid4().hex[:8]}'
        d.mkdir()
        p = d / name
        p.write_text(content, encoding='utf-8')
        created.append(d)
        return str(p)

    yield _make

    for d in created:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def cpplint_cfg():
    """Temp copy of .cpplint.cfg in the project root (cwd), yielding its bare filename."""
    fd, path = tempfile.mkstemp(dir=_PROJECT_ROOT, prefix='.cpplint_', suffix='.cfg')
    os.close(fd)
    try:
        shutil.copy2(CONFIG_DIR / '.cpplint.cfg', path)
        yield Path(path).name
    finally:
        Path(path).unlink(missing_ok=True)


def test_fix_iwyu_inserts_missing_header(project_files, cpplint_cfg):
    content = (
        '// SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.\n#include <iostream>\nvoid f() { std::string s; }\n'
    )
    f = project_files('test.cpp', content)
    result = fix_iwyu([f], cpplint_cfg)
    assert not result.passed
    assert '#include <string>' in Path(f).read_text()


def test_fix_iwyu_no_issues(project_files, cpplint_cfg):
    content = (
        '// SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.\n#include <string>\nvoid f() { std::string s; }\n'
    )
    f = project_files('test.cpp', content)
    result = fix_iwyu([f], cpplint_cfg)
    assert result.passed


def test_fix_iwyu_skips_empty_list(cpplint_cfg):
    result = fix_iwyu([], cpplint_cfg)
    assert result.passed
    assert result.skipped
