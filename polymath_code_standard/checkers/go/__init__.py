# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
import argparse
import importlib.resources
import shutil
from collections import defaultdict
from pathlib import Path

from polymath_code_standard.checker import CheckerGroup, Result, check_group, filter_files, run

from ._golangci import ensure_golangci_lint

# Config files bundled alongside this checker
CONFIG_DIR = importlib.resources.files(__package__)

CONFIG = Path(str(CONFIG_DIR / 'golangci.yml'))

GO_MISSING = 'Go toolchain not found on PATH. Install Go from https://go.dev/dl and re-run.'


def module_root(path: str) -> Path | None:
    """Return the nearest ancestor directory of path holding a go.mod."""
    for directory in Path(path).resolve().parents:
        if (directory / 'go.mod').is_file():
            return directory
    return None


def group_by_module(go_files: list[str]) -> tuple[dict[Path, list[Path]], list[str]]:
    """Split Go sources into per-module-root paths relative to that root, plus the files outside any module.

    Vendored sources are dropped.
    """
    modules: dict[Path, list[Path]] = defaultdict(list)
    orphans = []
    for filepath in go_files:
        root = module_root(filepath)
        if root is None:
            orphans.append(filepath)
            continue
        relative = Path(filepath).resolve().relative_to(root)
        if 'vendor' not in relative.parts:
            modules[root].append(relative)
    return dict(modules), orphans


def package_dirs(relative_files: list[Path]) -> list[str]:
    """Return the distinct package directories of relative_files as golangci-lint package patterns."""
    parents = {f.parent for f in relative_files}
    return sorted('.' if p == Path('.') else f'./{p.as_posix()}' for p in parents)


def format_module(binary: Path, config: Path, root: Path, relative_files: list[Path]) -> Result:
    """Check gofumpt and goimports formatting under root, then rewrite the files that need it."""
    args = [str(binary), 'fmt', '--config', str(config)]
    paths = [f.as_posix() for f in relative_files]
    # `fmt --diff` exits 1 only when it prints a diff.
    # An unparseable file is a warning with exit 0 and is left for `run` to report.
    check = run('golangci-lint fmt', args + ['--diff'], paths, cwd=str(root))
    if check.passed:
        return check
    run('golangci-lint fmt', args, paths, cwd=str(root))
    return Result(
        name='golangci-lint fmt',
        passed=False,
        output=check.output + '\n(files have been reformatted — please re-stage and recommit)',
        cmd=check.cmd,
    )


def lint_module(binary: Path, config: Path, root: Path, relative_files: list[Path]) -> Result:
    """Lint the packages under root that contain relative_files."""
    return run(
        'golangci-lint run',
        [str(binary), 'run', '--config', str(config)],
        package_dirs(relative_files),
        cwd=str(root),
    )


def tidy_module(root: Path) -> Result:
    """Report the go.mod and go.sum edits `go mod tidy` would make in root."""
    return run('go mod tidy', ['go', 'mod', 'tidy', '-diff'], None, cwd=str(root))


@check_group
class GoGroup(CheckerGroup):
    name = 'go'

    def run(self, args: argparse.Namespace) -> list[Result]:
        if shutil.which('go') is None:
            return [Result(name='go', passed=False, output=GO_MISSING)]

        modules, orphans = group_by_module(filter_files(args.files, frozenset({'go'})))
        module_files = filter_files(args.files, frozenset({'go-mod', 'go-sum'}))

        results = [
            Result(name='go', passed=False, output=f'{path}: no go.mod in any parent directory.') for path in orphans
        ]

        if modules:
            binary = ensure_golangci_lint()
            if isinstance(binary, Result):
                return results + [binary]
            for root, relative_files in sorted(modules.items()):
                results.append(format_module(binary, CONFIG, root, relative_files))
                results.append(lint_module(binary, CONFIG, root, relative_files))

        results.extend(tidy_module(d) for d in sorted({Path(f).resolve().parent for f in module_files}))

        if not results:
            return [Result(name='go', passed=True, skipped=True)]
        return results
