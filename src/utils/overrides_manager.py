"""Overrides persistence and migration utilities."""
import logging
from pathlib import Path
from typing import List

from src.models.string_model import StringEntry
from src.parser.ini_parser import parse_ini_file

logger = logging.getLogger(__name__)


def save_overrides(entries: List[StringEntry], overrides_path: Path) -> int:
    """Write only modified/new entries to overrides.ini.

    Args:
        entries: List of StringEntry objects from self.entries
        overrides_path: Destination path for overrides.ini

    Returns:
        Number of overrides written

    Raises:
        IOError: If write fails
    """
    # Filter to modified and new entries
    overrides = {
        entry.key: entry.custom_value
        for entry in entries
        if entry.custom_value  # Non-empty custom value
    }

    # Create parent directory
    overrides_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    try:
        with open(overrides_path, 'w', encoding='utf-8') as f:
            for key, value in overrides.items():
                f.write(f"{key}={value}\n")

        count = len(overrides)
        logger.info(f"Saved {count} overrides to {overrides_path}")
        return count

    except Exception as e:
        logger.error(f"Failed to save overrides: {e}")
        raise


def generate_overrides_from_diff(
    reference_path: Path,
    current_path: Path,
    overrides_path: Path
) -> int:
    """Diff reference vs current file, write differing keys as overrides.ini.

    Used on first run to bootstrap overrides from existing game file.

    Args:
        reference_path: Path to reference global.ini (data/global.ini)
        current_path: Path to current global.ini (LIVE/data/Localization/english/global.ini)
        overrides_path: Destination path for overrides.ini

    Returns:
        Number of overrides written, or 0 if skipped (missing files, etc.)
    """
    # Guard: skip if files don't exist
    if not reference_path.exists():
        logger.debug(f"Reference file not found: {reference_path}")
        return 0

    if not current_path.exists():
        logger.debug(f"Current file not found: {current_path}")
        return 0

    # Guard: skip if overrides already exist
    if overrides_path.exists():
        logger.debug(f"Overrides already exist: {overrides_path}")
        return 0

    try:
        # Parse both files
        reference = parse_ini_file(reference_path)
        current = parse_ini_file(current_path)

        # Find differing keys
        overrides = {}
        for key, current_value in current.items():
            reference_value = reference.get(key, "")
            if current_value != reference_value:
                overrides[key] = current_value

        if not overrides:
            logger.info("No differences found between reference and current file")
            return 0

        # Write overrides file
        overrides_path.parent.mkdir(parents=True, exist_ok=True)
        with open(overrides_path, 'w', encoding='utf-8') as f:
            for key, value in overrides.items():
                f.write(f"{key}={value}\n")

        logger.info(f"Bootstrapped {len(overrides)} overrides from diff")
        return len(overrides)

    except Exception as e:
        logger.warning(f"Failed to generate overrides from diff: {e}")
        return 0
