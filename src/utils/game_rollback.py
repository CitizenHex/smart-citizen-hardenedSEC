"""Transactional snapshots for the small set of game files Smart Citizen edits."""
from __future__ import annotations

import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path


MANIFEST = "manifest.json"
SNAPSHOT_PREFIX = "game_snapshot_"


def _sha256(path: Path) -> str:
    """Return a streaming SHA-256 without loading a game file into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_game_snapshot(targets: dict[str, Path], backups_dir: Path, keep: int = 5) -> Path:
    """Record existing/missing state for every managed game file."""
    backups_dir = Path(backups_dir)
    backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    snapshot = backups_dir / f"{SNAPSHOT_PREFIX}{stamp}"
    suffix = 0
    while True:
        try:
            snapshot.mkdir()
            break
        except FileExistsError:
            suffix += 1
            snapshot = backups_dir / f"{SNAPSHOT_PREFIX}{stamp}_{suffix}"
    manifest = {"schema": 2, "files": {}}
    for name, raw_target in sorted(targets.items()):
        target = Path(raw_target).resolve()
        existed = target.is_file()
        entry = {"target": str(target), "existed": existed}
        if existed:
            saved_name = f"{name}.original"
            saved = snapshot / saved_name
            shutil.copy2(target, saved)
            # Validate the just-created recovery copy before an Apply may
            # change anything. A bad/partial backup is worse than no backup.
            source_hash = _sha256(target)
            saved_hash = _sha256(saved)
            if saved_hash != source_hash:
                raise OSError(f"Backup verification failed for {target}")
            entry["saved"] = saved_name
            entry["sha256"] = saved_hash
        manifest["files"][name] = entry
    (snapshot / MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    snapshots = sorted(
        (p for p in backups_dir.glob(f"{SNAPSHOT_PREFIX}*") if p.is_dir()),
        key=lambda p: p.name,
    )
    for old in snapshots[:-max(1, keep)]:
        shutil.rmtree(old)
    return snapshot


def latest_game_snapshot(backups_dir: Path) -> Path | None:
    snapshots = sorted(
        (p for p in Path(backups_dir).glob(f"{SNAPSHOT_PREFIX}*") if p.is_dir()),
        key=lambda p: p.name,
        reverse=True,
    )
    return snapshots[0] if snapshots else None


def restore_game_snapshot(snapshot: Path, targets: dict[str, Path]) -> list[str]:
    """Restore one verified snapshot and return human-readable actions."""
    snapshot = Path(snapshot)
    manifest = json.loads((snapshot / MANIFEST).read_text(encoding="utf-8"))
    if manifest.get("schema") not in {1, 2} or not isinstance(manifest.get("files"), dict):
        raise ValueError("Unsupported or corrupt game rollback snapshot")

    actions = []
    for name, raw_target in sorted(targets.items()):
        target = Path(raw_target).resolve()
        entry = manifest["files"].get(name)
        if not isinstance(entry, dict) or Path(entry.get("target", "")).resolve() != target:
            raise ValueError(f"Snapshot target does not match the active game path: {name}")
        if entry.get("existed"):
            saved = snapshot / entry.get("saved", "")
            if not saved.is_file() or saved.parent != snapshot.resolve():
                raise ValueError(f"Snapshot is missing a safe backup for: {name}")
            expected_hash = entry.get("sha256")
            if manifest.get("schema") == 2:
                if not isinstance(expected_hash, str) or _sha256(saved) != expected_hash:
                    raise ValueError(f"Snapshot integrity check failed for: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(saved, target)
            if manifest.get("schema") == 2 and _sha256(target) != expected_hash:
                raise OSError(f"Rollback write verification failed for: {name}")
            actions.append(f"Restored {target}")
        elif target.exists():
            target.unlink()
            actions.append(f"Removed Smart Citizen-created {target}")
        else:
            actions.append(f"Already absent: {target}")
    return actions
