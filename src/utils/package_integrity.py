"""Verification for a portable Smart Citizen package.

The build creates ``package-integrity.json`` beside the executable after all
post-build cleanup has completed.  At startup a portable build verifies every
listed runtime file before the UI is created.  This is a local tamper and
corruption check; users should still verify the release ZIP's detached SHA-256
against the value published with the release.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path


MANIFEST_FILENAME = "package-integrity.json"
_MAX_MANIFEST_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True)
class PackageIntegrityResult:
    ok: bool
    message: str
    files_checked: int = 0
    package_dir: Path | None = None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def portable_package_dir() -> Path | None:
    """Return the frozen executable directory, or None in source/dev runs."""
    if not getattr(sys, "frozen", False):
        return None
    return Path(sys.executable).resolve().parent


def verify_portable_package(package_dir: Path | None = None) -> PackageIntegrityResult:
    """Verify every file listed in a portable package's local manifest."""
    package_dir = Path(package_dir) if package_dir is not None else portable_package_dir()
    if package_dir is None:
        return PackageIntegrityResult(True, "Not a frozen portable build.")
    manifest_path = package_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return PackageIntegrityResult(False, "Package integrity manifest is missing.", package_dir=package_dir)
    try:
        if manifest_path.stat().st_size > _MAX_MANIFEST_BYTES:
            raise ValueError("manifest is unexpectedly large")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = manifest["files"]
        if not isinstance(files, dict) or not files:
            raise ValueError("manifest contains no files")
        checked = 0
        root = package_dir.resolve()
        for relative, expected in files.items():
            if not isinstance(relative, str) or not isinstance(expected, dict):
                raise ValueError("manifest entry is invalid")
            target = (root / relative).resolve()
            if root not in target.parents:
                raise ValueError("manifest contains an unsafe path")
            if not target.is_file():
                return PackageIntegrityResult(False, f"Required package file is missing: {relative}", checked, root)
            if target.stat().st_size != expected.get("size"):
                return PackageIntegrityResult(False, f"Package file size changed: {relative}", checked, root)
            if _sha256(target) != expected.get("sha256"):
                return PackageIntegrityResult(False, f"Package file hash changed: {relative}", checked, root)
            checked += 1
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return PackageIntegrityResult(False, f"Package integrity manifest is invalid: {exc}", package_dir=package_dir)
    return PackageIntegrityResult(True, f"Verified {checked} packaged files.", checked, root)
