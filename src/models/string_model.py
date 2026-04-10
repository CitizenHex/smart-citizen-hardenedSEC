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
        if key_lower.startswith("item_name") or key_lower.startswith("item_desc"):
            # Turrets are ship components despite having the item_Name_/item_Desc_ prefix
            if key_lower.startswith("item_name_turret") or key_lower.startswith("item_desc_turret"):
                return "Ship Components"

            # Ship component type codes: SHLD, POWR, COOL, QDRV, JUMP, MISL, BOMB (check BEFORE FPS gear)
            # Handles both: item_NameQDRV_... and item_Name_QDRV_... (with or without underscore)
            # Case-insensitive matching for items with lowercase names
            components = ["SHLD", "POWR", "COOL", "QDRV", "JUMP", "MISL", "GMISL", "BOMB"]
            if any(
                key_lower.startswith(f"item_name{comp.lower()}_") or
                key_lower.startswith(f"item_desc{comp.lower()}_") or
                key_lower.startswith(f"item_name_{comp.lower()}_") or
                key_lower.startswith(f"item_desc_{comp.lower()}_")
                for comp in components
            ):
                return "Ship Components"

            # Ship weapons: contain a ship-size designator (_S1, _S02, _XL-1, etc.)
            # Matches: _S\d+ (S1, S02), _XL, _XXL, _L, _M, _S (size codes with optional hyphen+number)
            if re.search(r'_S\d+|_X{1,2}L(-\d+)?|_[LMS](-\d+)?', key, re.IGNORECASE):
                return "Ship Components"

            # FPS weapons: check for FPS weapon words or patterns (BEFORE generic item_Name_ check)
            if any(w in key_lower for w in fps_weapon_words):
                return "Gear"

            # FPS armor/equipment (armor, helmet, suit, vest)
            if any(armor in key_lower for armor in ["armor", "helmet", "suit", "vest", "glasses"]):
                return "Gear"

            # FPS gear uses item_Name_ / item_Desc_ (underscore directly after Name/Desc)
            # Only if it doesn't match any ship component pattern above
            if key_lower.startswith("item_name_") or key_lower.startswith("item_desc_"):
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


def test_category_extraction():
    """Test category extraction for edge cases."""
    # Ship components with underscore between Name and component code
    assert StringEntry.extract_category("item_Name_QDRV_RSI_S02_Hemera") == "Ship Components"
    assert StringEntry.extract_category("item_Desc_QDRV_RSI_S02_Hemera") == "Ship Components"

    # Ship components with lowercase item_name (from Data.p4k extraction)
    assert StringEntry.extract_category("item_nameQDRV_RSI_S02_Hemera_SCItem") == "Ship Components"
    assert StringEntry.extract_category("item_descqdrv_rsi_s02_hemera_scitem") == "Ship Components"

    # Ship weapons with XL size designator
    assert StringEntry.extract_category("item_Name_XL-1_something") == "Ship Components"
    assert StringEntry.extract_category("item_Name_XXL_something") == "Ship Components"

    # Regular ship components (original patterns)
    assert StringEntry.extract_category("item_NameSHLD_Aspirum") == "Ship Components"
    assert StringEntry.extract_category("item_NamePOWR_TR1") == "Ship Components"
    assert StringEntry.extract_category("item_Name_Turret_S1") == "Ship Components"

    # FPS weapons (should still work)
    assert StringEntry.extract_category("item_Name_rifle") == "Gear"

    print("[PASS] All category extraction tests passed!")
