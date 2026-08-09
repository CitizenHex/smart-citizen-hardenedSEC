"""Classification and defaults for optional in-game loot tags.

The classification is deliberately broad and display-only: it decides which
already-reviewed Finder/catalog matches receive a visible tag. It never makes
an acquisition claim by itself.
"""
from __future__ import annotations

import re


CATEGORY_COMBAT = "combat"
CATEGORY_ARMOR = "armor"
CATEGORY_CLOTHING = "clothing"
CATEGORY_FOOD = "food"
CATEGORY_MEDICAL = "medical"
CATEGORY_OTHER = "other"

CATEGORY_LABELS = {
    CATEGORY_COMBAT: "Weapons & ammunition",
    CATEGORY_ARMOR: "Armor & undersuits",
    CATEGORY_CLOTHING: "Clothing & accessories",
    CATEGORY_FOOD: "Food & drink",
    CATEGORY_MEDICAL: "Medical supplies",
    CATEGORY_OTHER: "Ship components & other items",
}

# Everyday consumables and clothing are intentionally opt-in. This keeps the
# first-use view useful for looting without filling it with labels most people
# will not act on; a player can enable any group at any time.
DEFAULT_ENABLED_CATEGORIES = frozenset({
    CATEGORY_COMBAT, CATEGORY_ARMOR, CATEGORY_OTHER,
})


def default_category_settings() -> dict[str, bool]:
    return {name: name in DEFAULT_ENABLED_CATEGORIES for name in CATEGORY_LABELS}


def normalize_category_settings(value) -> dict[str, bool]:
    defaults = default_category_settings()
    if not isinstance(value, dict):
        return defaults
    return {name: bool(value.get(name, default)) for name, default in defaults.items()}


def enabled_categories(value) -> frozenset[str]:
    settings = normalize_category_settings(value)
    return frozenset(name for name, enabled in settings.items() if enabled)


def classify_loot_item(key: str, value: str, source_category: str = "") -> str:
    """Classify a localized item name into a coarse, user-facing group.

    Armor is considered before clothing because boots, gloves, and helmets can
    belong to either. The source localization category is only a supporting
    hint; the visible item name remains the most stable input across builds.
    """
    text = " ".join((key or "", value or "", source_category or "")).casefold()
    text = re.sub(r"\s+", " ", text)
    if any(word in text for word in (
        "medpen", "medgun", "curelife", "medical", "medic", "healing",
        "health", "injector", "antidote", "stabilizer",
    )):
        return CATEGORY_MEDICAL
    if any(word in text for word in (
        "food", "drink", "water", "soda", "coffee", "tea", "juice",
        "snack", "meal", "ration", "beverage", "burrito", "hotdog",
    )):
        return CATEGORY_FOOD
    if any(word in text for word in (
        "armor", "helmet", "undersuit", "flight suit", "flightsuit",
        "tactical vest", "chest piece", "leg armor",
    )):
        return CATEGORY_ARMOR
    if any(word in text for word in (
        "rifle", "pistol", "shotgun", "sniper", "launcher", "weapon",
        "ammo", "ammunition", "magazine", "grenade", "missile", "knife",
    )):
        return CATEGORY_COMBAT
    if any(word in text for word in (
        "shirt", "pants", "jacket", "hoodie", "sweater", "dress", "skirt",
        "shorts", "hat", "cap", "beanie", "scarf", "shoes", "sneakers",
    )):
        return CATEGORY_CLOTHING
    return CATEGORY_OTHER
