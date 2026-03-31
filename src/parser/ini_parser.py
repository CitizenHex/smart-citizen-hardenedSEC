"""INI file parser for localization strings."""
import logging
from pathlib import Path
from typing import Dict, List, Optional

from src.models.string_model import StringEntry
from src.merger.ini_merger import merge_sources_by_hierarchy

logger = logging.getLogger(__name__)


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
    sources_dict: Dict[str, Dict[str, str]],
    hierarchy: List[str],
    user_overrides: Optional[Dict[str, str]] = None,
    custom_path: Optional[str | Path] = None,
) -> List[StringEntry]:
    """Load source files and build StringEntry list using hierarchy merge.

    Merges multiple sources in hierarchy order, then creates StringEntry objects.
    The original_value field contains the merged baseline. The custom_value field
    starts empty and will be populated when user edits in the UI.

    Args:
        sources_dict: Dictionary mapping source names to their key-value dicts.
                     e.g., {"global": {...}, "contracts": {...}, "components": {...}}
        hierarchy: Ordered list of source names to merge.
                  e.g., ["global", "contracts", "components"]
        user_overrides: Optional dict of pre-existing user edits to apply with highest priority.
                       Applied after all sources are merged.
        custom_path: DEPRECATED. Kept for backward compatibility. Use user_overrides instead.

    Returns:
        List of StringEntry objects with merged baseline values and user edits applied.
        custom_value will contain pre-existing edits if user_overrides provided.
    """
    entries = []

    # Handle legacy custom_path parameter
    if custom_path and not user_overrides:
        user_overrides = parse_ini_file(custom_path)

    # Merge all sources in hierarchy order, with user overrides as highest priority
    merged_values = merge_sources_by_hierarchy(sources_dict, hierarchy, user_overrides)

    # Track which source each key came from (for status calculation)
    source_origin: Dict[str, str] = {}
    for source_name in hierarchy:
        if source_name in sources_dict:
            source_data = sources_dict[source_name]
            for key in source_data.keys():
                source_origin[key] = source_name

    # If user has pre-existing overrides, track those too
    if user_overrides:
        for key in user_overrides.keys():
            source_origin[key] = 'user'

    # Create StringEntry for each key in merged result
    base_source = hierarchy[0] if hierarchy else 'global'
    for key, merged_value in merged_values.items():
        # Skip vehicle_Name entries ending with _short
        if key.startswith("vehicle_Name") and key.endswith("_short"):
            continue

        source = source_origin.get(key, base_source)
        status = _determine_status_from_source(source, base_source)

        # Determine category based on source
        # Contracts/User entries are marked as Missions if they came from contracts
        if source == 'contracts':
            category = 'Missions'
        else:
            category = StringEntry.extract_category(key)

        entry = StringEntry(
            key=key,
            source_file=source,
            category=category,
            original_value=merged_value,
            custom_value='',  # Start empty; user edits populate this in UI
            status=status
        )
        entries.append(entry)

    return entries


def load_sources_from_settings() -> tuple[Dict[str, Dict[str, str]], List[str]]:
    """Load all sources from application settings.

    For remote URLs, downloads to cache if missing, then loads from cache.
    For local paths, loads directly.

    Returns:
        Tuple of (sources_dict, hierarchy) where:
        - sources_dict: Dict mapping source names to key-value dicts
        - hierarchy: List of source names in merge order
    """
    from src.utils.settings import AppSettings
    from src.utils.updater import download_file

    sources_dict: Dict[str, Dict[str, str]] = {}
    hierarchy = AppSettings.get_merge_hierarchy()

    # Map source names to their cached file names
    cache_mapping = {
        AppSettings.SOURCE_GLOBAL: "base.ini",
        AppSettings.SOURCE_CONTRACTS: "contracts.ini",
        AppSettings.SOURCE_COMPONENTS: "components.ini",
        AppSettings.SOURCE_SHIPS: "ships.ini",
    }

    # Load each configured source
    for source_name in AppSettings.AVAILABLE_SOURCES:
        if not AppSettings.is_source_enabled(source_name):
            continue

        source_path = AppSettings.get_source_path(source_name)
        if not source_path:
            continue

        try:
            # Handle URLs vs local files
            if source_path.startswith('http://') or source_path.startswith('https://'):
                # For remote sources, try to load from cached local file
                if source_name in cache_mapping:
                    cache_file = Path(__file__).parent.parent.parent / "data" / cache_mapping[source_name]

                    # Download if cache doesn't exist
                    if not cache_file.exists():
                        try:
                            logger.info(f"Downloading {source_name} to cache: {source_path}")
                            download_file(source_path, cache_file)
                        except Exception as e:
                            logger.warning(f"Failed to download {source_name}: {e}")
                            continue

                    # Load from cache
                    source_data = parse_ini_file(cache_file)
                    if source_data:
                        sources_dict[source_name] = source_data
                continue

            source_data = parse_ini_file(source_path)
            if source_data:
                sources_dict[source_name] = source_data
        except Exception as e:
            logger.warning(f"Failed to load source {source_name} from {source_path}: {e}")

    return sources_dict, hierarchy


def load_overrides(target_path: str | Path) -> Dict[str, str]:
    """Load override strings from target_strings.ini.

    Args:
        target_path: Path to target_strings.ini

    Returns:
        Dictionary of overrides
    """
    return parse_ini_file(target_path)


def _determine_status(original_value: str, custom_value: str) -> str:
    """Determine status of an entry (legacy, kept for compatibility)."""
    if not custom_value:
        return 'Unmodified'
    if custom_value != original_value:
        return 'Modified'
    return 'Unmodified'


def _determine_status_from_source(source_name: str, base_source: str) -> str:
    """Determine status based on which source provided the value.

    Args:
        source_name: Name of the source that provided this value
        base_source: Name of the base source (usually 'global')

    Returns:
        Status string: 'Modified' if from higher-priority source or user,
                      'Unmodified' if from base source
    """
    if source_name == 'user':
        return 'Modified'  # User explicitly customized
    if source_name == base_source:
        return 'Unmodified'  # From base, not overridden
    return 'Modified'  # Overridden by higher-priority source
