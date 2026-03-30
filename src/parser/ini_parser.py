"""INI file parser for localization strings."""
from pathlib import Path
from typing import Dict, List

from src.models.string_model import StringEntry


def parse_ini_file(path: str | Path) -> Dict[str, str]:
    """Parse INI file line-by-line, preserving efficiency.

    Args:
        path: Path to INI file

    Returns:
        Dictionary of key-value pairs
    """
    result = {}
    path = Path(path)

    if not path.exists():
        return result

    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.rstrip('\n\r')

                # Skip empty lines and comments
                if not line.strip() or line.strip().startswith(';'):
                    continue

                # Split on first '=' only
                if '=' not in line:
                    continue

                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                if key:
                    result[key] = value
    except Exception as e:
        print(f"Error parsing INI file {path}: {e}")

    return result


def load_source_files(
    base_path: str | Path,
    custom_path: str | Path | None = None,
    contracts_path: str | Path | None = None,
) -> List[StringEntry]:
    """Load source files and build StringEntry list.

    Args:
        base_path: Path to base global.ini (CIG original or existing language pack)
        custom_path: Optional path to target_strings.ini (user overrides)
        contracts_path: Optional path to contracts.ini (mission strings from MrKraken/StarStrings)

    Returns:
        List of StringEntry objects with comparison status
    """
    entries = []

    # Load all source data
    base_strings = parse_ini_file(base_path)
    custom_strings = parse_ini_file(custom_path) if custom_path else {}

    # Process global.ini entries
    for key, original_value in base_strings.items():
        # Skip vehicle_Name entries ending with _short
        if key.startswith("vehicle_Name") and key.endswith("_short"):
            continue

        custom_value = custom_strings.get(key, '')
        status = _determine_status(original_value, custom_value)

        entry = StringEntry(
            key=key,
            source_file='global.ini',
            category=StringEntry.extract_category(key),
            original_value=original_value,
            custom_value=custom_value,
            status=status
        )
        entries.append(entry)

    # Process contracts.ini entries (Missions) - takes precedence over global.ini entries
    base_keys = set(base_strings.keys())
    if contracts_path:
        contracts_strings = parse_ini_file(contracts_path)
        contracts_keys = set(contracts_strings.keys())

        # Remove any global.ini entries that contracts.ini overrides
        entries = [e for e in entries if e.key not in contracts_keys]

        for key, original_value in contracts_strings.items():
            custom_value = custom_strings.get(key, '')
            entry = StringEntry(
                key=key,
                source_file='contracts.ini',
                category='Missions',
                original_value=original_value,
                custom_value=custom_value,
                status=_determine_status(original_value, custom_value),
            )
            entries.append(entry)

        # Update base_keys to include contracts keys for custom-only pass
        base_keys = set(base_strings.keys()) | contracts_keys

    # Process any custom-only entries (new strings not in base or contracts)
    for key, custom_value in custom_strings.items():
        if key not in base_keys:
            entry = StringEntry(
                key=key,
                source_file='custom',
                category=StringEntry.extract_category(key),
                original_value='',
                custom_value=custom_value,
                status='New'
            )
            entries.append(entry)

    return entries


def load_overrides(target_path: str | Path) -> Dict[str, str]:
    """Load override strings from target_strings.ini.

    Args:
        target_path: Path to target_strings.ini

    Returns:
        Dictionary of overrides
    """
    return parse_ini_file(target_path)


def _determine_status(original_value: str, custom_value: str) -> str:
    """Determine status of an entry."""
    if not custom_value:
        return 'Unmodified'
    if custom_value != original_value:
        return 'Modified'
    return 'Unmodified'
