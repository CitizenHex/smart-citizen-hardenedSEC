from dataclasses import dataclass


@dataclass
class StringEntry:
    """Represents a localization string entry."""
    key: str
    source_file: str              # "global" or "vehicles"
    category: str                 # Extracted from key prefix
    original_value: str           # From source global.ini
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

        return "Other"
