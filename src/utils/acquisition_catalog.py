"""Local, reviewable acquisition tags for in-game item names.

The game data identifies an item but does not authoritatively say whether it
is sold, limited, or worth retaining.  This module deliberately makes no such
guess.  Tags come only from a small JSON catalog that the player can inspect,
edit in the UI, export, and explicitly import.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from src.utils.resource_path import get_resource_path

SCHEMA_VERSION = 1
MAX_CATALOG_BYTES = 2 * 1024 * 1024
VALID_STATUSES = frozenset({"shop", "keep", "limited"})
DISPLAY_TAGS = {
    "shop": "[Shop]", "keep": "[Keep]", "limited": "[Limited]",
    "unlisted": "[Unlisted]",
}
_ITEM_NAME_RE = re.compile(r"^item_name", re.IGNORECASE)
_TAG_RE = re.compile(r"\s*<EM4>\[(?:Shop|Keep|Limited|Unlisted)\]</EM4>", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")


def is_item_name_key(key: str) -> bool:
    """Return whether *key* is a localized item name, never a description."""
    return bool(_ITEM_NAME_RE.match(key or ""))


def validate_catalog(payload) -> dict:
    """Validate and normalize an acquisition catalog without touching disk."""
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported acquisition catalog format.")
    items = payload.get("items")
    if not isinstance(items, dict):
        raise ValueError("The catalog must contain an items object.")
    cleaned = {}
    for key, record in items.items():
        if not isinstance(key, str) or not is_item_name_key(key):
            raise ValueError("Catalog item keys must be Star Citizen item_Name keys.")
        if not isinstance(record, dict) or record.get("status") not in VALID_STATUSES:
            raise ValueError("Each catalog item needs a valid status.")
        entry = {"status": record["status"]}
        if isinstance(record.get("source"), str) and len(record["source"]) <= 500:
            entry["source"] = record["source"].strip()
        cleaned[key] = entry
    names = payload.get("names", {})
    if not isinstance(names, dict):
        raise ValueError("The catalog names field must be an object.")
    cleaned_names = {}
    for name, record in names.items():
        if not isinstance(name, str) or not name.strip() or len(name) > 500:
            raise ValueError("Catalog names must be non-empty item display names.")
        if not isinstance(record, dict) or record.get("status") not in VALID_STATUSES | {"unlisted"}:
            raise ValueError("Each catalog name needs a valid status.")
        entry = {"status": record["status"]}
        if isinstance(record.get("source"), str) and len(record["source"]) <= 500:
            entry["source"] = record["source"].strip()
        cleaned_names[_normalize_display_name(name)] = entry
    complete = payload.get("shop_catalog_complete", False)
    if not isinstance(complete, bool):
        raise ValueError("shop_catalog_complete must be true or false.")
    result = {"schema_version": SCHEMA_VERSION, "items": cleaned, "names": cleaned_names,
              "shop_catalog_complete": complete}
    if isinstance(payload.get("shop_catalog_version"), str):
        result["shop_catalog_version"] = payload["shop_catalog_version"][:100]
    return result


def empty_catalog() -> dict:
    return {"schema_version": SCHEMA_VERSION, "items": {}, "names": {}, "shop_catalog_complete": False}


def load_catalog_file(path: str | Path) -> dict:
    path = Path(path)
    if path.stat().st_size > MAX_CATALOG_BYTES:
        raise ValueError("Catalog files must be 2 MiB or smaller.")
    try:
        with path.open("r", encoding="utf-8") as fh:
            return validate_catalog(json.load(fh))
    except UnicodeDecodeError as exc:
        raise ValueError("Catalog files must be UTF-8 JSON.") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("Catalog file is not valid JSON.") from exc


def bundled_catalog() -> dict:
    """Load the reviewed catalog shipped with this build (currently empty)."""
    try:
        return load_catalog_file(get_resource_path("assets/acquisition_catalog.json"))
    except (OSError, ValueError):
        return empty_catalog()


def catalog_from_json(raw: str | None) -> dict:
    if not raw:
        return bundled_catalog()
    if len(raw.encode("utf-8")) > MAX_CATALOG_BYTES:
        return bundled_catalog()
    try:
        return validate_catalog(json.loads(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return bundled_catalog()


def catalog_to_json(catalog: dict) -> str:
    return json.dumps(validate_catalog(catalog), indent=2, sort_keys=True) + "\n"


def set_item_status(catalog: dict, key: str, status: str | None) -> dict:
    """Return a catalog copy with one item tagged or cleared."""
    result = copy.deepcopy(validate_catalog(catalog))
    if not is_item_name_key(key):
        raise ValueError("Only item name entries can receive acquisition tags.")
    if status is None:
        result["items"].pop(key, None)
    elif status in VALID_STATUSES:
        result["items"][key] = {"status": status, "source": "Local user review"}
    else:
        raise ValueError("Unknown acquisition status.")
    return result


def status_for_key(key: str, catalog: dict) -> str | None:
    """Return an explicit tag, or cautious ``unlisted`` when warranted.

    Catalogs are validated when they are loaded or imported. This helper runs
    for every localized string at startup, so validation here would turn one
    large catalog into thousands of repeated full-catalog scans.
    """
    record = catalog["items"].get(key)
    if record:
        return record["status"]
    if catalog["shop_catalog_complete"] and is_item_name_key(key):
        return "unlisted"
    return None


def _normalize_display_name(value: str) -> str:
    """Normalize an item name for an exact, case-insensitive catalog match."""
    bare = _TAG_RE.sub("", value or "")
    return _WHITESPACE_RE.sub(" ", bare).strip().casefold()


def status_for_entry(key: str, value: str, catalog: dict) -> str | None:
    """Resolve a manual key override first, then a bundled display-name entry."""
    key_status = status_for_key(key, catalog)
    if key_status:
        return key_status
    record = catalog["names"].get(_normalize_display_name(value))
    return record["status"] if record else None


def apply_acquisition_tag(value: str, key: str, catalog: dict, enabled_groups=None,
                          source_category: str = "") -> str:
    """Idempotently append the selected tag to an item's own display name."""
    if not is_item_name_key(key):
        return value
    bare = _TAG_RE.sub("", value or "")
    if enabled_groups is not None:
        from src.utils.loot_tag_categories import classify_loot_item
        if classify_loot_item(key, bare, source_category) not in enabled_groups:
            return bare
    status = status_for_entry(key, bare, catalog)
    if not status:
        return bare
    return f"{bare} <EM4>{DISPLAY_TAGS[status]}</EM4>"
