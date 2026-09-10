# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for the javascript, css, and html checker groups."""

import shutil
import sys
import uuid
from pathlib import Path

import pytest

from polymath_code_standard import runner
from polymath_code_standard.checker import Result
from polymath_code_standard.checkers import web
from polymath_code_standard.checkers.web import _node

_PROJECT_ROOT = Path(__file__).parent.parent
_TEST_FILES = Path('test_files') / 'web'


@pytest.fixture
def project_dir():
    """A scratch directory inside the project root, which is where ESLint's base path reaches.

    Keep the name out of .gitignore: Prettier's default --ignore-path includes .gitignore,
    and an ignored fixture would pass without being checked.
    """
    path = _PROJECT_ROOT / f'.pytest_web_{uuid.uuid4().hex[:8]}'
    path.mkdir()
    yield path
    shutil.rmtree(path, ignore_errors=True)


def _passing_run(name, cmd, files=None, env=None):
    return Result(name=name, passed=True)


def test_node_install_runs_once_per_bundle(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(_node, 'run', lambda name, cmd, *a, **kw: calls.append(cmd) or Result(name=name, passed=True))

    install_dir = tmp_path / 'polymath-node'
    assert _node.ensure_node_modules(install_dir) == install_dir
    assert calls[0][1:4] == ['ci', '--prefix', str(install_dir)]

    # The tool configs land beside the manifest, where Node resolves their imports from.
    for name in _node.BUNDLE:
        assert (install_dir / name).is_file()

    assert _node.ensure_node_modules(install_dir) == install_dir
    assert len(calls) == 1

    monkeypatch.setattr(_node, 'bundle_digest', lambda: 'a' * 64)
    assert _node.ensure_node_modules(install_dir) == install_dir
    assert len(calls) == 2


def test_node_install_failure_is_returned(tmp_path, monkeypatch):
    monkeypatch.setattr(
        _node, 'run', lambda name, cmd, *a, **kw: Result(name=name, passed=False, output='EBADPLATFORM')
    )

    install_dir = tmp_path / 'polymath-node'
    result = _node.ensure_node_modules(install_dir)
    assert result == Result(name='npm', passed=False, output='EBADPLATFORM')

    # An unstamped directory reinstalls on the next run.
    assert not (install_dir / _node.STAMP_NAME).exists()


def test_node_env_puts_the_venv_first_on_path():
    assert _node.node_env()['PATH'].startswith(f'{Path(sys.executable).parent}:')


def test_eslint_receives_the_selected_frameworks(monkeypatch):
    captured = {}

    def fake_run(name, cmd, files=None, env=None):
        captured[name] = (cmd, files, env)
        return Result(name=name, passed=True)

    monkeypatch.setattr(web, 'run', fake_run)
    monkeypatch.setattr(web, 'ensure_node_modules', lambda: Path('/node'))

    assert runner.main(['javascript', '--framework', 'next', '--framework', 'storybook', 'app.ts']) == 0

    cmd, files, env = captured['eslint']
    assert env['POLYMATH_ESLINT_FRAMEWORKS'] == 'next,storybook'
    assert files == ['app.ts']
    assert cmd[0] == '/node/node_modules/.bin/eslint'
    assert cmd[1:3] == ['--config', '/node/eslint.config.mjs']


def test_eslint_frameworks_default_to_empty(monkeypatch):
    captured = {}

    def fake_run(name, cmd, files=None, env=None):
        captured[name] = env
        return Result(name=name, passed=True)

    monkeypatch.setattr(web, 'run', fake_run)
    monkeypatch.setattr(web, 'ensure_node_modules', lambda: Path('/node'))

    assert runner.main(['javascript', 'app.ts']) == 0
    assert captured['eslint']['POLYMATH_ESLINT_FRAMEWORKS'] == ''


def test_unknown_framework_is_rejected():
    with pytest.raises(SystemExit):
        runner.main(['javascript', '--framework', 'svelte', 'app.ts'])


def test_prettier_skips_without_files():
    assert web.run_prettier(Path('/node'), []) == Result(name='prettier', passed=True, skipped=True)


def test_prettier_writes_and_reports(monkeypatch):
    """A failing --check triggers a --write pass and the re-stage message."""
    modes = []

    def fake_run(name, cmd, files=None, env=None):
        modes.append(cmd[-1])
        passed = '--write' in cmd
        return Result(name=name, passed=passed, output='' if passed else 'style.css', cmd=cmd)

    monkeypatch.setattr(web, 'run', fake_run)

    result = web.run_prettier(Path('/node'), ['style.css'])
    assert modes == ['--check', '--write']
    assert not result.passed
    assert result.output == f'style.css\n{web.RESTAGE}'


def test_prettier_omits_restage_when_the_write_fails(monkeypatch):
    """A syntax error fails both passes, so nothing was rewritten."""
    monkeypatch.setattr(
        web, 'run', lambda name, cmd, files=None, env=None: Result(name=name, passed=False, output='SyntaxError')
    )

    result = web.run_prettier(Path('/node'), ['broken.css'])
    assert result.output == 'SyntaxError'


def test_prettier_ignores_editorconfig(monkeypatch):
    """Both passes carry --no-editorconfig."""
    commands = []
    monkeypatch.setattr(
        web,
        'run',
        lambda name, cmd, files=None, env=None: commands.append(cmd) or Result(name=name, passed=False, cmd=cmd),
    )

    web.run_prettier(Path('/node'), ['style.css'])
    assert [cmd[-1] for cmd in commands] == ['--check', '--write']
    assert all('--no-editorconfig' in cmd for cmd in commands)


@pytest.mark.parametrize('group', ['javascript', 'css', 'html'])
def test_groups_skip_without_files(group, monkeypatch):
    """No applicable files means no npm install."""
    monkeypatch.setattr(web, 'ensure_node_modules', lambda: pytest.fail('installed with nothing to check'))
    assert runner.main([group]) == 0


@pytest.mark.parametrize('group', ['javascript', 'css', 'html'])
def test_failed_install_is_the_only_result(group, monkeypatch):
    failure = Result(name='npm', passed=False, output='network unreachable')
    monkeypatch.setattr(web, 'ensure_node_modules', lambda: failure)
    monkeypatch.setattr(web, 'run', _passing_run)
    assert runner.main([group, 'anything.ts']) == 1


@pytest.mark.network
@pytest.mark.parametrize(
    ('group', 'names'),
    [
        ('javascript', ['greeting.ts', 'banner.tsx', 'total.js', 'paths.cjs']),
        ('css', ['banner.css', 'banner.scss']),
        ('html', ['banner.html']),
    ],
)
def test_bundled_test_files_pass(group, names, monkeypatch):
    monkeypatch.chdir(_PROJECT_ROOT)
    assert runner.main([group, *(str(_TEST_FILES / name) for name in names)]) == 0


@pytest.mark.network
def test_explicit_any_fails_eslint(project_dir, monkeypatch):
    source = project_dir / 'any.ts'
    source.write_text('const x: any = 1;\nexport default x;\n')
    monkeypatch.chdir(_PROJECT_ROOT)
    assert runner.main(['javascript', str(source.relative_to(_PROJECT_ROOT))]) == 1


@pytest.mark.network
def test_unformatted_css_is_rewritten(project_dir, monkeypatch):
    source = project_dir / 'unformatted.css'
    source.write_text('.a{color:#FFF}\n')
    monkeypatch.chdir(_PROJECT_ROOT)
    assert runner.main(['css', str(source.relative_to(_PROJECT_ROOT))]) == 1
    assert source.read_text() == '.a {\n  color: #fff;\n}\n'
