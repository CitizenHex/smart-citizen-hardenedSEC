"""Tests for src.utils.dataforge_patcher."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from utils.dataforge_patcher import apply_patches


def _records_root(tmp_path: Path) -> Path:
    """Create the DataForge records/ layout the patcher expects."""
    root = tmp_path / "dataforge" / "raw" / "libs" / "foundry" / "records"
    root.mkdir(parents=True)
    return root


def _write_patch(patch_dir: Path, subpath: str, body: dict) -> Path:
    p = patch_dir / subpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(body), encoding="utf-8")
    return p


_CONTRACT_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<root>
  <Contract debugName="Hockrow_FacilityDelve_P2M4-Stanton4_Repeat">
    <paramOverrides>
      <stringParamOverrides>
        <ContractStringParam param="Title" value="@Hockrow_FacilityDelve_P2M4_Repeat_title" />
        <ContractStringParam param="Description" value="@Hockrow_FacilityDelve_P2M1_Repeat_desc" />
      </stringParamOverrides>
    </paramOverrides>
  </Contract>
  <Contract debugName="UnrelatedContract">
    <paramOverrides>
      <stringParamOverrides>
        <ContractStringParam param="Description" value="@SomeOther_desc" />
      </stringParamOverrides>
    </paramOverrides>
  </Contract>
</root>
"""


def _write_target(records: Path, subpath: str, body: str) -> Path:
    target = records / subpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target


_P2M4_EDIT = {
    "xpath": ".//Contract[@debugName='Hockrow_FacilityDelve_P2M4-Stanton4_Repeat']//ContractStringParam[@param='Description']",
    "attribute": "value",
    "expected": "@Hockrow_FacilityDelve_P2M1_Repeat_desc",
    "set": "@Hockrow_FacilityDelve_P2M4_Repeat_desc",
}


def test_apply_edit_rewrites_attribute(tmp_path: Path):
    records = _records_root(tmp_path)
    target = _write_target(records, "contracts/hockrowagency.xml", _CONTRACT_XML)
    patches = tmp_path / "patches"
    _write_patch(patches, "hockrow.patch.json", {
        "target": "contracts/hockrowagency.xml",
        "edits": [_P2M4_EDIT],
    })

    report = apply_patches(patches, tmp_path / "dataforge")

    assert report.edits_applied == 1
    assert report.files_rewritten == 1
    assert "@Hockrow_FacilityDelve_P2M4_Repeat_desc" in target.read_text(encoding="utf-8")
    assert "@Hockrow_FacilityDelve_P2M1_Repeat_desc" not in target.read_text(encoding="utf-8")


def test_apply_edit_is_idempotent(tmp_path: Path):
    records = _records_root(tmp_path)
    _write_target(records, "contracts/hockrowagency.xml", _CONTRACT_XML)
    patches = tmp_path / "patches"
    _write_patch(patches, "hockrow.patch.json", {
        "target": "contracts/hockrowagency.xml",
        "edits": [_P2M4_EDIT],
    })

    first = apply_patches(patches, tmp_path / "dataforge")
    second = apply_patches(patches, tmp_path / "dataforge")

    assert first.edits_applied == 1
    # Second run: value already matches `set`; should be a clean no-op
    assert second.edits_applied == 0
    assert second.edits_idempotent == 1
    assert second.files_rewritten == 0


def test_expected_mismatch_skips_with_warning(tmp_path: Path):
    records = _records_root(tmp_path)
    target = _write_target(records, "contracts/hockrowagency.xml",
                           _CONTRACT_XML.replace("@Hockrow_FacilityDelve_P2M1_Repeat_desc",
                                                 "@UpstreamAlreadyFixed_desc"))
    patches = tmp_path / "patches"
    _write_patch(patches, "hockrow.patch.json", {
        "target": "contracts/hockrowagency.xml",
        "edits": [_P2M4_EDIT],
    })

    report = apply_patches(patches, tmp_path / "dataforge")

    assert report.edits_applied == 0
    assert report.edits_skipped_mismatch == 1
    assert report.files_rewritten == 0
    # Target stayed as-is
    assert "@UpstreamAlreadyFixed_desc" in target.read_text(encoding="utf-8")


def test_missing_target_file_records_error(tmp_path: Path):
    _records_root(tmp_path)  # records dir exists but target file doesn't
    patches = tmp_path / "patches"
    _write_patch(patches, "missing.patch.json", {
        "target": "does/not/exist.xml",
        "edits": [_P2M4_EDIT],
    })

    report = apply_patches(patches, tmp_path / "dataforge")

    assert report.patches_seen == 1
    assert report.files_rewritten == 0
    assert any("does/not/exist.xml" in e for e in report.errors)


def test_missing_patches_dir_returns_empty_report(tmp_path: Path):
    _records_root(tmp_path)
    report = apply_patches(tmp_path / "nope", tmp_path / "dataforge")
    assert report.patches_seen == 0
    assert report.errors == []


def test_no_xpath_match_records_no_match(tmp_path: Path):
    records = _records_root(tmp_path)
    _write_target(records, "contracts/hockrowagency.xml", _CONTRACT_XML)
    patches = tmp_path / "patches"
    _write_patch(patches, "hockrow.patch.json", {
        "target": "contracts/hockrowagency.xml",
        "edits": [{
            **_P2M4_EDIT,
            "xpath": ".//Contract[@debugName='DoesNotExist']//ContractStringParam[@param='Description']",
        }],
    })

    report = apply_patches(patches, tmp_path / "dataforge")

    assert report.edits_no_match == 1
    assert report.edits_applied == 0


def test_unrelated_elements_left_alone(tmp_path: Path):
    records = _records_root(tmp_path)
    target = _write_target(records, "contracts/hockrowagency.xml", _CONTRACT_XML)
    patches = tmp_path / "patches"
    _write_patch(patches, "hockrow.patch.json", {
        "target": "contracts/hockrowagency.xml",
        "edits": [_P2M4_EDIT],
    })

    apply_patches(patches, tmp_path / "dataforge")

    # UnrelatedContract's Description must remain untouched
    assert "@SomeOther_desc" in target.read_text(encoding="utf-8")


def test_malformed_patch_recorded_as_error(tmp_path: Path):
    _records_root(tmp_path)
    patches = tmp_path / "patches"
    (patches).mkdir(parents=True)
    (patches / "bad.patch.json").write_text("{ not valid json", encoding="utf-8")

    report = apply_patches(patches, tmp_path / "dataforge")

    assert report.patches_seen == 1
    assert report.errors  # at least one error recorded
