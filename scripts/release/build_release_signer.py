"""Build the offline Smart Citizen release-signing utility.

The resulting EXE is intended for the separate trusted signing machine.  It
contains no release key and performs no network activity; it only generates an
Ed25519 key pair or signs release-manifest JSON supplied by the operator.
"""
from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

import PyInstaller.__main__


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts" / "release" / "sign_release_manifest.py"
DIST = ROOT / "dist" / "release-signer"
BUILD = ROOT / "build" / "release-signer"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    # Never remove a prior signing tool automatically. It is an operator-facing
    # security tool and output replacement should be a deliberate action.
    DIST.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    output = DIST / "SmartCitizen-ReleaseSigner.exe"
    if output.exists():
        raise SystemExit(f"Refusing to overwrite {output}. Move it aside first.")
    PyInstaller.__main__.run([
        str(SOURCE), "--name", "SmartCitizen-ReleaseSigner", "--onefile",
        "--console", "--paths", str(ROOT), "--distpath", str(DIST),
        "--workpath", str(BUILD), "--specpath", str(BUILD),
        "--clean", "--noconfirm",
    ])
    hash_path = output.with_suffix(".exe.sha256")
    hash_path.write_text(sha256(output) + "  " + output.name + "\n", encoding="ascii")
    print(f"Built {output}")
    print(f"SHA-256 recorded in {hash_path}")


if __name__ == "__main__":
    main()
