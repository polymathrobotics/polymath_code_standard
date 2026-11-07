# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Git LFS pointer check in the general group."""

import subprocess

import pytest

from polymath_code_standard.checkers.general import GeneralGroup

POINTER = b'version https://git-lfs.github.com/spec/v1\noid sha256:0\nsize 1\n'


@pytest.fixture
def repo(tmp_path, monkeypatch):
    # Without the user's LFS filter, `git add` stages files as they are, as on a machine without git-lfs.
    monkeypatch.setenv('GIT_CONFIG_GLOBAL', '/dev/null')
    monkeypatch.setenv('GIT_CONFIG_NOSYSTEM', '1')
    subprocess.run(['git', 'init', '-q'], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    (tmp_path / '.gitattributes').write_text('*.webp filter=lfs diff=lfs merge=lfs -text\n')
    (tmp_path / 'img').mkdir()
    return tmp_path


def stage(repo, path, content):
    (repo / path).write_bytes(content)
    subprocess.run(['git', 'add', path], cwd=repo, check=True)


def test_plain_lfs_file_fails(repo):
    stage(repo, 'img/a.webp', b'RIFF....WEBP')

    result = GeneralGroup.run_lfs_pointers(['img/a.webp'])

    assert not result.passed
    assert '  img/a.webp\n' in result.output
    assert 'git add --renormalize img/a.webp' in result.output


def test_pointer_passes(repo):
    stage(repo, 'img/a.webp', POINTER)

    assert GeneralGroup.run_lfs_pointers(['img/a.webp']).passed


def test_file_outside_lfs_passes(repo):
    stage(repo, 'img/a.svg', b'<svg/>')

    assert GeneralGroup.run_lfs_pointers(['img/a.svg']).passed


def test_unstaged_file_skipped(repo):
    (repo / 'img' / 'a.webp').write_bytes(b'RIFF....WEBP')

    assert GeneralGroup.run_lfs_pointers(['img/a.webp']).passed


def test_checks_staged_content_not_working_tree(repo):
    stage(repo, 'img/a.webp', b'RIFF....WEBP')
    (repo / 'img' / 'a.webp').write_bytes(POINTER)

    assert not GeneralGroup.run_lfs_pointers(['img/a.webp']).passed


def test_absolute_path(repo):
    stage(repo, 'img/a.webp', b'RIFF....WEBP')

    assert not GeneralGroup.run_lfs_pointers([str(repo / 'img' / 'a.webp')]).passed


def test_reports_only_plain_files(repo):
    stage(repo, 'img/a.webp', POINTER)
    stage(repo, 'img/b.webp', b'RIFF....WEBP')

    result = GeneralGroup.run_lfs_pointers(['img/a.webp', 'img/b.webp', 'img/c.webp'])

    assert result.output.endswith('git add --renormalize img/b.webp')


def test_no_files_skipped():
    assert GeneralGroup.run_lfs_pointers([]).skipped
