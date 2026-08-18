"""Tests for the local-only Crafting Planner recipe reader."""
from pathlib import Path

from src.utils.crafting_recipes import (
    CraftingRecipe, RecipeIngredient, build_shopping_list, load_crafting_recipes,
)


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


def test_resource_reference_resolves_inside_record_with_own_root(tmp_path: Path):
    records = tmp_path / "raw" / "libs" / "foundry" / "records"
    recipes_dir = records / "crafting" / "blueprints" / "crafting"
    items = records / "entities" / "scitem"
    recipes_dir.mkdir(parents=True)
    items.mkdir(parents=True)
    resource = "11111111-1111-1111-1111-111111111111"
    own_ref = "22222222-2222-2222-2222-222222222222"
    (recipes_dir / "bp.xml").write_text(
        f'<Blueprint><CraftingCost_Resource resource="{resource}" quantity="2"/></Blueprint>', encoding="utf-8"
    )
    (items / "ore.xml").write_text(
        f'<Item __ref="{own_ref}"><Ref value="{resource}"/><Params Name="@item_ore"/></Item>', encoding="utf-8"
    )
    recipe = load_crafting_recipes(tmp_path, {"item_ore": "Test Ore"})[0]
    assert recipe.ingredients[0].name == "Test Ore"
    assert recipe.ingredients[0].resolved


def test_load_crafting_recipes_reads_nested_standard_cargo_quantity(tmp_path: Path):
    records = tmp_path / "crafting" / "blueprints" / "crafting"
    items = tmp_path / "entities" / "scitem"
    records.mkdir(parents=True)
    items.mkdir(parents=True)
    resource = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    (records / "bp_craft_nested.xml").write_text(
        "<Blueprint><CraftingCost_Resource resource=\"%s\"><quantity>"
        "<SStandardCargoUnit standardCargoUnits=\"0.03\"/></quantity>"
        "</CraftingCost_Resource></Blueprint>" % resource,
        encoding="utf-8",
    )
    (items / "resource.xml").write_text(
        f'<Item __ref="{resource}"><Params Name="@item_iron"/></Item>', encoding="utf-8"
    )
    recipe = load_crafting_recipes(tmp_path, {"item_iron": "Iron"})[0]
    assert recipe.ingredients[0].quantity == "0.03"


def test_blank_localized_material_uses_record_filename(tmp_path: Path):
    records = tmp_path / "crafting" / "blueprints" / "crafting"
    items = tmp_path / "entities" / "scitem"
    records.mkdir(parents=True)
    items.mkdir(parents=True)
    resource = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    (records / "bp_craft_m5a.xml").write_text(
        f'<Blueprint><CraftingCost_Resource resource="{resource}" quantity="1.16"/></Blueprint>',
        encoding="utf-8",
    )
    (items / "m5a_material.xml").write_text(
        f'<Item __ref="{resource}"><Params Name="@item_m5a_material"/></Item>',
        encoding="utf-8",
    )

    recipe = load_crafting_recipes(tmp_path, {"item_m5a_material": ""})[0]

    assert recipe.ingredients[0].name == "M5A Material"
    assert recipe.ingredients[0].resolved


def test_placeholder_localization_is_skipped_for_real_material_name(tmp_path: Path):
    records = tmp_path / "crafting" / "blueprints" / "crafting"
    items = tmp_path / "entities" / "scitem"
    records.mkdir(parents=True)
    items.mkdir(parents=True)
    resource = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    (records / "bp_craft_m4a.xml").write_text(
        f'<Blueprint><CraftingCost_Resource resource="{resource}" quantity="0.64"/></Blueprint>',
        encoding="utf-8",
    )
    (items / "agricium.xml").write_text(
        f'<Item __ref="{resource}"><Params Name="@LOC_EMPTY"/>'
        '<Localization Name="@items_commodities_agricium"/></Item>',
        encoding="utf-8",
    )

    recipe = load_crafting_recipes(tmp_path, {
        "LOC_EMPTY": "<= PLACEHOLDER =>",
        "items_commodities_agricium": "Agricium",
    })[0]

    assert recipe.ingredients[0].name == "Agricium"


def test_resource_uses_concise_commodity_name_from_cargo_filename(tmp_path: Path):
    records = tmp_path / "crafting" / "blueprints" / "crafting"
    items = tmp_path / "entities" / "scitem" / "carryables"
    records.mkdir(parents=True)
    items.mkdir(parents=True)
    resource = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    (records / "bp_craft_m4a.xml").write_text(
        f'<Blueprint><CraftingCost_Resource resource="{resource}" quantity="0.64"/></Blueprint>',
        encoding="utf-8",
    )
    (items / "carryable_tbo_commodity_metal_agricium.xml").write_text(
        f'<Item __ref="other"><Ref value="{resource}"/>'
        '<Localization Name="@cargo_comm_agricium"/></Item>',
        encoding="utf-8",
    )

    recipe = load_crafting_recipes(tmp_path, {
        "cargo_comm_agricium": "Cargo Comm 125X3 Metal Agricium A",
    })[0]

    assert recipe.ingredients[0].name == "Agricium"


def test_build_shopping_list_combines_matching_materials():
    recipes = [
        CraftingRecipe("One", "test", (RecipeIngredient("Iron", "12"), RecipeIngredient("Hadanite", "3"))),
        CraftingRecipe("Two", "test", (RecipeIngredient("Iron", "7"), RecipeIngredient("Copper", "10"))),
    ]
    shopping_list = build_shopping_list(recipes)
    assert [(item.name, item.quantity) for item in shopping_list] == [
        ("Copper", "10"),
        ("Hadanite", "3"), ("Iron", "19"),
    ]
