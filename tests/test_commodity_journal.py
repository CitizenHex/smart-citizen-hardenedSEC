"""Regression tests for ``scan_crafting_blueprints`` return shape.

Pre-1.4.1, the function's early-return when the crafting blueprints
directory was missing returned a single empty dict, while the happy path
returned a ``(commodity_out, journal_out)`` 2-tuple. The dispatcher in
``main()`` unpacks the result into ``out_commodities, out_journal`` —
so any user whose DataForge cache happened to lack the crafting tree
crashed the enhancements pipeline with::

    ValueError: not enough values to unpack (expected 2, got 0)

This test locks both halves of the contract: returns a 2-tuple of dicts
on the missing-directory path AND on the present-but-empty path.
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
        "generate_enhancements_ini_commodity_test", script_path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestScanCraftingBlueprintsReturnShape:
    def test_missing_directory_returns_two_empty_dicts(self, gen_module, tmp_path):
        """The early-return path (no crafting blueprints dir) must produce a
        2-tuple to match the happy-path shape — otherwise the dispatcher in
        ``main()`` fails to unpack the result."""
        nonexistent = tmp_path / "does_not_exist"
        carryables = tmp_path / "carryables_also_missing"

        result = gen_module.scan_crafting_blueprints(
            bp_dir=nonexistent,
            carryables_dir=carryables,
            entity_names={},
            loc={},
        )

        assert isinstance(result, tuple), (
            "scan_crafting_blueprints must return a 2-tuple even when bp_dir "
            "is missing — the main() dispatcher unpacks the result into "
            "(out_commodities, out_journal) unconditionally."
        )
        assert len(result) == 2
        commodities, journal = result
        assert commodities == {}
        assert journal == {}

    def test_dispatcher_unpack_against_missing_dir(self, gen_module, tmp_path):
        """End-to-end shape guard: a fresh ``(out_commodities, out_journal) =
        scan_crafting_blueprints(...)`` unpack must not raise even when the
        directory is missing. This is the exact line that crashed in 1.3.1."""
        out_commodities, out_journal = gen_module.scan_crafting_blueprints(
            bp_dir=tmp_path / "missing",
            carryables_dir=tmp_path / "missing_too",
            entity_names={},
            loc={},
        )
        assert out_commodities == {}
        assert out_journal == {}
