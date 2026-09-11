# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for the go checker group.

golangci-lint works on packages and must run from a module root.
Most of this group is the bookkeeping that gets there:
find each file's module, make its paths relative, and collapse them to package directories.
"""

import argparse
import hashlib
import io
import shutil
import tarfile
from pathlib import Path

import pytest
import yaml

from polymath_code_standard import runner
from polymath_code_standard.checker import Result
from polymath_code_standard.checkers import go as go_checker
from polymath_code_standard.checkers.go import _golangci

_PROJECT_ROOT = Path(__file__).parent.parent

_HAS_GO = shutil.which('go') is not None
needs_go = pytest.mark.skipif(not _HAS_GO, reason='Go toolchain not on PATH')

CLEAN_MAIN = '// Package main is a fixture.\npackage main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("x")\n}\n'


def _module(root: Path, name: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / 'go.mod').write_text(f'module example.com/{name}\n\ngo 1.23\n')
    return root


def _go_args(*files: Path) -> argparse.Namespace:
    return argparse.Namespace(files=[str(f) for f in files])


# --- module grouping ---


def test_module_root_finds_nearest_go_mod(tmp_path):
    outer = _module(tmp_path / 'outer', 'outer')
    inner = _module(outer / 'inner', 'inner')
    nested = inner / 'pkg' / 'deep.go'
    nested.parent.mkdir(parents=True)
    nested.write_text(CLEAN_MAIN)
    assert go_checker.module_root(str(nested)) == inner


def test_group_by_module_splits_modules_and_nested_packages(tmp_path):
    first = _module(tmp_path / 'first', 'first')
    second = _module(tmp_path / 'second', 'second')
    files = [first / 'main.go', first / 'pkg' / 'a.go', second / 'main.go']
    for f in files:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(CLEAN_MAIN)

    modules, orphans = go_checker.group_by_module([str(f) for f in files])
    assert orphans == []
    assert modules == {
        first: [Path('main.go'), Path('pkg/a.go')],
        second: [Path('main.go')],
    }


def test_group_by_module_drops_vendored_sources(tmp_path):
    root = _module(tmp_path, 'app')
    vendored = root / 'vendor' / 'example.com' / 'dep' / 'dep.go'
    vendored.parent.mkdir(parents=True)
    vendored.write_text(CLEAN_MAIN)
    (root / 'main.go').write_text(CLEAN_MAIN)

    modules, orphans = go_checker.group_by_module([str(root / 'main.go'), str(vendored)])
    assert orphans == []
    assert modules == {root: [Path('main.go')]}


def test_group_by_module_reports_files_outside_any_module(tmp_path):
    stray = tmp_path / 'stray.go'
    stray.write_text(CLEAN_MAIN)
    modules, orphans = go_checker.group_by_module([str(stray)])
    assert modules == {}
    assert orphans == [str(stray)]


def test_package_dirs_collapses_to_distinct_directories():
    relative = [Path('main.go'), Path('doc.go'), Path('pkg/a.go'), Path('pkg/b.go'), Path('pkg/sub/c.go')]
    assert go_checker.package_dirs(relative) == ['.', './pkg', './pkg/sub']


def test_hook_runs_as_a_single_process():
    """pre-commit passes every staged file to one process, since golangci-lint locks per run."""
    hooks = yaml.safe_load((_PROJECT_ROOT / '.pre-commit-hooks.yaml').read_text())
    go_hook = next(h for h in hooks if h['id'] == 'polymath-go')
    assert go_hook['require_serial'] is True


def test_bundled_config_allows_parallel_runners():
    config = yaml.safe_load((go_checker.CONFIG_DIR / 'golangci.yml').read_text())
    assert config['run']['allow-parallel-runners'] is True


def test_file_without_go_mod_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(go_checker.shutil, 'which', lambda _: '/usr/bin/go')
    stray = tmp_path / 'stray.go'
    stray.write_text(CLEAN_MAIN)
    results = go_checker.GoGroup().run(_go_args(stray))
    assert [r.passed for r in results] == [False]
    assert 'no go.mod' in results[0].output


def test_no_go_files_skips(tmp_path, monkeypatch):
    monkeypatch.setattr(go_checker.shutil, 'which', lambda _: '/usr/bin/go')
    unrelated = tmp_path / 'notes.txt'
    unrelated.write_text('hello\n')
    results = go_checker.GoGroup().run(_go_args(unrelated))
    assert [(r.passed, r.skipped) for r in results] == [(True, True)]


def test_missing_go_toolchain_fails_without_running_anything(tmp_path, monkeypatch):
    monkeypatch.setattr(go_checker.shutil, 'which', lambda _: None)
    monkeypatch.setattr(
        go_checker, 'ensure_golangci_lint', lambda *a, **k: pytest.fail('golangci-lint must not be installed')
    )
    source = _module(tmp_path, 'x') / 'main.go'
    source.write_text(CLEAN_MAIN)

    results = go_checker.GoGroup().run(_go_args(source))
    assert [(r.name, r.passed) for r in results] == [('go', False)]
    assert results[0].output == go_checker.GO_MISSING


# --- golangci-lint install ---


def test_target_platform_maps_machine_names(monkeypatch):
    for machine, arch in [('x86_64', 'amd64'), ('amd64', 'amd64'), ('aarch64', 'arm64'), ('arm64', 'arm64')]:
        monkeypatch.setattr(_golangci.platform, 'machine', lambda m=machine: m)
        monkeypatch.setattr(_golangci.platform, 'system', lambda: 'Linux')
        assert _golangci.target_platform() == ('linux', arch)

    monkeypatch.setattr(_golangci.platform, 'system', lambda: 'Darwin')
    monkeypatch.setattr(_golangci.platform, 'machine', lambda: 'arm64')
    assert _golangci.target_platform() == ('darwin', 'arm64')


def test_target_platform_unknown_is_none(monkeypatch):
    monkeypatch.setattr(_golangci.platform, 'system', lambda: 'Windows')
    monkeypatch.setattr(_golangci.platform, 'machine', lambda: 'AMD64')
    assert _golangci.target_platform() is None


def test_every_supported_platform_has_a_checksum():
    assert set(_golangci.CHECKSUMS) == {
        (os_name, arch) for os_name in ('linux', 'darwin') for arch in ('amd64', 'arm64')
    }


def test_unsupported_platform_returns_failed_result(tmp_path, monkeypatch):
    monkeypatch.setattr(_golangci.platform, 'system', lambda: 'Windows')
    monkeypatch.setattr(_golangci.platform, 'machine', lambda: 'AMD64')
    result = _golangci.ensure_golangci_lint(install_root=tmp_path / 'install')
    assert isinstance(result, Result)
    assert not result.passed
    assert 'Windows' in result.output


def _fake_tarball(path: Path, member_name: str = 'golangci-lint-2.13.2-linux-amd64/golangci-lint') -> Path:
    payload = b'#!/bin/sh\necho fake\n'
    with tarfile.open(path, 'w:gz') as archive:
        info = tarfile.TarInfo(member_name)
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    return path


def _serve(monkeypatch, tarball: Path) -> None:
    """Answer any urlopen with the bytes of tarball."""

    class _Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.close()

    monkeypatch.setattr(_golangci.urllib.request, 'urlopen', lambda *a, **k: _Response(tarball.read_bytes()))


def test_install_extracts_only_the_binary(tmp_path, monkeypatch):
    tarball = _fake_tarball(tmp_path / 'src.tar.gz')
    monkeypatch.setitem(_golangci.CHECKSUMS, ('linux', 'amd64'), hashlib.sha256(tarball.read_bytes()).hexdigest())
    monkeypatch.setattr(_golangci, 'target_platform', lambda: ('linux', 'amd64'))
    _serve(monkeypatch, tarball)

    install_root = tmp_path / 'install'
    binary = _golangci.ensure_golangci_lint(install_root=install_root)
    assert isinstance(binary, Path)
    assert binary.read_bytes() == b'#!/bin/sh\necho fake\n'
    assert binary.stat().st_mode & 0o111
    install_dir = install_root / f'golangci-lint-{_golangci.VERSION}'
    assert sorted(p.name for p in install_dir.iterdir()) == ['asset', 'golangci-lint']

    # The stamp makes a second call a no-op, so the download is never repeated.
    monkeypatch.setattr(
        _golangci.urllib.request, 'urlopen', lambda *a, **k: pytest.fail('install must not re-download')
    )
    assert _golangci.ensure_golangci_lint(install_root=install_root) == binary


def test_install_rejects_a_checksum_mismatch(tmp_path, monkeypatch):
    tarball = _fake_tarball(tmp_path / 'src.tar.gz')
    monkeypatch.setitem(_golangci.CHECKSUMS, ('linux', 'amd64'), '00' * 32)
    monkeypatch.setattr(_golangci, 'target_platform', lambda: ('linux', 'amd64'))
    _serve(monkeypatch, tarball)

    install_root = tmp_path / 'install'
    result = _golangci.ensure_golangci_lint(install_root=install_root)
    assert isinstance(result, Result)
    assert not result.passed
    assert 'sha256 mismatch' in result.output
    assert not (install_root / f'golangci-lint-{_golangci.VERSION}' / 'golangci-lint').exists()


def test_install_reports_a_tarball_without_the_binary(tmp_path, monkeypatch):
    tarball = _fake_tarball(tmp_path / 'src.tar.gz', member_name='somewhere/README.md')
    monkeypatch.setitem(_golangci.CHECKSUMS, ('linux', 'amd64'), hashlib.sha256(tarball.read_bytes()).hexdigest())
    monkeypatch.setattr(_golangci, 'target_platform', lambda: ('linux', 'amd64'))
    _serve(monkeypatch, tarball)

    result = _golangci.ensure_golangci_lint(install_root=tmp_path / 'install')
    assert isinstance(result, Result)
    assert 'no golangci-lint executable' in result.output


def test_install_failure_short_circuits_linting(tmp_path, monkeypatch):
    monkeypatch.setattr(go_checker.shutil, 'which', lambda _: '/usr/bin/go')
    failure = Result(name='golangci-lint', passed=False, output='no release for this platform')
    monkeypatch.setattr(go_checker, 'ensure_golangci_lint', lambda *a, **k: failure)
    monkeypatch.setattr(go_checker, 'format_module', lambda *a: pytest.fail('must not format'))
    monkeypatch.setattr(go_checker, 'lint_module', lambda *a: pytest.fail('must not lint'))
    source = _module(tmp_path, 'x') / 'main.go'
    source.write_text(CLEAN_MAIN)

    assert go_checker.GoGroup().run(_go_args(source)) == [failure]


# --- end to end ---


@pytest.mark.network
@needs_go
def test_clean_module_passes(tmp_path):
    source = _module(tmp_path, 'clean') / 'main.go'
    source.write_text(CLEAN_MAIN)
    assert runner.main(['go', str(source)]) == 0


@pytest.mark.network
@needs_go
def test_bundled_test_files_module_is_clean():
    module = _PROJECT_ROOT / 'test_files' / 'go'
    assert runner.main(['go', str(module / 'main.go'), str(module / 'go.mod')]) == 0


@pytest.mark.network
@needs_go
def test_missing_import_is_added_and_reported(tmp_path):
    """goimports resolves a standard-library reference, so the file is rewritten for re-staging."""
    source = _module(tmp_path, 'noimport') / 'main.go'
    source.write_text('// Package main is a fixture.\npackage main\n\nfunc main() {\n\tfmt.Println("x")\n}\n')

    assert runner.main(['go', str(source)]) == 1
    assert 'import "fmt"' in source.read_text()


@pytest.mark.network
@needs_go
def test_undefined_symbol_fails_lint(tmp_path):
    source = _module(tmp_path, 'broken') / 'main.go'
    source.write_text('// Package main is a fixture.\npackage main\n\nfunc main() {\n\tmissing()\n}\n')
    results = go_checker.GoGroup().run(_go_args(source))
    lint = next(r for r in results if r.name == 'golangci-lint run')
    assert not lint.passed
    assert 'undefined: missing' in lint.output
    # Paths are relative to the module root.
    assert '../' not in lint.output


@pytest.mark.network
@needs_go
def test_unformatted_file_is_rewritten_and_reported(tmp_path):
    source = _module(tmp_path, 'unformatted') / 'main.go'
    source.write_text('// Package main is a fixture.\npackage main\n\nfunc main() {\n\n\tx := 1\n\t_ = x\n}\n')
    results = go_checker.GoGroup().run(_go_args(source))
    fmt_result = next(r for r in results if r.name == 'golangci-lint fmt')
    assert not fmt_result.passed
    assert 'please re-stage and recommit' in fmt_result.output
    assert '\n\n\tx := 1' not in source.read_text()


@pytest.mark.network
@needs_go
def test_unparseable_file_is_left_to_the_linter(tmp_path):
    """A file gofumpt cannot parse passes fmt untouched and fails run with the syntax error."""
    source = _module(tmp_path, 'syntax') / 'main.go'
    source.write_text('// Package main is a fixture.\npackage main\n\nfunc main() {\n')
    results = go_checker.GoGroup().run(_go_args(source))

    fmt_result = next(r for r in results if r.name == 'golangci-lint fmt')
    assert fmt_result.passed
    assert source.read_text() == '// Package main is a fixture.\npackage main\n\nfunc main() {\n'

    lint = next(r for r in results if r.name == 'golangci-lint run')
    assert not lint.passed
    assert 'syntax error' in lint.output


@pytest.mark.network
@needs_go
def test_untidy_go_mod_fails(tmp_path):
    root = _module(tmp_path, 'untidy')
    (root / 'main.go').write_text(CLEAN_MAIN)
    (root / 'go.mod').write_text(
        'module example.com/untidy\n\ngo 1.23\n\nrequire github.com/pkg/errors v0.9.1\n',
    )
    result = go_checker.tidy_module(root)
    assert not result.passed
    assert 'errors' in result.output
