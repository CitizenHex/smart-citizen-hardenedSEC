"""Export a small, offline asset-name catalog from local DataForge data."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
import xml.etree.ElementTree as ET


def _category(path: Path) -> str | None:
    parts = {part.casefold() for part in path.parts}
    if "vehicles" in parts or "vehicle" in parts:
        return "ships"
    if "armor" in parts:
        return "armor"
    if "weapons" in parts or "weapon" in parts:
        return "weapons"
    return None


def _name_key(root: ET.Element) -> str | None:
    for element in root.iter():
        value = element.get("Name", "")
        if value.startswith("@item_Name"):
            return value[1:]
    return None


def build_asset_catalog(forge_dir: Path, localization: dict[str, str], channel: str) -> dict:
    """Return display names for ships, armor, and weapons from local files only."""
    records = forge_dir / "raw" / "libs" / "foundry" / "records"
    if not records.is_dir():
        raise ValueError("Local DataForge records are not available. Import Data.p4k first.")
    buckets: dict[str, dict[str, dict]] = {"ships": {}, "armor": {}, "weapons": {}}
    for path in records.rglob("*.xml"):
        category = _category(path.relative_to(records))
        if category is None:
            continue
        try:
            key = _name_key(ET.parse(path).getroot())
        except (ET.ParseError, OSError):
            continue
        name = localization.get(key or "", "").strip()
        if not name or name.startswith("<="):
            continue
        buckets[category].setdefault(key, {
            "name": name,
            "localization_key": key,
            "source_path": path.relative_to(records).as_posix(),
        })
    return {
        "format": "citizenhex-asset-catalog",
        "version": 1,
        "channel": channel,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **{category: sorted(values.values(), key=lambda row: row["name"].casefold()) for category, values in buckets.items()},
    }


def write_asset_catalog(path: str | Path, catalog: dict) -> None:
    Path(path).write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
