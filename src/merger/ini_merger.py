"""INI file merger for combining base and custom strings."""
from pathlib import Path
from typing import Dict, List, Optional


def merge_sources_by_hierarchy(
    sources_dict: Dict[str, Dict[str, str]],
    hierarchy: List[str],
    user_overrides: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """Merge multiple INI sources in specified hierarchy order.

    Sources earlier in hierarchy have lower priority. Sources later in hierarchy
    overwrite earlier ones. User overrides (if provided) always have highest priority
    and are applied last.

    Args:
        sources_dict: Dictionary mapping source name to its key-value pairs.
                     e.g., {"global": {"key1": "val1", ...}, "contracts": {...}}
        hierarchy: Ordered list of source names to merge in order.
                  e.g., ["global", "contracts", "components"]
                  Earlier = lower priority, later = higher priority
        user_overrides: Optional dict of user edits (highest priority).
                       Applied last, overwrites all other sources.

    Returns:
        Merged dictionary with final values from all sources applied in order.

    Example:
        >>> sources = {
        ...     "global": {"key1": "base_val", "key2": "val2"},
        ...     "contracts": {"key1": "override_val", "key3": "val3"},
        ...     "components": {"key4": "val4"}
        ... }
        >>> hierarchy = ["global", "contracts", "components"]
        >>> user = {"key1": "user_val"}
        >>> result = merge_sources_by_hierarchy(sources, hierarchy, user)
        >>> result["key1"]
        'user_val'  # User override always wins
        >>> result["key3"]
        'val3'      # From contracts (overrides global)
        >>> result["key2"]
        'val2'      # From global (only source for this key)
    """
    result: Dict[str, str] = {}

    # Process each source in hierarchy order
    # Earlier sources are base, later sources overwrite
    for source_name in hierarchy:
        if source_name not in sources_dict:
            continue

        source_data = sources_dict[source_name]
        for key, value in source_data.items():
            result[key] = value

    # Apply user overrides last (highest priority)
    if user_overrides:
        for key, value in user_overrides.items():
            result[key] = value

    return result


def merge_ini_files(
    source_path: str | Path,
    overrides_dict: Dict[str, str],
    output_path: str | Path
) -> None:
    """Merge source INI with overrides, preserving all lines.

    Reads source file line-by-line, replaces values for matching keys,
    and writes to output as UTF-8.

    Args:
        source_path: Path to base file (base.ini or game's global.ini)
        overrides_dict: Dictionary of key-value overrides
        output_path: Path to write merged output
    """
    source_path = Path(source_path)
    output_path = Path(output_path)

    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(source_path, 'r', encoding='utf-8') as infile, \
             open(output_path, 'w', encoding='utf-8') as outfile:

            for line in infile:
                # Preserve line ending style, but work with stripped version
                line_rstrip = line.rstrip('\n\r')
                original_ending = line[len(line_rstrip):]

                # Skip processing for comments and empty lines
                if not line_rstrip.strip() or line_rstrip.strip().startswith(';'):
                    outfile.write(line)
                    continue

                # Try to split on first '='
                if '=' not in line_rstrip:
                    outfile.write(line)
                    continue

                key, value = line_rstrip.split('=', 1)
                key_stripped = key.strip()

                # Check if we have an override for this key
                if key_stripped in overrides_dict:
                    # Replace value, preserving key spacing
                    new_value = overrides_dict[key_stripped]
                    new_line = f"{key}={new_value}{original_ending}"
                    outfile.write(new_line)
                else:
                    # Keep original line
                    outfile.write(line)

    except Exception as e:
        raise IOError(f"Error merging INI files: {e}")
