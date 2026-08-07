"""Read-only crafting recipe discovery from a local DataForge cache.

The game stores crafting costs in XML records beneath Data.p4k. This module
does not modify that cache or the game; it turns those records into a small,
display-ready recipe catalogue for the Crafting Planner.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import xml.etree.ElementTree as ET

_NULL_UUID = "00000000-0000-0000-0000-000000000000"


@dataclass(frozen=True)
class RecipeIngredient:
    name: str
    quantity: str
    resolved: bool = True


@dataclass(frozen=True)
class CraftingRecipe:
    name: str
    category: str
    ingredients: tuple[RecipeIngredient, ...]


def _records_dir(forge_dir: Path) -> Path:
    nested = forge_dir / "raw" / "libs" / "foundry" / "records"
    return nested if nested.exists() else forge_dir


def _type(elem: ET.Element) -> str:
    return elem.get("__polymorphicType") or elem.tag


def _fallback_name(stem: str) -> str:
    stem = re.sub(r"^bp_craft_", "", stem, flags=re.IGNORECASE)
    return stem.replace("_", " ").replace("-", " ").title()


def _element_name(root: ET.Element, loc: dict[str, str]) -> str | None:
    for elem in root.iter():
        value = elem.get("Name", "")
        if value.startswith("@"):
            return loc.get(value[1:], value[1:])
    return None


def load_crafting_recipes(forge_dir: Path, loc: dict[str, str] | None = None) -> list[CraftingRecipe]:
    """Return recipes from *forge_dir*, retaining every authored quantity.

    CIG uses both ``CraftingCost_Resource`` and ``CraftingCost_Item``.
    A missing entity name is deliberately shown as ``Unknown material`` rather
    than guessing or silently omitting an ingredient.
    """
    loc = loc or {}
    records = _records_dir(Path(forge_dir))
    bp_dir = records / "crafting" / "blueprints" / "crafting"
    scitem_dir = records / "entities" / "scitem"
    if not bp_dir.exists() or not scitem_dir.exists():
        return []

    parsed: list[tuple[Path, str, list[tuple[str, str]]]] = []
    wanted_ids: set[str] = set()
    for xml_file in bp_dir.rglob("*.xml"):
        try:
            root = ET.parse(xml_file).getroot()
        except (ET.ParseError, OSError):
            continue
        output_id = ""
        costs: list[tuple[str, str]] = []
        for elem in root.iter():
            kind = _type(elem)
            if kind == "CraftingProcess_Creation" and not output_id:
                output_id = elem.get("entityClass", "")
            elif kind == "CraftingCost_Resource":
                uid = elem.get("resource", "")
                if uid and uid != _NULL_UUID:
                    costs.append((uid, elem.get("quantity", "1")))
                    wanted_ids.add(uid)
            elif kind == "CraftingCost_Item":
                uid = elem.get("entityClass", "")
                if uid and uid != _NULL_UUID:
                    costs.append((uid, elem.get("quantity", "1")))
                    wanted_ids.add(uid)
        if output_id:
            wanted_ids.add(output_id)
        if costs:
            parsed.append((xml_file, output_id, costs))

    names: dict[str, str] = {}
    for xml_file in scitem_dir.rglob("*.xml"):
        try:
            text = xml_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        matches = [uid for uid in wanted_ids if uid not in names and uid in text]
        if not matches:
            continue
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            continue
        display = _element_name(root, loc) or xml_file.stem.replace("_", " ").title()
        # A record's own UUID is authoritative for output items and direct
        # item costs. Resource UUIDs can instead appear as a reference inside
        # a carryable record, so retain the broader text-match fallback only
        # for IDs that do not have an owning record.
        own_ref = root.get("__ref", "")
        if own_ref in wanted_ids:
            names[own_ref] = display
        for uid in matches:
            if uid != own_ref:
                names.setdefault(uid, display)

    recipes: list[CraftingRecipe] = []
    for xml_file, output_id, costs in parsed:
        output = names.get(output_id, _fallback_name(xml_file.stem))
        category = str(xml_file.relative_to(bp_dir).parent).replace("\\", "/")
        ingredients = tuple(
            RecipeIngredient(names.get(uid, "Unknown material"), quantity, uid in names)
            for uid, quantity in costs
        )
        recipes.append(CraftingRecipe(output, category, ingredients))
    return sorted(recipes, key=lambda recipe: recipe.name.casefold())
