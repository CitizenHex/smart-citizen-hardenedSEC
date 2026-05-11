"""
dataforge_diff.py — Diff-cache for the DataForge XML cache.

Usage
-----
After unforge writes the cache, call `update_manifest` to snapshot it.
Before running enhancement generators, call `dirty_categories` to find
out which ones actually need to re-run.

    from utils.dataforge_diff import update_manifest, dirty_categories

    # In EnhancementsGeneratorWorker / pak_extractor, after extraction:
    update_manifest(cache_dir)

    # Before each generator run:
    dirty = dirty_categories(cache_dir)
    # dirty == None  →  no prior manifest; run everything
    # dirty == set() →  nothing changed; skip everything
    # dirty == {"ships", "missions"} →  only re-run those two
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Optional

MANIFEST_FILE = ".diff_manifest.json"

# Maps category name → DataForge subtree prefixes it reads from.
# Mirrors DATAFORGE_KEEP_SUBPATHS in pak_extractor.py — keep in sync.
CATEGORY_SUBTREES: dict[str, list[str]] = {
    "ships":       ["entities/ships", "entities/spaceships"],
    "components":  ["entities/itemports", "entities/scitem"],
    "ship_weapons":["entities/scitem/weapons/spacecraft"],
    "fps_weapons": ["entities/scitem/weapons/fps"],
    "missions":    ["entities/missions", "libs/foundry/records/missions"],
    "commodities": ["entities/scitem/cargo", "libs/economy"],
    "journal":     ["libs/foundry/records/journal"],
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _hash_file(path: Path) -> str:
    """SHA-256 of file content, hex-encoded."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_snapshot(cache_dir: Path) -> dict[str, dict]:
    """
    Walk the dataforge cache and return a snapshot dict:
        { "relative/path.xml": {"mtime": float, "sha256": str}, ... }

    mtime is checked first; sha256 is only computed when mtime differs,
    keeping the hot path (nothing changed) fast.
    """
    snapshot: dict[str, dict] = {}
    for root, _, files in os.walk(cache_dir):
        for fname in files:
            if not fname.endswith(".xml"):
                continue
            abs_path = Path(root) / fname
            rel = str(abs_path.relative_to(cache_dir)).replace("\\", "/")
            snapshot[rel] = {
                "mtime": abs_path.stat().st_mtime,
                "sha256": _hash_file(abs_path),
            }
    return snapshot


def _manifest_path(cache_dir: Path) -> Path:
    return cache_dir / MANIFEST_FILE


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def update_manifest(cache_dir: Path) -> None:
    """
    Snapshot the current state of the DataForge cache and persist it.
    Call this *after* a successful extraction so the next run can diff
    against it.
    """
    cache_dir = Path(cache_dir)
    snapshot = _build_snapshot(cache_dir)
    with open(_manifest_path(cache_dir), "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)


def dirty_categories(cache_dir: Path) -> Optional[set[str]]:
    """
    Compare the current DataForge cache against the stored manifest and
    return the set of category names whose source XMLs have changed.

    Return values:
        None        — no prior manifest exists; treat all categories as dirty
        set()       — nothing changed; all generators can be skipped
        {"ships", …} — only these categories need to re-run
    """
    cache_dir = Path(cache_dir)
    manifest_file = _manifest_path(cache_dir)

    if not manifest_file.exists():
        return None  # first run — regenerate everything

    with open(manifest_file, encoding="utf-8") as f:
        old: dict[str, dict] = json.load(f)

    new = _build_snapshot(cache_dir)

    # Find changed paths (added, removed, or different hash)
    all_paths = set(old) | set(new)
    changed: set[str] = set()
    for rel in all_paths:
        if rel not in old or rel not in new:
            changed.add(rel)  # added or removed
        elif old[rel]["mtime"] != new[rel]["mtime"]:
            # mtime differs — confirm with hash before marking dirty
            if old[rel]["sha256"] != new[rel]["sha256"]:
                changed.add(rel)

    if not changed:
        return set()  # clean — skip all generators

    # Map changed paths → categories
    dirty: set[str] = set()
    for rel_path in changed:
        for category, subtrees in CATEGORY_SUBTREES.items():
            if any(rel_path.startswith(prefix) for prefix in subtrees):
                dirty.add(category)
                break

    return dirty