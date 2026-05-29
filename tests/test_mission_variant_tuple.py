"""Regression guard for the contract mission-variant tuple shape.

Contract generators store one tuple per mission variant under
``contractgen_missions[title_key]``. The 1.4.2 rep-tier-names change grew
the tuple from 10 → 11 elements (adding ``rank_name`` at position 10).
These tests lock the tuple width at every consumer so the next refactor
can't slip a similar drift through.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.regression]


@pytest.fixture(scope="module")
def gen_module():
    repo_root = Path(__file__).resolve().parent.parent
    script_path = repo_root / "scripts" / "generate_enhancements_ini.py"
    spec = importlib.util.spec_from_file_location(
        "generate_enhancements_ini_tuple_test", script_path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# Canonical mission-variant tuple — same shape as the one built at
# generate_enhancements_ini.py:2817 (``missions[title_key].append(...)``).
# Keeping this aligned with the writer site is the entire point: when the
# writer shape moves, this constant must move, and every destructure in
# ``_run_gen_missions`` must follow.
def _make_variant(
    system_name: str = "Stanton",
    success_xp: int = 100,
    failure_xp: int = -50,
    desc_key: str = "test_desc_key",
    contract_flags=None,
    spawns=None,
    contract_difficulty: str | None = "3",
    contract_has_bp: bool = False,
    contract_bp_chance: float = 0.0,
    contract_bp_variant: str = "",
    rank_name: str = "",
) -> tuple:
    return (
        system_name,
        success_xp,
        failure_xp,
        desc_key,
        contract_flags or [],
        spawns if spawns is not None else {},
        contract_difficulty,
        contract_has_bp,
        contract_bp_chance,
        contract_bp_variant,
        rank_name,
    )


class TestMissionVariantTupleShape:
    """The canonical variant tuple has exactly 10 positions."""

    def test_variant_tuple_has_eleven_positions(self):
        v = _make_variant()
        assert len(v) == 11, (
            "The mission-variant tuple width is locked at 11 since the 1.4.2 "
            "rep-tier-names change. If you're changing this, also update "
            "every destructure in _run_gen_missions and every v[N] index "
            "access — see the comment block at the top of this test file."
        )


class TestRunGenMissionsTupleConsumers:
    """Both ``for ... in variants`` destructures in ``_run_gen_missions``
    must accept the canonical 10-tuple without raising. Pre-fix the head
    destructure had 11 placeholders and exploded on the first call."""

    def test_seen_tiers_destructure_accepts_canonical_tuple(self):
        """Locks the ``for _, sxp, fxp, _, _, _, _, _, _, _, rname in variants:``
        loop near the start of ``_run_gen_missions``."""
        variants = [
            _make_variant(success_xp=100, failure_xp=-50, rank_name="Rookie"),
            _make_variant(success_xp=200, failure_xp=-100, rank_name="Junior"),
            _make_variant(success_xp=300, failure_xp=-150, rank_name="Member"),
        ]
        seen_tiers: list[tuple[int, int, str]] = []
        for _, sxp, fxp, _, _, _, _, _, _, _, rname in variants:
            tier = (sxp, fxp, rname)
            if tier not in seen_tiers:
                seen_tiers.append(tier)
        assert seen_tiers == [(100, -50, "Rookie"), (200, -100, "Junior"), (300, -150, "Member")]

    def test_desc_variants_destructure_accepts_canonical_tuple(self):
        """Locks the ``for _, vsxp, vfxp, _, vflags, vspawns, vdiff, vhas_bp,
        vbp_chance, vbp_variant, vrname in desc_variants:`` aggregator loop."""
        desc_variants = [
            _make_variant(
                success_xp=500,
                contract_flags=["Starter"],
                spawns={"hostile": {"Pirates": 4}},
                contract_difficulty="2",
                contract_has_bp=True,
                contract_bp_chance=0.25,
                contract_bp_variant="hard",
                rank_name="Rookie",
            )
        ]
        rows: list[tuple] = []
        for _, vsxp, vfxp, _, vflags, vspawns, vdiff, vhas_bp, vbp_chance, vbp_variant, vrname in desc_variants:
            rows.append((vsxp, vflags, vspawns, vdiff, vhas_bp, vbp_chance, vbp_variant, vrname))
        assert rows == [
            (500, ["Starter"], {"hostile": {"Pirates": 4}}, "2", True, 0.25, "hard", "Rookie")
        ]

    def test_indexed_access_positions(self):
        """v[3] = desc_key, v[7] = contract_has_bp, v[0] = system_name,
        v[10] = rank_name — these are the exact ``v[N]`` indices read
        inside _run_gen_missions (the destructure-free access paths).
        Locks each."""
        v = _make_variant(
            system_name="Pyro",
            desc_key="my_desc",
            contract_has_bp=True,
            rank_name="Rookie",
        )
        assert v[0] == "Pyro"
        assert v[3] == "my_desc"
        assert v[7] is True
        assert v[10] == "Rookie"


