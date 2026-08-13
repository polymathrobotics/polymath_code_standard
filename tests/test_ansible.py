# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for the ansible checker group.

Beyond running ansible-lint, this group installs what a repo declares in
ansible/requirements.yml, because ansible-lint will not: it only auto-installs
from paths ansible_compat hardcodes, resolved against its notion of the project
root -- which is the directory of the --config file we pass, i.e. a path inside
this package.
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from polymath_code_standard import runner
from polymath_code_standard.checker import Result
from polymath_code_standard.checkers import ansible as ansible_checker

_PROJECT_ROOT = Path(__file__).parent.parent


def _write_manifest(root: Path, fqcn: str, dependencies: dict) -> None:
    """Fake a collection installed by ansible-galaxy, which records deps in MANIFEST.json."""
    namespace, name = fqcn.split('.')
    path = root / 'ansible_collections' / namespace / name
    path.mkdir(parents=True)
    (path / 'MANIFEST.json').write_text(
        json.dumps({'collection_info': {'namespace': namespace, 'name': name, 'dependencies': dependencies}})
    )


@pytest.mark.network
def test_ansible_installs_requirements(tmp_path, monkeypatch):
    """A downstream repo declaring requirements.yml gets them installed, then linted.

    The fixture playbook imports a role and a module from a collection, neither of
    which ansible-lint resolves on its own.
    """
    shutil.copytree(_PROJECT_ROOT / 'test_files' / 'ansible', tmp_path / 'ansible')
    monkeypatch.chdir(tmp_path)

    assert runner.main(['ansible', 'ansible/playbook.yml']) == 0

    # A passing lint already proves the syntax-check child resolved both, but assert
    # the layout too, so moving these paths fails loudly instead of silently
    # depending on some other collections path that happens to be populated.
    assert (tmp_path / ansible_checker.COLLECTIONS_DIR / 'ansible_collections' / 'ansible' / 'posix').is_dir()
    assert (tmp_path / ansible_checker.ROLES_DIR / 'geerlingguy.docker').is_dir()

    # The cache hides itself, so consuming repos need no .gitignore edit.
    assert (tmp_path / ansible_checker.CACHE_DIR / '.gitignore').read_text().strip() == '*'

    # Second run installs nothing: re-cloning on every commit would be far too slow.
    assert ansible_checker.AnsibleGroup._install_requirements() == []


def test_ansible_stamp_tracks_requirements(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'ansible').mkdir()
    requirements = tmp_path / ansible_checker.REQUIREMENTS
    requirements.write_text('---\ncollections:\n  - name: ansible.posix\n')

    stamp = tmp_path / ansible_checker.STAMP
    stamp.parent.mkdir(parents=True)
    stamp.write_text(hashlib.sha256(requirements.read_bytes()).hexdigest())
    assert ansible_checker.AnsibleGroup._install_requirements() == []

    # Editing requirements.yml invalidates the stamp so the install runs again.
    requirements.write_text('---\nroles:\n  - name: geerlingguy.docker\n')
    assert ansible_checker.AnsibleGroup._install_requirements() != []


def test_ansible_without_requirements_installs_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert ansible_checker.AnsibleGroup._install_requirements() == []
    assert not (tmp_path / ansible_checker.CACHE_DIR).exists()


def test_ansible_git_dependencies_detected_from_manifest(tmp_path, monkeypatch):
    """Unmet dependencies of an installed collection are found, met ones ignored."""
    monkeypatch.chdir(tmp_path)
    cache = tmp_path / ansible_checker.COLLECTIONS_DIR
    _write_manifest(cache, 'polymath.core', {'community.general': '>=10.4', 'amazon.aws': '*'})
    _write_manifest(cache, 'amazon.aws', {})

    calls = []
    monkeypatch.setattr(
        ansible_checker.AnsibleGroup,
        '_check',
        classmethod(lambda cls, tool, args, files, **kw: calls.append(args) or Result(name=tool, passed=True)),
    )

    git_entry = [{'name': 'git@github.com:polymathrobotics/polymath_core.git', 'type': 'git'}]
    assert ansible_checker.AnsibleGroup._install_git_dependencies(git_entry) == [
        Result(name='ansible-galaxy', passed=True)
    ]

    # amazon.aws is already installed; a '*' spec is passed as a bare name.
    assert calls == [['collection', 'install', 'community.general:>=10.4', '-p', str(ansible_checker.COLLECTIONS_DIR)]]


def test_ansible_registry_only_requirements_skip_dependency_pass(tmp_path, monkeypatch):
    """galaxy resolves dependencies itself for non-git sources, so we stay out of it."""
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path / ansible_checker.COLLECTIONS_DIR, 'polymath.core', {'community.general': '>=10.4'})
    assert ansible_checker.AnsibleGroup._install_git_dependencies([{'name': 'ansible.posix'}]) == []
