"""Tests for src/merger/ini_merger.py — sync_key_variants and the
merge_sources_by_hierarchy pipeline that drives it.

sync_key_variants had no test coverage at all before this file, despite two
real bug reports against its variant-selection heuristic (a naive "first
variant wins" pass, then a "prefer non-_SCItem" pre-filter, both wrong in
opposite ways — see the docstring in ini_merger.py). These tests pin the
three real-data shapes that broke it, plus the guard added so a user's
override to a variant can't be silently outvoted by the longest-value rule.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.merger.ini_merger import merge_sources_by_hierarchy, sync_key_variants  # noqa: E402

pytestmark = pytest.mark.unit


class TestSyncKeyVariantsRealDataShapes:
    """The two real bug reports this function's history is built from."""

    def test_short_untagged_sibling_loses_to_tagged(self):
        """The 7SA pair: item_Name_SHLD_BEHR_S01_7SA (tagged/enhanced) and
        item_NameSHLD_BEHR_S01_7sa (a distinct, never-enhanced sibling with
        just the bare stock name) canonicalize to the same key. The short,
        untagged one must not win."""
        merged = {
            "item_Name_SHLD_BEHR_S01_7SA": "[SHLD-S1-B] BEHR Shield",
            "item_NameSHLD_BEHR_S01_7sa": "BEHR Shield",
        }
        sync_key_variants(merged)
        assert merged["item_Name_SHLD_BEHR_S01_7SA"] == "[SHLD-S1-B] BEHR Shield"
        assert merged["item_NameSHLD_BEHR_S01_7sa"] == "[SHLD-S1-B] BEHR Shield"

    def test_scitem_suffixed_variant_can_hold_correct_value(self):
        """The Taiga pair: item_NameCOOL_WCPR_S02_Taiga_SCItem holds the
        correctly tagged value while its non-_SCItem sibling
        item_Name_COOL_WCPR_S02_Taiga is the never-enhanced bare one. A
        blanket "non-_SCItem always wins" pre-filter (tried and reverted)
        picked the bare one every time — length alone must decide."""
        merged = {
            "item_Name_COOL_WCPR_S02_Taiga": "Taiga Cooler",
            "item_NameCOOL_WCPR_S02_Taiga_SCItem": "[COOL-S2-B] Taiga Cooler",
        }
        sync_key_variants(merged)
        assert merged["item_Name_COOL_WCPR_S02_Taiga"] == "[COOL-S2-B] Taiga Cooler"
        assert merged["item_NameCOOL_WCPR_S02_Taiga_SCItem"] == "[COOL-S2-B] Taiga Cooler"

    def test_equal_length_variants_are_a_no_op(self):
        """Genuine same-entity variants (the generator's own sibling
        mirroring) already carry matching values, so a length tie is
        harmless either way."""
        merged = {
            "item_Name_QDRV_RSI_S02_Hemera": "Hemera Drive",
            "item_nameQDRV_RSI_S02_Hemera_SCItem": "Hemera Drive",
        }
        sync_key_variants(merged)
        assert merged["item_Name_QDRV_RSI_S02_Hemera"] == "Hemera Drive"
        assert merged["item_nameQDRV_RSI_S02_Hemera_SCItem"] == "Hemera Drive"

    def test_unrelated_keys_untouched(self):
        merged = {"some_unrelated_key": "value", "another_key": "other value"}
        sync_key_variants(merged)
        assert merged == {"some_unrelated_key": "value", "another_key": "other value"}


class TestSyncKeyVariantsUserEditGuard:
    """A user-edited variant must survive sync_key_variants even when it's
    shorter than an untouched sibling's value — otherwise the very next
    merge silently reverts the user's edit (root CLAUDE.md: user overrides
    "apply last and survive")."""

    def test_user_edited_short_variant_wins_over_longer_untouched_sibling(self):
        merged = {
            "item_Name_SHLD_BEHR_S01_7SA": "My Custom Name",
            "item_NameSHLD_BEHR_S01_7sa": "[SHLD-S1-B] BEHR Shield Original",
        }
        sync_key_variants(merged, user_edited_keys={"item_Name_SHLD_BEHR_S01_7SA"})
        assert merged["item_Name_SHLD_BEHR_S01_7SA"] == "My Custom Name"
        assert merged["item_NameSHLD_BEHR_S01_7sa"] == "My Custom Name"

    def test_no_user_edit_falls_back_to_longest(self):
        """Same data as above, but with no user_edited_keys passed — the
        pre-existing longest-value behavior is unchanged."""
        merged = {
            "item_Name_SHLD_BEHR_S01_7SA": "My Custom Name",
            "item_NameSHLD_BEHR_S01_7sa": "[SHLD-S1-B] BEHR Shield Original",
        }
        sync_key_variants(merged)
        assert merged["item_Name_SHLD_BEHR_S01_7SA"] == "[SHLD-S1-B] BEHR Shield Original"
        assert merged["item_NameSHLD_BEHR_S01_7sa"] == "[SHLD-S1-B] BEHR Shield Original"

    def test_multiple_user_edited_variants_longest_of_those_wins(self):
        """No ordering signal between two deliberate edits, so fall back to
        the same longest-wins tie-break, scoped to just the edited ones."""
        merged = {
            "item_Name_SHLD_BEHR_S01_7SA": "Short Edit",
            "item_NameSHLD_BEHR_S01_7sa": "A Longer Deliberate Edit",
        }
        sync_key_variants(
            merged,
            user_edited_keys={"item_Name_SHLD_BEHR_S01_7SA", "item_NameSHLD_BEHR_S01_7sa"},
        )
        assert merged["item_Name_SHLD_BEHR_S01_7SA"] == "A Longer Deliberate Edit"
        assert merged["item_NameSHLD_BEHR_S01_7sa"] == "A Longer Deliberate Edit"

    def test_user_edited_key_unrelated_to_variants_is_ignored(self):
        """user_edited_keys naming a key with no variant siblings at all
        must not error or affect anything."""
        merged = {
            "item_Name_SHLD_BEHR_S01_7SA": "[SHLD-S1-B] BEHR Shield",
            "item_NameSHLD_BEHR_S01_7sa": "BEHR Shield",
        }
        sync_key_variants(merged, user_edited_keys={"totally_unrelated_key"})
        assert merged["item_Name_SHLD_BEHR_S01_7SA"] == "[SHLD-S1-B] BEHR Shield"


class TestMergeSourcesByHierarchyUserOverrideSurvival:
    """Integration-level: merge_sources_by_hierarchy must wire the guard
    through automatically, not just the unit-level sync_key_variants."""

    def test_user_override_to_short_variant_survives_merge(self):
        sources = {
            "global": {
                "item_Name_SHLD_BEHR_S01_7SA": "[SHLD-S1-B] BEHR Shield",
                "item_NameSHLD_BEHR_S01_7sa": "BEHR Shield",
            },
        }
        user_overrides = {"item_Name_SHLD_BEHR_S01_7SA": "My Renamed Shield"}
        result = merge_sources_by_hierarchy(sources, ["global"], user_overrides)
        assert result["item_Name_SHLD_BEHR_S01_7SA"] == "My Renamed Shield"
        assert result["item_NameSHLD_BEHR_S01_7sa"] == "My Renamed Shield"

    def test_no_overrides_still_syncs_by_longest(self):
        sources = {
            "global": {
                "item_Name_COOL_WCPR_S02_Taiga": "Taiga Cooler",
                "item_NameCOOL_WCPR_S02_Taiga_SCItem": "[COOL-S2-B] Taiga Cooler",
            },
        }
        result = merge_sources_by_hierarchy(sources, ["global"])
        assert result["item_Name_COOL_WCPR_S02_Taiga"] == "[COOL-S2-B] Taiga Cooler"
