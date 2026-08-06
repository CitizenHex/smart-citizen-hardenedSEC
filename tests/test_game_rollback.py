"""Full game-side snapshot and emergency rollback tests."""
from pathlib import Path

import json
import pytest

from src.utils.game_rollback import (
    MANIFEST,
    create_game_snapshot,
    latest_game_snapshot,
    restore_game_snapshot,
)


pytestmark = [pytest.mark.unit, pytest.mark.regression]


def _targets(root: Path) -> dict[str, Path]:
    return {
        "global_ini": root / "data" / "Localization" / "english" / "global.ini",
        "languages_ini": root / "data" / "languages.ini",
        "user_cfg": root / "user.cfg",
    }


def test_rollback_restores_originals_and_removes_new_files(tmp_path):
    targets = _targets(tmp_path / "LIVE")
    targets["user_cfg"].parent.mkdir(parents=True)
    targets["user_cfg"].write_text("original=true\n", encoding="utf-8")

    snapshot = create_game_snapshot(targets, tmp_path / "backups")
    for target in targets.values():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("smart-citizen-change\n", encoding="utf-8")

    actions = restore_game_snapshot(snapshot, targets)

    assert targets["user_cfg"].read_text(encoding="utf-8") == "original=true\n"
    assert not targets["global_ini"].exists()
    assert not targets["languages_ini"].exists()
    assert len(actions) == 3


def test_snapshot_target_tampering_is_rejected(tmp_path):
    targets = _targets(tmp_path / "LIVE")
    snapshot = create_game_snapshot(targets, tmp_path / "backups")
    manifest_path = snapshot / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["user_cfg"]["target"] = str(tmp_path / "outside.cfg")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match"):
        restore_game_snapshot(snapshot, targets)


def test_latest_snapshot_and_rotation(tmp_path):
    targets = _targets(tmp_path / "LIVE")
    backups = tmp_path / "backups"
    snapshots = [create_game_snapshot(targets, backups, keep=2) for _ in range(3)]

    assert latest_game_snapshot(backups) == snapshots[-1]
    assert not snapshots[0].exists()
    assert snapshots[1].exists() and snapshots[2].exists()
