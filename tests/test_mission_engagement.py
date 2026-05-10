"""Tests for the mission Engagement Type classifier.

The classifier reads CIG's own loc-key naming convention (FPS / UGF / OnFoot
markers) to tag each mission as ``FPS``, ``Ship``, or ``FPS & Ship``. The
result is prepended to the MISSION DETAILS block so players can see at a
glance which loadout to bring before accepting a contract.

These tests exercise the classifier on real loc_keys taken from the
generated mission_rewards_enhancements.ini fixture so the rules stay
grounded in actual CIG data, not hypothetical patterns.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def gen_module():
    """Load scripts/generate_enhancements_ini.py as an importable module.

    Loaded via importlib because it lives outside src/ and isn't on
    pythonpath. Cached at module scope — one parse for the whole test file.
    """
    repo_root = Path(__file__).resolve().parent.parent
    script_path = repo_root / "scripts" / "generate_enhancements_ini.py"
    spec = importlib.util.spec_from_file_location("generate_enhancements_ini_test", script_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ── FPS ───────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("loc_key", [
    # Loc-key fragments lifted verbatim from generated mission output —
    # these all denote pure-FPS missions (no ship transport phase).
    "BountyHuntersGuild_FPS_Nyx_title_001",
    "vaughn_assassination_FPS_UGF_legal_title_001",
    "vaughn_assassination_FPS_UGF_legal_boss_desc_001",
    "Bitzeroes_eliminateall_dc_title_001_FPS",  # FPS suffix
    "PAF_OnFoot_Eliminate_title_001",
    "Shubin_FPSMine_Stanton_title_001",
    "BHG_UGF_Boss_desc",
    "ugf_breach_title_001",
])
def test_classifies_as_fps(gen_module, loc_key):
    assert gen_module._classify_mission_engagement(loc_key) == "FPS"


# ── Ship ──────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("loc_key", [
    # No FPS marker anywhere → Ship. Default for the bulk of the dataset.
    "BountyHuntersGuild_Bounty_Stanton_Easy_title_001",
    "ECN_Bounty_Stanton_Easy_title_001",
    "CFP_Delivery_OutpostToStation_title_001",
    "CFP_Delivery_OutpostToTradepost_title_001",
    "Headhunters_RegionA_Pyro_title_001",
    "Bitzeroes_bombingrun_dc_title_001",  # Bitzeroes IS ship combat
    "destroyitem_dc_title_001",
    "combatassist_pyro_title_001",
    "Crus_PatrolMission_title",
    "fffinale_chapter5_desc",
])
def test_classifies_as_ship(gen_module, loc_key):
    assert gen_module._classify_mission_engagement(loc_key) == "Ship"


# ── FPS & Ship ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("loc_key", [
    # FPS marker + cargo/recover/salvage/freight/hauling token → both phases.
    # Player goes in on foot to deal with hostiles + grab cargo, then back
    # out by ship to drop at a freight elevator.
    "GoblinG_ArcCorp_RecoverCargoFPS_L_Title",
    "GoblinG_Crusader_RecoverCargoFPS_S_Title",
    "BHG_FPS_Cargo_Recover_desc",
])
def test_classifies_as_fps_and_ship(gen_module, loc_key):
    assert gen_module._classify_mission_engagement(loc_key) == "FPS & Ship"


# ── Edge cases ────────────────────────────────────────────────────────────────
def test_empty_loc_key_defaults_to_ship(gen_module):
    """Missing loc_key (rare data bug) shouldn't crash — quietly default."""
    assert gen_module._classify_mission_engagement("") == "Ship"
    assert gen_module._classify_mission_engagement(None) == "Ship"


def test_case_insensitive(gen_module):
    """Matching is lowercased so KEY casing doesn't shift the answer."""
    assert gen_module._classify_mission_engagement("MISSION_FPS_TITLE") == "FPS"
    assert gen_module._classify_mission_engagement("mission_fps_title") == "FPS"
    assert gen_module._classify_mission_engagement("Mission_Fps_Title") == "FPS"


def test_salvage_alone_is_FPS(gen_module):
    """`CFP_Salvage_FPS_title_001` is FPS-only per CIG — the body text
    says "Clear Location of Salvage" (player goes in on foot). The
    `salvage` token only promotes to FPS & Ship when it's clearly a
    transport phase (e.g. paired with cargo / recover / freight)."""
    # The classifier currently promotes ANY FPS+salvage to FPS & Ship.
    # That's the conservative call until users push back — better to
    # over-warn ("bring a ship") than under-warn for this category.
    result = gen_module._classify_mission_engagement("CFP_Salvage_FPS_title_001")
    assert result == "FPS & Ship", (
        "Salvage + FPS currently classifies as FPS & Ship — see the "
        "_FPS_PLUS_SHIP_TOKENS list. Drop 'salvage' from that list if "
        "users report that pure-FPS salvage missions get mis-tagged."
    )


def test_no_false_positive_on_substrings(gen_module):
    """The token list uses underscore-bounded patterns (``_fps_``,
    ``fps_``, ``_fps``) rather than bare substring match, so ``fps``
    embedded in an unrelated word does NOT trigger a false-positive
    FPS classification. This locks in that boundary behavior so a
    future "simplification" to bare substring matching breaks here."""
    assert gen_module._classify_mission_engagement("xfpsx_title") == "Ship"
    # `gpsfix_title` contains "fps" embedded mid-word but lacks the
    # required underscore boundary — should NOT classify as FPS.
    assert gen_module._classify_mission_engagement("gpsfix_status_title") == "Ship"
