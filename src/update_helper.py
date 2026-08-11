"""Temporary helper used by the portable app to install a verified update."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from src.utils.package_integrity import verify_portable_package

MAX_FILES = 2_000
MAX_UNCOMPRESSED = 600 * 1024 * 1024


def safe_extract(zip_path: Path, stage: Path) -> None:
    """Extract a release ZIP with traversal, count, and size limits."""
    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES or sum(info.file_size for info in infos) > MAX_UNCOMPRESSED:
            raise ValueError("update archive exceeds safe limits")
        root = stage.resolve()
        for info in infos:
            target = (root / info.filename).resolve()
            if root not in target.parents or info.is_dir():
                if info.is_dir() and root in target.parents:
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                raise ValueError("update archive contains an unsafe path")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as destination:
                shutil.copyfileobj(source, destination)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wait_for_exit(pid: int) -> None:
    while True:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.25)


def install(zip_path: Path, app_dir: Path, pid: int, relaunch: str,
            expected_sha256: str, expected_size: int) -> None:
    """Install a download already approved by the main app.

    The helper repeats the signed size/hash check so that a ZIP cannot be
    swapped between the GUI's verification and this separate process.
    """
    if expected_size < 1 or zip_path.stat().st_size != expected_size:
        raise RuntimeError("update ZIP size does not match the approved release")
    if sha256_file(zip_path).lower() != expected_sha256.lower():
        raise RuntimeError("update ZIP hash does not match the approved release")
    work = app_dir.parent / ".smartcitizen-update-staging"
    if work.exists():
        raise RuntimeError("an earlier update staging folder is still present")
    stage = work / "package"
    safe_extract(zip_path, stage)
    integrity = verify_portable_package(stage)
    if not integrity.ok:
        raise RuntimeError("downloaded package failed integrity verification: " + integrity.message)
    wait_for_exit(pid)
    backup = work / "backup"
    backup.mkdir(parents=True)
    manifest_file = app_dir / "package-integrity.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    old_files = manifest["files"]
    new_files = json.loads((stage / "package-integrity.json").read_text(encoding="utf-8"))["files"]
    previous_manifest = backup / "package-integrity.json"
    shutil.copy2(manifest_file, previous_manifest)
    moved: list[Path] = []
    installed: list[Path] = []
    try:
        for relative in old_files:
            old = app_dir / relative
            if old.is_file():
                saved = backup / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                os.replace(old, saved)
                moved.append(Path(relative))
        for relative in new_files:
            source = stage / relative
            target = app_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            installed.append(Path(relative))
        shutil.copy2(stage / "package-integrity.json", manifest_file)
        if not verify_portable_package(app_dir).ok:
            raise RuntimeError("installed package failed final integrity verification")
    except Exception:
        # Restore the former files and manifest before reporting the failure.
        # User data is outside the package manifest and is never touched.
        for relative in installed:
            target = app_dir / relative
            if relative not in old_files and target.is_file():
                target.unlink()
        for relative in moved:
            saved = backup / relative
            target = app_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if saved.is_file():
                os.replace(saved, target)
        shutil.copy2(previous_manifest, manifest_file)
        raise
    # Staging contains only the verified ZIP extraction and the recoverable
    # pre-update backup. Remove that exact temporary directory after success;
    # user data lives under app_dir/data and is never part of this cleanup.
    shutil.rmtree(work)
    subprocess.Popen([str(app_dir / relaunch)], cwd=app_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--app-dir", required=True, type=Path)
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--relaunch", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--size", required=True, type=int)
    args = parser.parse_args()
    install(args.zip.resolve(), args.app_dir.resolve(), args.pid, args.relaunch,
            args.sha256, args.size)


if __name__ == "__main__":
    main()
