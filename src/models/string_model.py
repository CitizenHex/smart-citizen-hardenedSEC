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

        # Ship/vehicle names: vehicle_NameANVL_Carrack -> Ships
        if key.startswith("vehicle_Name"):
            return "Ships"

        # Ship components: item_NameSHLD_*, item_Name_SHLD_*, item_NamePOWR_*, etc.
        if key.startswith("item_Name"):
            components = ["SHLD", "POWR", "COOL", "QDRV", "JUMP"]
            if any(key.startswith(f"item_Name{comp}_") or key.startswith(f"item_Name_{comp}_") for comp in components):
                return "Ship Components"

        # Mission-related keys (from contracts.ini or similar mission sources)
        mission_patterns = [
            "shubin_", "Shubin_",           # Shubin mining missions
            "blackbox_", "BlackBox_",       # Black box recovery
            "hockrow_", "Hockrow_",         # Hockrow facility
            "contract", "Contract",         # General contracts
            "mission_", "Mission_",         # General missions
            "jt_", "JT_",                   # Job terminals
        ]
        key_lower = key.lower()
        if any(key_lower.startswith(pattern.lower()) for pattern in mission_patterns):
            return "Missions"

        return "Other"
