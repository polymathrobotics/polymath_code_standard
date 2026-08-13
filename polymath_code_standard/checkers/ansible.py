# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
import argparse
import hashlib
import json
from pathlib import Path

import yaml

from polymath_code_standard.checker import CONFIG_DIR, CheckerGroup, Result, check_group

# Where a repo declares the collections and roles its playbooks import.
REQUIREMENTS = Path('ansible/requirements.yml')

# Where we put them: a cache this hook owns, in the consuming repo but out of the
# way. It carries its own '*' .gitignore so no downstream repo has to add one.
#
# The path is ours to choose because ansible-lint runs `ansible-playbook
# --syntax-check` as a child process that receives exactly the paths exported
# below (plus site-packages). Note ansible-lint logs a `<repo>/.ansible/collections`
# entry belonging to its own isolated runtime which it never passes on -- content
# installed there is invisible to syntax-check, which then reports every role as
# "not found".
CACHE_DIR = Path('.polymath-ansible')
COLLECTIONS_DIR = CACHE_DIR / 'collections'
ROLES_DIR = CACHE_DIR / 'roles'

# Installing means downloading, and cloning from git for our own collection: far
# too slow for every commit. Stamp the requirements digest beside the installed
# tree and re-install only when the file changes.
STAMP = CACHE_DIR / 'requirements-sha256'


@check_group
class AnsibleGroup(CheckerGroup):
    name = 'ansible'

    def run(self, args: argparse.Namespace) -> list[Result]:
        results = []

        for result in self._install_requirements():
            results.append(result)
            if not result.passed:
                # Linting now would bury the real error under a pile of
                # syntax-check "role not found" noise.
                return results

        results.append(
            self._check(
                'python3',
                [
                    '-m',
                    'ansiblelint',
                    '-v',
                    '--force-color',
                    # Without this the project root is wherever --config lives (inside
                    # this package), which misplaces requirements lookup and excludes.
                    '--project-dir',
                    '.',
                    '-c',
                    CONFIG_DIR / 'ansible-lint.yml',
                ],
                args.files,
                name='ansible-lint',
                env={
                    'ANSIBLE_COLLECTIONS_PATH': str(COLLECTIONS_DIR),
                    'ANSIBLE_ROLES_PATH': str(ROLES_DIR),
                },
            )
        )
        return results

    @classmethod
    def _install_requirements(cls) -> list[Result]:
        """Install declared content, or return nothing when there is nothing to do.

        ansible-lint does install requirements itself, but only from the locations
        ansible_compat hardcodes (requirements.yml, roles/requirements.yml,
        collections/requirements.yml, tests/...), resolved against its notion of the
        project root -- the directory of the --config file we pass, i.e. a path
        inside this package. Neither matches a Polymath repo, so we install here.
        """
        if not REQUIREMENTS.is_file():
            return []

        raw = REQUIREMENTS.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if STAMP.is_file() and STAMP.read_text().strip() == digest:
            return []

        try:
            declared = yaml.safe_load(raw) or {}
        except yaml.YAMLError as exc:
            return [Result(name='ansible-galaxy', passed=False, output=f'{REQUIREMENTS}: {exc}')]

        cls._make_cache_dir()

        # `collection install` silently skips a roles-only file ("Skipping install,
        # no requirements found", exit 0) and vice versa, so dispatch on what is
        # actually declared rather than always running both.
        installs = [
            ('collection', COLLECTIONS_DIR, declared.get('collections')),
            ('role', ROLES_DIR, declared.get('roles')),
        ]

        results = []
        for kind, dest, entries in installs:
            if not entries:
                continue
            result = cls._check(
                'ansible-galaxy',
                [kind, 'install', '-r', str(REQUIREMENTS), '-p', str(dest)],
                None,
                name='ansible-galaxy',
                # `-p` says where to install but not where to look: galaxy decides
                # "already installed" from the configured search paths, so anything
                # present in the developer's ~/.ansible ends with "Nothing to do"
                # and an empty cache that the linter then cannot resolve.
                env={'ANSIBLE_COLLECTIONS_PATH': str(COLLECTIONS_DIR), 'ANSIBLE_ROLES_PATH': str(ROLES_DIR)},
            )
            results.append(result)
            if not result.passed:
                return results

        git_deps = cls._install_git_dependencies(declared.get('collections') or [])
        results.extend(git_deps)
        if any(not r.passed for r in git_deps):
            return results

        STAMP.write_text(f'{digest}\n')
        return results

    @classmethod
    def _install_git_dependencies(cls, collections: list) -> list[Result]:
        """Install the dependencies of git-sourced collections.

        ansible-galaxy resolves dependencies for collections it pulls from a galaxy
        server, but not for ones installed from git: those arrive with their
        dependencies unmet, and playbooks then fail on modules like
        community.general.modprobe. Requiring every consumer to restate the list is
        how it silently rots, so read it from the collection we just installed.

        Only one pass is needed: whatever we install here comes from a galaxy server,
        so galaxy resolves its dependencies for us.
        """
        if not any(cls._is_git_source(entry) for entry in collections):
            return []

        installed = {}
        for manifest in sorted(COLLECTIONS_DIR.glob('ansible_collections/*/*/MANIFEST.json')):
            try:
                info = json.loads(manifest.read_text())['collection_info']
            except (json.JSONDecodeError, KeyError, OSError):
                continue
            installed[f'{info["namespace"]}.{info["name"]}'] = info.get('dependencies') or {}

        missing = {name: spec for deps in installed.values() for name, spec in deps.items() if name not in installed}
        if not missing:
            return []

        # A '*' requirement is expressed by passing the bare name.
        targets = [f'{name}:{spec}' if spec and spec != '*' else name for name, spec in sorted(missing.items())]
        return [
            cls._check(
                'ansible-galaxy',
                ['collection', 'install', *targets, '-p', str(COLLECTIONS_DIR)],
                None,
                name='ansible-galaxy',
                env={'ANSIBLE_COLLECTIONS_PATH': str(COLLECTIONS_DIR), 'ANSIBLE_ROLES_PATH': str(ROLES_DIR)},
            )
        ]

    @staticmethod
    def _is_git_source(entry: object) -> bool:
        if not isinstance(entry, dict):
            return False
        name = str(entry.get('name', ''))
        return entry.get('type') == 'git' or name.startswith('git@') or name.endswith('.git')

    @staticmethod
    def _make_cache_dir() -> None:
        """Create the cache and make it ignore itself, including on a failed install."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        gitignore = CACHE_DIR / '.gitignore'
        if not gitignore.is_file():
            gitignore.write_text('*\n')
