# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Smoke tests: verify runner.main dispatches to each checker and runs without error."""

import shutil
import uuid
from pathlib import Path

import pytest

from polymath_code_standard import runner
from polymath_code_standard.checker import _GROUPS

_PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture
def make_file(tmp_path):
    """Create a temp file in /tmp — fine for most checkers."""

    def _make(name: str, content: str) -> str:
        p = tmp_path / name
        p.write_text(content, encoding='utf-8')
        return str(p)

    return _make


@pytest.fixture
def make_project_file():
    """Create a temp file inside the project root — needed when tools walk up to find configs."""
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


def test_all_groups_registered():
    names = {g.name for g in _GROUPS}
    expected = {
        'general',
        'python',
        'cpp',
        'shell',
        'cmake',
        'docker',
        'markdown',
        'xml',
        'yaml',
        'toml',
        'json',
        'copyright',
        'ansible',
    }
    assert names == expected


def test_general():
    # Use this test file itself — it's inside the git repo and clean
    assert runner.main(['general', str(Path(__file__))]) == 0


def test_python(make_file):
    f = make_file('example.py', 'x = 1\n')
    assert runner.main(['python', f]) == 0


def test_cpp(make_project_file):
    # Files must be inside the project so cpplint can walk up and find the config
    content = 'int main()\n{\n  return 0;\n}\n'
    f = make_project_file('example.cpp', content)
    assert runner.main(['cpp', f]) == 0


def test_shell(make_file):
    f = make_file('example.sh', '#!/bin/bash\necho "hello"\n')
    assert runner.main(['shell', f]) == 0


def test_cmake(make_file):
    content = 'cmake_minimum_required(VERSION 3.20)\nproject(test)\n'
    f = make_file('CMakeLists.txt', content)
    assert runner.main(['cmake', f]) == 0


def test_docker(make_file):
    f = make_file('Dockerfile', 'FROM ubuntu:22.04\n')
    assert runner.main(['docker', f]) == 0


def test_markdown(make_file):
    f = make_file('README.md', '# Hello\n\nWorld\n')
    assert runner.main(['markdown', f]) == 0


def test_xml(make_file):
    f = make_file('test.xml', '<?xml version="1.0"?>\n<root/>\n')
    assert runner.main(['xml', f]) == 0


def test_yaml(make_file):
    f = make_file('test.yaml', '---\nkey: value\n')
    assert runner.main(['yaml', f]) == 0


def test_toml(make_file):
    f = make_file('test.toml', '[section]\nkey = "value"\n')
    assert runner.main(['toml', f]) == 0


def test_json(make_file):
    f = make_file('test.json', '{"key": "value"}\n')
    assert runner.main(['json', f]) == 0


def test_copyright(make_file):
    content = (
        '# Copyright (c) 2024-present Test Corp All rights reserved\n'
        '# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.\n'
        'x = 1\n'
    )
    f = make_file('example.py', content)
    assert (
        runner.main([
            'copyright',
            '--license',
            'proprietary',
            '--copyright-org',
            'Test Corp',
            '--copyright-year',
            '2024',
            f,
        ])
        == 0
    )


def test_ansible(make_file):
    content = (
        '---\n'
        '- name: Minimal playbook\n'
        '  hosts: localhost\n'
        '  gather_facts: false\n'
        '  tasks:\n'
        '    - name: Print message\n'
        '      ansible.builtin.debug:\n'
        '        msg: "hello"\n'
    )
    f = make_file('playbook.yml', content)
    assert runner.main(['ansible', f]) == 0
