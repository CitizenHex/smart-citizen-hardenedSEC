"""Tests for the local-only Crafting Planner recipe reader."""
from pathlib import Path

from src.utils.crafting_recipes import load_crafting_recipes


def test_load_crafting_recipes_resolves_resource_item_and_quantity(tmp_path: Path):
    records = tmp_path / "raw" / "libs" / "foundry" / "records"
    bp_dir = records / "crafting" / "blueprints" / "crafting" / "weapons"
    items = records / "entities" / "scitem" / "carryables"
    bp_dir.mkdir(parents=True)
    items.mkdir(parents=True)
    resource = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    gem = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    output = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    (bp_dir / "bp_craft_test_laser.xml").write_text(
        f'<Blueprint><CraftingProcess_Creation entityClass="{output}"/>'
        f'<CraftingCost_Resource resource="{resource}" quantity="12"/>'
        f'<CraftingCost_Item entityClass="{gem}" quantity="3"/></Blueprint>',
        encoding="utf-8",
    )
    (items / "resource.xml").write_text(
        f'<Item><Ref value="{resource}"/><Params Name="@item_iron"/></Item>', encoding="utf-8"
    )
    (items / "gem.xml").write_text(
        f'<Item __ref="{gem}"><Params Name="@item_hadanite"/></Item>', encoding="utf-8"
    )
    (items / "laser.xml").write_text(
        f'<Item __ref="{output}"><Params Name="@item_laser"/></Item>', encoding="utf-8"
    )

    recipes = load_crafting_recipes(tmp_path, {
        "item_iron": "Iron", "item_hadanite": "Hadanite", "item_laser": "Test Laser",
    })

    assert len(recipes) == 1
    assert recipes[0].name == "Test Laser"
    assert recipes[0].category == "weapons"
    assert [(i.name, i.quantity, i.resolved) for i in recipes[0].ingredients] == [
        ("Iron", "12", True), ("Hadanite", "3", True),
    ]


def test_load_crafting_recipes_keeps_unknown_material_visible(tmp_path: Path):
    records = tmp_path / "crafting" / "blueprints" / "crafting"
    items = tmp_path / "entities" / "scitem"
    records.mkdir(parents=True)
    items.mkdir(parents=True)
    (records / "bp_craft_unknown.xml").write_text(
        '<Blueprint><CraftingCost_Item entityClass="missing" quantity="2"/></Blueprint>',
        encoding="utf-8",
    )
    recipes = load_crafting_recipes(tmp_path)
    assert recipes[0].ingredients[0].name == "Unknown material"
    assert recipes[0].ingredients[0].quantity == "2"
    assert not recipes[0].ingredients[0].resolved
