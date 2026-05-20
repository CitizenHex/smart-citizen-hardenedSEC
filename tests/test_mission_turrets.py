"""Tests for mission turret detection.

Two CIG signal sources, sourced from inspecting the live 4.7 DataForge
cache:
- ``SpawnDescription_ShipGroup Name="Turrets"`` — the spawn-data path,
  used by ~119/2558 pu_missions
- ``MissionProperty missionVariableName="OverrideTurretHosility_BP"``
  (with CIG's "Hosility" typo) — the explicit-hostility-override path,
  used by ~8 missions

Tests fabricate minimal XML snippets matching those structures so the
classifier doesn't depend on a populated DataForge cache.
"""
from __future__ import annotations

import importlib.util
import sys
from lxml import etree as ET
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def gen_module():
    repo_root = Path(__file__).resolve().parent.parent
    script_path = repo_root / "scripts" / "generate_enhancements_ini.py"
    spec = importlib.util.spec_from_file_location("generate_enhancements_ini_test", script_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_root(body: str) -> ET.Element:
    """Parse an XML fragment wrapped in a synthetic root element."""
    return ET.fromstring(f"<MissionBrokerEntry>{body}</MissionBrokerEntry>")


# ── No turret references ──────────────────────────────────────────────────────
def test_no_turret_references_returns_none(gen_module):
    """Mission with neither spawn group nor override property → None."""
    root = _make_root(
        '<spawnDescriptions>'
        '<SpawnDescription_ShipGroup Name="Hostiles">'
        '<ships><SpawnDescription_Ship concurrentAmount="3"/></ships>'
        '</SpawnDescription_ShipGroup>'
        '</spawnDescriptions>'
    )
    assert gen_module._extract_turret_info(root) is None


# ── Spawn-group turrets (the common case) ─────────────────────────────────────
def test_spawn_group_turrets_default_hostile(gen_module):
    """Turret spawn group with no explicit override → hostile (default)."""
    root = _make_root(
        '<spawnDescriptions>'
        '<SpawnDescription_ShipGroup Name="Turrets">'
        '<ships>'
        '<SpawnDescription_Ship concurrentAmount="3"/>'
        '<SpawnDescription_Ship concurrentAmount="2"/>'
        '</ships>'
        '</SpawnDescription_ShipGroup>'
        '</spawnDescriptions>'
    )
    assert gen_module._extract_turret_info(root) == "5 (hostile)"


def test_turret_substring_match_in_group_name(gen_module):
    """`PerimeterTurrets` and similar variants are still recognised."""
    root = _make_root(
        '<spawnDescriptions>'
        '<SpawnDescription_ShipGroup Name="PerimeterTurrets">'
        '<ships><SpawnDescription_Ship concurrentAmount="4"/></ships>'
        '</SpawnDescription_ShipGroup>'
        '</spawnDescriptions>'
    )
    assert gen_module._extract_turret_info(root) == "4 (hostile)"


def test_zero_concurrent_amount_returns_none(gen_module):
    """A turret group with concurrentAmount=0 isn't really there."""
    root = _make_root(
        '<spawnDescriptions>'
        '<SpawnDescription_ShipGroup Name="Turrets">'
        '<ships><SpawnDescription_Ship concurrentAmount="0"/></ships>'
        '</SpawnDescription_ShipGroup>'
        '</spawnDescriptions>'
    )
    assert gen_module._extract_turret_info(root) is None


# ── Explicit hostility override ───────────────────────────────────────────────
def test_explicit_hostile_override_with_count(gen_module):
    """OverrideTurretHosility_BP=1 + spawn count → "(hostile)" qualifier."""
    root = _make_root(
        '<MissionProperty missionVariableName="OverrideTurretHosility_BP">'
        '<value><MissionPropertyValue_Boolean value="1"/></value>'
        '</MissionProperty>'
        '<spawnDescriptions>'
        '<SpawnDescription_ShipGroup Name="Turrets">'
        '<ships><SpawnDescription_Ship concurrentAmount="2"/></ships>'
        '</SpawnDescription_ShipGroup>'
        '</spawnDescriptions>'
    )
    assert gen_module._extract_turret_info(root) == "2 (hostile)"


def test_explicit_friendly_override_with_count(gen_module):
    """OverrideTurretHosility_BP=0 → "(friendly)" qualifier even though
    the spawn group is named "Turrets". Hypothetical case — not observed
    in the live 4.7 dataset, but covered defensively in case CIG ever
    ships one (the property is a Boolean with both values legal)."""
    root = _make_root(
        '<MissionProperty missionVariableName="OverrideTurretHosility_BP">'
        '<value><MissionPropertyValue_Boolean value="0"/></value>'
        '</MissionProperty>'
        '<spawnDescriptions>'
        '<SpawnDescription_ShipGroup Name="Turrets">'
        '<ships><SpawnDescription_Ship concurrentAmount="3"/></ships>'
        '</SpawnDescription_ShipGroup>'
        '</spawnDescriptions>'
    )
    assert gen_module._extract_turret_info(root) == "3 (friendly)"


def test_override_only_no_spawn_count(gen_module):
    """Mission has the override property but no spawn group with turrets
    (e.g. environmental turrets handled by the location, not the mission).
    Output uses "present" instead of a count."""
    root = _make_root(
        '<MissionProperty missionVariableName="OverrideTurretHosility_BP">'
        '<value><MissionPropertyValue_Boolean value="1"/></value>'
        '</MissionProperty>'
    )
    assert gen_module._extract_turret_info(root) == "present (hostile)"


# ── Interaction with _extract_spawn_counts ────────────────────────────────────
def test_turrets_excluded_from_enemy_count(gen_module):
    """Turret ship-groups should NOT inflate the Enemies tally; otherwise
    the MISSION DETAILS block would double-count them (once as Enemies,
    once as Turrets)."""
    root = _make_root(
        '<spawnDescriptions>'
        '<SpawnDescription_ShipGroup Name="Hostiles">'
        '<ships><SpawnDescription_Ship concurrentAmount="4"/></ships>'
        '</SpawnDescription_ShipGroup>'
        '<SpawnDescription_ShipGroup Name="Turrets">'
        '<ships><SpawnDescription_Ship concurrentAmount="3"/></ships>'
        '</SpawnDescription_ShipGroup>'
        '</spawnDescriptions>'
    )
    breakdown = gen_module._extract_spawn_counts(root)
    # The non-turret hostile group contributes its 4 ships to Hostiles. The
    # ``Hostiles`` group name routes to the "Hostiles" label via the generic
    # hostile keyword.
    assert breakdown[gen_module.SPAWN_HOSTILE] == {"Hostiles": 4}, (
        "Turrets should not be counted as Hostiles"
    )
    assert breakdown[gen_module.SPAWN_FRIENDLY] == {}
    assert breakdown[gen_module.SPAWN_OBJECTIVE] == {}
    assert breakdown[gen_module.SPAWN_UNKNOWN] == {}
    # Turret count surfaces via the dedicated extractor instead.
    assert gen_module._extract_turret_info(root) == "3 (hostile)"
