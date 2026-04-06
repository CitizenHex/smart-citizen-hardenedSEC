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
        logger.info(f"Loading user overrides from legacy path: {custom_path}")
        user_overrides = parse_ini_file(custom_path)

    logger.info(f"Starting merge of {sum(len(d) for d in sources_dict.values())} total keys from {len(sources_dict)} sources")
    logger.info(f"Hierarchy: {hierarchy}, Sources available: {list(sources_dict.keys())}")

    # Filter hierarchy to only include sources that exist in sources_dict
    filtered_hierarchy = [s for s in hierarchy if s in sources_dict]
    logger.info(f"Filtered hierarchy: {filtered_hierarchy}")

    # Filter each source to only include relevant keys based on source type
    from src.utils.settings import AppSettings

    filtered_sources = {}
    for source_name in filtered_hierarchy:
        source_data = sources_dict[source_name]

        # User source is special - never filter it (it's app-generated overrides)
        if source_name == AppSettings.SOURCE_USER:
            filtered_sources[source_name] = source_data
            continue

        # Map source types to their relevant categories
        source_category_filters = {
            AppSettings.SOURCE_GLOBAL: None,      # No filtering - load all
            AppSettings.SOURCE_CONTRACTS: "Missions",
            AppSettings.SOURCE_COMPONENTS: "Ship Components",
            AppSettings.SOURCE_SHIPS: "Ships",
            "stats": None,                        # No filtering - description keys are "Other"
        }

        category_filter = source_category_filters.get(source_name)

        if category_filter:
            # Filter keys to only those matching the category
            filtered_data = {}
            for key, value in source_data.items():
                if StringEntry.extract_category(key) == category_filter:
                    filtered_data[key] = value
            logger.info(f"Filtered {source_name}: {len(source_data)} keys -> {len(filtered_data)} keys (category: {category_filter})")
            filtered_sources[source_name] = filtered_data
        else:
            # No filtering for this source
            filtered_sources[source_name] = source_data

    try:
        logger.info("Calling merge_sources_by_hierarchy...")
        # Merge all sources in hierarchy order, with user overrides as highest priority
        merged_values = merge_sources_by_hierarchy(filtered_sources, filtered_hierarchy, user_overrides)
        logger.info(f"Merge complete. Result has {len(merged_values)} keys")
    except Exception as e:
        logger.exception(f"Error during merge: {e}")
        raise

    # Track which source each key came from (for status calculation)
    logger.info("Tracking source origin for each key...")
    source_origin: Dict[str, str] = {}
    for source_name in filtered_hierarchy:
        source_data = filtered_sources[source_name]
        for key in source_data.keys():
            source_origin[key] = source_name

    # If user has pre-existing overrides, track those too
    if user_overrides:
        for key in user_overrides.keys():
            source_origin[key] = 'user'
    logger.info(f"Source origin tracking complete. {len(source_origin)} keys tracked")

    # Create StringEntry for each key in merged result
    logger.info("Creating StringEntry objects...")
    base_source = filtered_hierarchy[0] if filtered_hierarchy else 'global'
    entry_count = 0
    for key, merged_value in merged_values.items():
        # Skip abbreviated ship name entries (e.g. vehicle_Name*_short, vehicle_name*_short,P)
        if key.lower().startswith("vehicle_name") and "_short" in key:
            continue

        entry_count += 1
        if entry_count % 10000 == 0:
            logger.debug(f"Processing entry {entry_count} of ~{len(merged_values)}...")

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

    logger.info(f"Created {len(entries)} StringEntry objects successfully")
    return entries


def load_sources_from_settings() -> tuple[Dict[str, Dict[str, str]], List[str]]:
    """Load all sources from application settings.

    For remote URLs, loads from cached local files if available.
    For local paths, loads directly.
    Remote sources are downloaded asynchronously by the update checker, not here.

    Returns:
        Tuple of (sources_dict, hierarchy) where:
        - sources_dict: Dict mapping source names to key-value dicts
        - hierarchy: List of source names in merge order
    """
    from src.utils.settings import AppSettings

    sources_dict: Dict[str, Dict[str, str]] = {}
    hierarchy = AppSettings.get_merge_hierarchy()

    # Map source names to their cached file names in AppData cache
    cache_mapping = {
        AppSettings.SOURCE_GLOBAL: "base.ini",
        AppSettings.SOURCE_CONTRACTS: "contracts.ini",
        AppSettings.SOURCE_COMPONENTS: "components.ini",
        AppSettings.SOURCE_SHIPS: "ships.ini",
    }

    cache_dir = AppSettings.get_cache_dir()

    # Load each configured source
    logger.info(f"Loading sources from settings. Available sources: {AppSettings.AVAILABLE_SOURCES}")
    for source_name in AppSettings.AVAILABLE_SOURCES:
        if not AppSettings.is_source_enabled(source_name):
            logger.debug(f"Source {source_name} is disabled")
            continue

        source_path = AppSettings.get_source_path(source_name)
        if not source_path:
            logger.debug(f"Source {source_name} has no path configured")
            continue

        logger.info(f"Processing source {source_name}: {source_path}")

        try:
            # Handle URLs vs local files
            if source_path.startswith('http://') or source_path.startswith('https://'):
                # For remote sources, load from cached local file in AppData (must exist)
                if source_name in cache_mapping:
                    cache_file = cache_dir / cache_mapping[source_name]
                    logger.info(f"Looking for cache file: {cache_file}")

                    if cache_file.exists():
                        logger.info(f"Cache file found, parsing {source_name}...")
                        source_data = parse_ini_file(cache_file)
                        if source_data:
                            sources_dict[source_name] = source_data
                            logger.info(f"Loaded {len(source_data)} entries from {source_name}")
                        else:
                            logger.warning(f"Parsed {source_name} but got empty result")
                    else:
                        logger.error(f"Remote source {source_name} requires download. Cache not found: {cache_file}")
                        raise FileNotFoundError(f"Source {source_name} cache not found. Run auto-update to download: {cache_file}")
                continue

            # Local file path
            logger.info(f"Loading local file {source_path}...")
            local_file = Path(source_path)

            # User source can be empty on first run
            if source_name == AppSettings.SOURCE_USER:
                if local_file.exists():
                    source_data = parse_ini_file(source_path)
                    if source_data:
                        sources_dict[source_name] = source_data
                        logger.info(f"Loaded {len(source_data)} entries from {source_name}")
                    else:
                        logger.info(f"User overrides file is empty: {source_path}")
                else:
                    logger.info(f"No user overrides yet: {source_path}")
                continue

            # Other local sources must exist
            if not local_file.exists():
                logger.error(f"Local file not found: {source_path}")
                raise FileNotFoundError(f"Source {source_name} file not found: {source_path}")

            source_data = parse_ini_file(source_path)
            if source_data:
                sources_dict[source_name] = source_data
                logger.info(f"Loaded {len(source_data)} entries from {source_name}")
        except Exception as e:
            logger.exception(f"Failed to load source {source_name} from {source_path}: {e}")

    # ── Stats enhancements ───────────────────────────────────────────────────
    if AppSettings.get_stats_enabled():
        stats_combined: Dict[str, str] = {}
        for label, filename in AppSettings.STATS_FILES.items():
            stats_file = cache_dir / filename
            if stats_file.exists():
                data = parse_ini_file(stats_file)
                stats_combined.update(data)
                logger.info(f"Loaded {len(data)} stats entries from {filename}")
            else:
                logger.debug(f"Stats file not found (skipping): {stats_file}")

        if stats_combined:
            sources_dict["stats"] = stats_combined
            logger.info(f"Stats enhancements: {len(stats_combined)} total entries loaded")
            # Insert "stats" just before "user" in the hierarchy (or at end if no user)
            if AppSettings.SOURCE_USER in hierarchy:
                idx = hierarchy.index(AppSettings.SOURCE_USER)
                hierarchy = hierarchy[:idx] + ["stats"] + hierarchy[idx:]
            else:
                hierarchy = hierarchy + ["stats"]

    logger.info(f"load_sources_from_settings complete. Loaded sources: {list(sources_dict.keys())}")
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
