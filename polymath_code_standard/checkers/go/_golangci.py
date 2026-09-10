# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Install a pinned golangci-lint release into the hook's virtualenv.

`ensure_golangci_lint()` returns the path to the binary, or a failed `Result`
describing what went wrong.
"""

import fcntl
import hashlib
import platform
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

from polymath_code_standard.checker import Result

VERSION = '2.13.2'

# sha256 of each release tarball, from golangci-lint-<VERSION>-checksums.txt.
# Bump these together with VERSION.
CHECKSUMS = {
    ('darwin', 'amd64'): '8a13aaf9cbbb1dee52824e862cf0d0720e5bb97c1f4260d1e51623a09492b57b',
    ('darwin', 'arm64'): 'f4bf83f0b64f055c42b28fc9a38861839f69c096e61c788e72dfaae412011789',
    ('linux', 'amd64'): '2277d43b98ec0054280f2ac26b53268bae97682444678a59a657dd565da021d6',
    ('linux', 'arm64'): 'a2a4e0065aa41be71f7c5ac90f271b61751331e5d04314e62afe4027855f0893',
}

RELEASE_URL = 'https://github.com/golangci/golangci-lint/releases/download/v{version}/{asset}.tar.gz'

_SYSTEMS = {'Linux': 'linux', 'Darwin': 'darwin'}
_MACHINES = {'x86_64': 'amd64', 'amd64': 'amd64', 'aarch64': 'arm64', 'arm64': 'arm64'}

INSTALL_ROOT = Path(sys.prefix) / 'polymath-go'

NAME = 'golangci-lint'


def target_platform() -> tuple[str, str] | None:
    """Return the (os, arch) pair naming this machine's release asset."""
    system = _SYSTEMS.get(platform.system())
    machine = _MACHINES.get(platform.machine().lower())
    return (system, machine) if system and machine else None


def asset_name(version: str, os_name: str, arch: str) -> str:
    return f'golangci-lint-{version}-{os_name}-{arch}'


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def extract_binary(tarball: Path, dest: Path) -> Result | None:
    """Extract the golangci-lint executable from a release tarball to dest.

    Returns a failed Result when the tarball holds no such member.
    """
    with tarfile.open(tarball, 'r:gz') as archive:
        member = next((m for m in archive.getmembers() if m.isfile() and Path(m.name).name == NAME), None)
        if member is None:
            return Result(name=NAME, passed=False, output=f'{tarball.name} contains no {NAME} executable.')
        source = archive.extractfile(member)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('wb') as handle:
            handle.write(source.read())
    dest.chmod(0o755)
    return None


def _download_and_verify(url: str, expected_sha256: str, dest_dir: Path) -> Path | Result:
    tarball = dest_dir / 'download.tar.gz'
    try:
        with urllib.request.urlopen(url, timeout=60) as response, tarball.open('wb') as handle:
            handle.write(response.read())
    except (urllib.error.URLError, OSError) as exc:
        return Result(name=NAME, passed=False, output=f'Failed to download {url}: {exc}')

    actual = _sha256(tarball)
    if actual != expected_sha256:
        tarball.unlink(missing_ok=True)
        return Result(
            name=NAME,
            passed=False,
            output=f'sha256 mismatch for {url}\n  expected {expected_sha256}\n  got      {actual}',
        )
    return tarball


def ensure_golangci_lint(version: str = VERSION, install_root: Path = INSTALL_ROOT) -> Path | Result:
    """Return the path to the pinned golangci-lint binary, downloading it on first use."""
    target = target_platform()
    if target is None or target not in CHECKSUMS:
        return Result(
            name=NAME,
            passed=False,
            output=(
                f'No golangci-lint release for {platform.system()} {platform.machine()}. '
                f'Supported: {", ".join(f"{o}/{a}" for o, a in sorted(CHECKSUMS))}.'
            ),
        )
    os_name, arch = target

    asset = asset_name(version, os_name, arch)
    install_dir = install_root / f'golangci-lint-{version}'
    binary = install_dir / NAME
    stamp = install_dir / 'asset'
    if binary.is_file() and stamp.is_file() and stamp.read_text().strip() == asset:
        return binary

    # pre-commit runs one hook in parallel batches, so the install is serialized across processes.
    install_root.mkdir(parents=True, exist_ok=True)
    lock_path = install_root.with_suffix('.lock')
    with lock_path.open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if binary.is_file() and stamp.is_file() and stamp.read_text().strip() == asset:
            return binary

        install_dir.mkdir(parents=True, exist_ok=True)
        tarball = _download_and_verify(RELEASE_URL.format(version=version, asset=asset), CHECKSUMS[target], install_dir)
        if isinstance(tarball, Result):
            return tarball
        try:
            failure = extract_binary(tarball, binary)
        finally:
            tarball.unlink(missing_ok=True)
        if failure is not None:
            return failure

        stamp.write_text(f'{asset}\n')
        return binary
