"""Read-only crafting recipe discovery from a local DataForge cache.

The game stores crafting costs in XML records beneath Data.p4k. This module
does not modify that cache or the game; it turns those records into a small,
display-ready recipe catalogue for the Crafting Planner.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import xml.etree.ElementTree as ET

_NULL_UUID = "00000000-0000-0000-0000-000000000000"
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)
_ROOT_REF_RE = re.compile(
    r'\b__ref="([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RecipeIngredient:
    name: str
    quantity: str
    resolved: bool = True
    identifier: str = ""


@dataclass(frozen=True)
class CraftingRecipe:
    name: str
    category: str
    ingredients: tuple[RecipeIngredient, ...]


def build_shopping_list(recipes) -> list[RecipeIngredient]:
    """Combine numeric ingredients from one or more recipes.

    Unresolved records are kept separate by their DataForge identifier, so two
    unrelated unknown materials are never silently combined. Non-numeric
    quantities are retained as individual lines rather than guessed at.
    """
    totals: dict[tuple[str, str], tuple[str, bool, Decimal]] = {}
    passthrough: list[RecipeIngredient] = []
    for recipe in recipes:
        for ingredient in recipe.ingredients:
            try:
                quantity = Decimal(ingredient.quantity)
                if not quantity.is_finite():
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                passthrough.append(ingredient)
                continue
            identity = ingredient.name.casefold() if ingredient.resolved else ingredient.identifier
            key = (identity, ingredient.name)
            previous = totals.get(key)
            totals[key] = (ingredient.name, ingredient.resolved, quantity if previous is None else previous[2] + quantity)

    def _format_quantity(quantity: Decimal) -> str:
        rendered = format(quantity, "f")
        return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered

    out = [
        RecipeIngredient(name, _format_quantity(quantity), resolved, identity)
        for (identity, _), (name, resolved, quantity) in totals.items()
    ]
    out.extend(passthrough)
    return sorted(out, key=lambda ingredient: (not ingredient.resolved, ingredient.name.casefold()))


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


def _cost_quantity(elem: ET.Element) -> str:
    """Read direct and current nested DataForge quantity formats."""
    if elem.get("quantity"):
        return elem.get("quantity", "1")
    # Current crafting records place quantities under ``<quantity>`` as
    # SStandardCargoUnit.standardCargoUnits rather than on CraftingCost_*.
    for child in elem.iter():
        for attribute in ("standardCargoUnits", "quantity", "count", "amount"):
            value = child.get(attribute)
            if value:
                return value
    return "1"


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
    # Outputs/items need an authoritative record root; resource costs are
    # references inside carryable records with a different root UUID.
    direct_ids: set[str] = set()
    resource_ids: set[str] = set()
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
                    costs.append((uid, _cost_quantity(elem)))
                    resource_ids.add(uid)
            elif kind == "CraftingCost_Item":
                uid = elem.get("entityClass", "")
                if uid and uid != _NULL_UUID:
                    costs.append((uid, _cost_quantity(elem)))
                    direct_ids.add(uid)
        if output_id:
            direct_ids.add(output_id)
        if costs:
            parsed.append((xml_file, output_id, costs))

    names: dict[str, str] = {}
    unresolved_direct = set(direct_ids)
    unresolved_resources = set(resource_ids)
    for xml_file in scitem_dir.rglob("*.xml"):
        try:
            # The old implementation compared every wanted UUID against the
            # full text of every one of ~24,000 item records. That becomes
            # tens of millions of scans and leaves the UI at "Reading...".
            # A record's identifiers live near its XML header, so first screen
            # a small prefix with one compiled UUID expression and parse only
            # the few records that actually refer to recipe data.
            with xml_file.open("r", encoding="utf-8", errors="ignore") as handle:
                text = handle.read(16 * 1024)
        except OSError:
            continue
        own_match = _ROOT_REF_RE.search(text)
        own_ref = own_match.group(1) if own_match else ""
        # Prefer a record's authoritative root ID. A wanted ID can appear as
        # a reference in unrelated ship/loadout records before its own item
        # record is encountered; accepting that first gave real items generic
        # fallback names (for example, M6A Cannon became "Behr Lasercannon").
        direct_match = own_ref if own_ref in unresolved_direct else ""
        # Current mineral UUIDs are references inside a carryable record whose
        # own root UUID is unrelated, so resources must accept such references.
        resource_matches = set(_UUID_RE.findall(text)) & unresolved_resources
        # Some resource records use a legacy <Ref value="…"> instead of an
        # authoritative __ref. Keep this narrow fallback only for records
        # without a root reference so it cannot steal another item's name.
        if not direct_match and not resource_matches:
            continue
        try:
            # ``text`` is only a small header used for fast UUID discovery;
            # full records can exceed that window, so parse the actual file
            # once it has been identified as relevant.
            root = ET.parse(xml_file).getroot()
        except (ET.ParseError, OSError):
            continue
        display = _element_name(root, loc) or xml_file.stem.replace("_", " ").title()
        # A record's own UUID is authoritative for output items and direct
        # item costs. Resource UUIDs can instead appear as a reference inside
        # a carryable record, so retain the broader text-match fallback only
        # for IDs that do not have an owning record.
        own_ref = root.get("__ref", "")
        if direct_match:
            names[own_ref] = display
            unresolved_direct.discard(own_ref)
        for uid in resource_matches:
            names.setdefault(uid, display)
            unresolved_resources.discard(uid)

    recipes: list[CraftingRecipe] = []
    for xml_file, output_id, costs in parsed:
        output = names.get(output_id, _fallback_name(xml_file.stem))
        category = str(xml_file.relative_to(bp_dir).parent).replace("\\", "/")
        ingredients = tuple(
            RecipeIngredient(names.get(uid, "Unknown material"), quantity, uid in names, uid)
            for uid, quantity in costs
        )
        recipes.append(CraftingRecipe(output, category, ingredients))
    return sorted(recipes, key=lambda recipe: recipe.name.casefold())
