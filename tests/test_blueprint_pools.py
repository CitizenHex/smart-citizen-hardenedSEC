"""Tests for the blueprint-pool side of the mission rewards pipeline.

Covers two changes shipped in 1.4.0:

1. ``scan_contract_generators`` previously kept only the first blueprint
   pool per ``(title_key, system_name)`` — subsequent ``BlueprintRewards``
   elements in the same contract were dropped on the floor. 4.8-era
   Adagio mining missions reward BOTH FPS gear (one pool) and ship
   components (another pool) from a single contract, so the old
   single-pool assumption silently lost half the loot list. The fix
   merges with order-preserving de-dup; the regression tests below
   guard that.

2. ``build_scitem_lookups`` now also returns an ``entity_name_tags``
   dict — UUID → ``[CLASS-Sx-grade]`` tag — that ``build_blueprint_pool_lookup``
   appends to ship-component blueprint names. So a mission's POTENTIAL
   BLUEPRINTS list reads "Norfield [MIL-S1-A]" instead of bare
   "Norfield", mirroring the inline tag the components pipeline writes
   onto stock component titles. FPS gear / weapons / ships get no tag.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from lxml import etree as ET

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def gen_module():
    """Load scripts/generate_enhancements_ini.py as an importable module."""
    repo_root = Path(__file__).resolve().parent.parent
    script_path = repo_root / "scripts" / "generate_enhancements_ini.py"
    spec = importlib.util.spec_from_file_location("generate_enhancements_ini_blueprint_test", script_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_contractgen_xml(dir_path: Path, filename: str, contract_xml: str) -> Path:
    """Write a minimal ContractGenerator XML containing the given contract body."""
    path = dir_path / filename
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<root>\n'
        + contract_xml +
        '\n</root>\n',
        encoding="utf-8",
    )
    return path


class TestMultiSourcePoolMerge:
    """Regression guard for the 1.4.0 Adagio-mining multi-pool bug.

    Pre-fix: only the first ``BlueprintRewards`` per system was kept;
    subsequent pools (FPS gear + ship components in the same contract)
    were silently dropped.
    """

    @pytest.mark.regression
    def test_two_blueprint_rewards_in_one_contract_merge(self, gen_module, tmp_path):
        contractgen_dir = tmp_path / "contractgenerator"
        contractgen_dir.mkdir()

        # Adagio-style contract: one Contract, two BlueprintRewards pointing
        # at different pools (FPS gear + ship components).
        contract_xml = '''
<ContractGeneratorHandler_List debugName="Adagio_Stanton_HandMining">
    <Contract debugName="Adagio_Stanton_HandMining_T1">
        <Title>
            <ContractStringParam param="Title" value="@adagio_mining_title"/>
            <ContractStringParam param="Description" value="@adagio_mining_desc"/>
        </Title>
        <BlueprintRewards blueprintPool="pool-fps-uuid" chance="1.0"/>
        <BlueprintRewards blueprintPool="pool-comp-uuid" chance="1.0"/>
    </Contract>
</ContractGeneratorHandler_List>
'''
        _write_contractgen_xml(contractgen_dir, "adagio.xml", contract_xml)

        blueprint_pools = {
            "pool-fps-uuid":  ["Pyro Pickaxe", "FPS Mining Helmet"],
            "pool-comp-uuid": ["Norfield Power Plant", "Harkin Cooler"],
        }

        _missions, mission_blueprints, _chance, _items = gen_module.scan_contract_generators(
            contractgen_dir,
            reputation_lookup={},
            blueprint_pools=blueprint_pools,
            entity_names={},
        )

        assert "adagio_mining_title" in mission_blueprints, (
            "title_key missing from mission_blueprints — contract parser failed"
        )
        per_system = mission_blueprints["adagio_mining_title"]
        assert "Stanton" in per_system, f"expected 'Stanton' system, got {list(per_system)}"

        items = per_system["Stanton"]
        # Both pools' items must appear — the bug was the second pool getting dropped.
        assert "Pyro Pickaxe" in items
        assert "FPS Mining Helmet" in items
        assert "Norfield Power Plant" in items
        assert "Harkin Cooler" in items
        assert len(items) == 4, f"expected 4 merged items, got {len(items)}: {items}"

    @pytest.mark.regression
    def test_merge_dedups_duplicate_items_across_pools(self, gen_module, tmp_path):
        """When two pools share an item, the merged list should list it once."""
        contractgen_dir = tmp_path / "contractgenerator"
        contractgen_dir.mkdir()
        contract_xml = '''
<ContractGeneratorHandler_List debugName="DupeTest_Stanton">
    <Contract debugName="DupeTest_Stanton_T1">
        <Title>
            <ContractStringParam param="Title" value="@dupe_title"/>
            <ContractStringParam param="Description" value="@dupe_desc"/>
        </Title>
        <BlueprintRewards blueprintPool="pool-a" chance="1.0"/>
        <BlueprintRewards blueprintPool="pool-b" chance="1.0"/>
    </Contract>
</ContractGeneratorHandler_List>
'''
        _write_contractgen_xml(contractgen_dir, "dupe.xml", contract_xml)

        blueprint_pools = {
            "pool-a": ["Shared Item", "Unique A"],
            "pool-b": ["Shared Item", "Unique B"],
        }

        _, mission_blueprints, _, _ = gen_module.scan_contract_generators(
            contractgen_dir, reputation_lookup={},
            blueprint_pools=blueprint_pools, entity_names={},
        )
        items = mission_blueprints["dupe_title"]["Stanton"]
        assert items.count("Shared Item") == 1, (
            f"de-dup failed — 'Shared Item' appears {items.count('Shared Item')}× in {items}"
        )
        assert sorted(items) == ["Shared Item", "Unique A", "Unique B"]

    def test_single_pool_unchanged(self, gen_module, tmp_path):
        """Single-BlueprintRewards contracts behave identically to pre-fix."""
        contractgen_dir = tmp_path / "contractgenerator"
        contractgen_dir.mkdir()
        contract_xml = '''
<ContractGeneratorHandler_List debugName="SingleTest_Stanton">
    <Contract debugName="SingleTest_Stanton_T1">
        <Title>
            <ContractStringParam param="Title" value="@single_title"/>
            <ContractStringParam param="Description" value="@single_desc"/>
        </Title>
        <BlueprintRewards blueprintPool="pool-only" chance="0.5"/>
    </Contract>
</ContractGeneratorHandler_List>
'''
        _write_contractgen_xml(contractgen_dir, "single.xml", contract_xml)

        _, mission_blueprints, mission_bp_chance, _ = gen_module.scan_contract_generators(
            contractgen_dir, reputation_lookup={},
            blueprint_pools={"pool-only": ["Only Item"]},
            entity_names={},
        )
        assert mission_blueprints["single_title"]["Stanton"] == ["Only Item"]
        assert mission_bp_chance["single_title"] == pytest.approx(0.5)


class TestBlueprintNameTags:
    """1.4.0 annotation: components in blueprint pools get the inline
    ``[CLASS-Sx-grade]`` tag the components pipeline writes onto stock
    component titles."""

    def test_scitem_lookup_emits_tag_for_component(self, gen_module, tmp_path):
        """A component XML with Size:/Grade:/Class: description should
        produce an entry in ``entity_name_tags``."""
        scitem_dir = tmp_path / "scitem"
        scitem_dir.mkdir()
        comp_xml = scitem_dir / "norfield_pp_s1.xml"
        comp_xml.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<EntityClassDefinition __ref="ent-norfield-uuid">\n'
            '  <Components>\n'
            '    <SAttachableComponentParams>\n'
            '      <AttachDef>\n'
            '        <Localization Name="@item_NameNorfield" Description="@item_DescNorfield"/>\n'
            '      </AttachDef>\n'
            '    </SAttachableComponentParams>\n'
            '  </Components>\n'
            '</EntityClassDefinition>\n',
            encoding="utf-8",
        )
        loc = {
            "item_NameNorfield": "Norfield",
            "item_DescNorfield": "Size: 1\\nGrade: A\\nClass: Military\\n\\nDescription text.",
        }

        _, entity_names, _, entity_name_tags = gen_module.build_scitem_lookups(scitem_dir, loc=loc)

        assert entity_names["ent-norfield-uuid"] == "Norfield"
        assert entity_name_tags["ent-norfield-uuid"] == "[MIL-S1-A]"

    def test_scitem_lookup_skips_tag_for_non_component(self, gen_module, tmp_path):
        """FPS gear / weapons whose description has no Size:/Grade:/Class:
        header should NOT produce a tag entry."""
        scitem_dir = tmp_path / "scitem"
        scitem_dir.mkdir()
        fps_xml = scitem_dir / "pickaxe.xml"
        fps_xml.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<EntityClassDefinition __ref="ent-pickaxe-uuid">\n'
            '  <Components>\n'
            '    <SAttachableComponentParams>\n'
            '      <AttachDef>\n'
            '        <Localization Name="@item_NamePickaxe" Description="@item_DescPickaxe"/>\n'
            '      </AttachDef>\n'
            '    </SAttachableComponentParams>\n'
            '  </Components>\n'
            '</EntityClassDefinition>\n',
            encoding="utf-8",
        )
        loc = {
            "item_NamePickaxe": "Pyro Pickaxe",
            "item_DescPickaxe": "A heavy-duty mining pickaxe with no component header.",
        }

        _, entity_names, _, entity_name_tags = gen_module.build_scitem_lookups(scitem_dir, loc=loc)

        assert entity_names["ent-pickaxe-uuid"] == "Pyro Pickaxe"
        assert "ent-pickaxe-uuid" not in entity_name_tags

    def test_blueprint_pool_appends_tag_on_uuid_hit(self, gen_module, tmp_path):
        """``build_blueprint_pool_lookup`` should append the tag to the
        display name when the entityClass UUID resolves AND has a tag entry."""
        pool_dir = tmp_path / "blueprintrewards"
        bp_dir = tmp_path / "blueprints" / "crafting"
        pool_dir.mkdir(parents=True)
        bp_dir.mkdir(parents=True)

        # One blueprint pool with two BlueprintReward entries — one for
        # a tagged component, one for an FPS item.
        (pool_dir / "pool_adagio.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<BlueprintPoolRecord __ref="pool-adagio-uuid">\n'
            '  <BlueprintReward blueprintRecord="bp-norfield-uuid"/>\n'
            '  <BlueprintReward blueprintRecord="bp-pickaxe-uuid"/>\n'
            '</BlueprintPoolRecord>\n',
            encoding="utf-8",
        )
        (bp_dir / "bp_craft_norfield.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<CraftingBlueprintRecord __ref="bp-norfield-uuid">\n'
            '  <CraftingProcess_Creation entityClass="ent-norfield-uuid"/>\n'
            '</CraftingBlueprintRecord>\n',
            encoding="utf-8",
        )
        (bp_dir / "bp_craft_pickaxe.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<CraftingBlueprintRecord __ref="bp-pickaxe-uuid">\n'
            '  <CraftingProcess_Creation entityClass="ent-pickaxe-uuid"/>\n'
            '</CraftingBlueprintRecord>\n',
            encoding="utf-8",
        )

        entity_names = {
            "ent-norfield-uuid": "Norfield",
            "ent-pickaxe-uuid": "Pyro Pickaxe",
        }
        entity_name_tags = {
            "ent-norfield-uuid": "[MIL-S1-A]",
            # No entry for pickaxe — FPS gear has no component tag.
        }

        pools = gen_module.build_blueprint_pool_lookup(
            pool_dir, bp_dir, entity_names,
            entity_name_tags=entity_name_tags,
        )

        items = pools["pool-adagio-uuid"]
        # Order: blueprint-pool resolution order, not alphabetical.
        assert "Norfield [MIL-S1-A]" in items, f"tagged name missing: {items}"
        assert "Pyro Pickaxe" in items, f"bare FPS name missing: {items}"
        # Critically, the FPS item is NOT tagged.
        assert not any(name.startswith("Pyro Pickaxe ") for name in items), (
            f"FPS gear should not get a [CLASS-Sx-grade] tag: {items}"
        )

    def test_strip_cig_size_prefix_helper(self, gen_module):
        """The strip helper removes ``S0 `` / ``S00 `` / ``S1 ``… prefixes
        but leaves names that start with ``S`` + letters (Sasquatch, etc.)."""
        f = gen_module._strip_cig_size_prefix
        assert f("S0 Helix") == "Helix"
        assert f("S00 Hofstede") == "Hofstede"
        assert f("S1 ExampleHead") == "ExampleHead"
        assert f("S15 BiggerHead") == "BiggerHead"
        # Names that begin with 'S' but not 'S{digit}' are untouched.
        assert f("Sasquatch") == "Sasquatch"
        assert f("Slicer Pistol") == "Slicer Pistol"
        assert f("Surveyor-Go") == "Surveyor-Go"
        # No prefix → unchanged.
        assert f("Norfield") == "Norfield"
        # Strip only the LEADING occurrence — a literal "S0" elsewhere stays.
        assert f("Foo S0 Bar") == "Foo S0 Bar"
        # Sanity: a name that's only the prefix collapses to empty (edge case;
        # unlikely in real data but worth pinning behavior).
        assert f("S0 ") == ""

    def test_blueprint_pool_strips_cig_size_prefix_on_uuid_hit(self, gen_module, tmp_path):
        """Tier-1 (UUID-resolved) names should have the CIG-baked size
        prefix stripped before reaching the blueprint list — eliminates
        the visual inconsistency of "S0 Helix" sitting next to
        "Surveyor [IND-S2-C]" in the same rendered list."""
        pool_dir = tmp_path / "blueprintrewards"
        bp_dir = tmp_path / "blueprints" / "crafting"
        pool_dir.mkdir(parents=True)
        bp_dir.mkdir(parents=True)

        (pool_dir / "pool.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<BlueprintPoolRecord __ref="pool-uuid">\n'
            '  <BlueprintReward blueprintRecord="bp-helix-uuid"/>\n'
            '  <BlueprintReward blueprintRecord="bp-norfield-uuid"/>\n'
            '</BlueprintPoolRecord>\n',
            encoding="utf-8",
        )
        (bp_dir / "bp_craft_helix.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<CraftingBlueprintRecord __ref="bp-helix-uuid">\n'
            '  <CraftingProcess_Creation entityClass="ent-helix-uuid"/>\n'
            '</CraftingBlueprintRecord>\n',
            encoding="utf-8",
        )
        (bp_dir / "bp_craft_norfield.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<CraftingBlueprintRecord __ref="bp-norfield-uuid">\n'
            '  <CraftingProcess_Creation entityClass="ent-norfield-uuid"/>\n'
            '</CraftingBlueprintRecord>\n',
            encoding="utf-8",
        )

        entity_names = {
            "ent-helix-uuid": "S0 Helix",
            "ent-norfield-uuid": "Norfield",
        }
        entity_name_tags = {
            "ent-norfield-uuid": "[MIL-S1-A]",
            # Helix doesn't get a tag (its description lacks Class:) — but
            # the CIG-baked "S0 " prefix should still come off.
        }

        pools = gen_module.build_blueprint_pool_lookup(
            pool_dir, bp_dir, entity_names,
            entity_name_tags=entity_name_tags,
        )
        items = pools["pool-uuid"]
        assert "Helix" in items, f"prefix should be stripped: {items}"
        assert "S0 Helix" not in items, f"unstripped name should not appear: {items}"
        assert "Norfield [MIL-S1-A]" in items, f"tagged name should still work: {items}"

    def test_blueprint_pool_omits_tag_when_dict_unset(self, gen_module, tmp_path):
        """Back-compat: callers that don't pass entity_name_tags get
        un-annotated names (pre-1.4.0 behavior)."""
        pool_dir = tmp_path / "blueprintrewards"
        bp_dir = tmp_path / "blueprints" / "crafting"
        pool_dir.mkdir(parents=True)
        bp_dir.mkdir(parents=True)

        (pool_dir / "pool.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<BlueprintPoolRecord __ref="pool-uuid">\n'
            '  <BlueprintReward blueprintRecord="bp-uuid"/>\n'
            '</BlueprintPoolRecord>\n',
            encoding="utf-8",
        )
        (bp_dir / "bp_craft_thing.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<CraftingBlueprintRecord __ref="bp-uuid">\n'
            '  <CraftingProcess_Creation entityClass="ent-uuid"/>\n'
            '</CraftingBlueprintRecord>\n',
            encoding="utf-8",
        )

        # No entity_name_tags argument → no tag, even though we could've matched.
        pools = gen_module.build_blueprint_pool_lookup(
            pool_dir, bp_dir, {"ent-uuid": "Thing"},
        )
        assert pools["pool-uuid"] == ["Thing"]
