import re
from dataclasses import dataclass


@dataclass
class StringEntry:
    """Represents a localization string entry."""
    key: str
    source_file: str              # "global" or "vehicles"
    category: str                 # Extracted from key prefix
    original_value: str           # From merged sources (base file + others)
    custom_value: str             # From target_strings.ini (or empty)
    status: str                   # "Modified" | "Unmodified" | "New"

    @property
    def is_modified(self) -> bool:
        """Check if custom value differs from original."""
        return bool(self.custom_value and self.custom_value != self.original_value)

    @staticmethod
    def extract_category(key: str) -> str:
        """Extract category from key prefix.

        Rules:
        - Keys starting with `vehicle_Name` → category "Ships"
        - Keys starting with `item_Name(SHLD|POWR|COOL|QDRV|JUMP)` → category "Ship Components"
        - Mission-related keys (contracts, shubin, blackbox, hockrow, etc.) → "Missions"
        - Everything else → "Other"
        """
        if not key:
            return "Other"

        # Ship/vehicle names and descriptions: vehicle_NameANVL_Carrack, vehicle_DescANVL_Carrack -> Ships
        key_lower = key.lower()
        if key_lower.startswith("vehicle_name") or key_lower.startswith("vehicle_desc"):
            return "Ships"

        # item_Name* / item_Desc* keys — resolve in priority order
        fps_weapon_words = ["_rifle_", "_pistol_", "_smg_", "_shotgun_", "_sniper_", "_launcher_", "_lmg_", "_hmg_", "_knife_", "_multi_"]
        if key.startswith("item_Name") or key.startswith("item_Desc"):
            # Turrets are ship components despite having the item_Name_/item_Desc_ prefix
            if key.startswith("item_Name_Turret") or key.startswith("item_Desc_Turret"):
                return "Ship Components"

            # FPS gear uses item_Name_ / item_Desc_ (underscore directly after Name/Desc)
            if key.startswith("item_Name_") or key.startswith("item_Desc_"):
                return "Gear"

            # Ship component type codes: SHLD, POWR, COOL, QDRV, JUMP, MISL, BOMB
            components = ["SHLD", "POWR", "COOL", "QDRV", "JUMP", "MISL", "GMISL", "BOMB"]
            if any(
                key.startswith(f"item_Name{comp}_") or
                key.startswith(f"item_Desc{comp}_")
                for comp in components
            ):
                return "Ship Components"

            # Ship weapons: contain a ship-size designator (_S1, _S02, etc.)
            if re.search(r'_S\d+', key):
                return "Ship Components"

            # FPS weapons without underscore separator (e.g. item_NameGMNI_rifle_*)
            if any(w in key_lower for w in fps_weapon_words):
                return "Gear"

        # Commodity items
        if key_lower.startswith("items_commodities_"):
            return "Commodities"

        # Mission-related keys (from contracts.ini or similar mission sources)
        mission_patterns = [
            "shubin_", "Shubin_",           # Shubin mining missions
            "blackbox_", "BlackBox_",       # Black box recovery
            "hockrow_", "Hockrow_",         # Hockrow facility
            "contract", "Contract",         # General contracts
            "mission_", "Mission_",         # General missions
            "jt_", "JT_",                   # Job terminals
        ]
        if any(key_lower.startswith(pattern.lower()) for pattern in mission_patterns):
            return "Missions"

        return "Other"
