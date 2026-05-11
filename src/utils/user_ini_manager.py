"""User INI persistence and import utilities."""
import logging
from pathlib import Path
from typing import Dict, List

from src.models.string_model import StringEntry
from src.parser.ini_parser import parse_ini_file
from src.utils.perf import timed

logger = logging.getLogger(__name__)


def should_autosave_user_ini(entries: List[StringEntry], user_ini_path: Path) -> bool:
    """Decide whether the close-time autosave is safe to run.

    Returns False — and the caller skips the write — when the in-memory entry
    list has zero modified entries but ``user_ini_path`` already exists on
    disk with non-zero content. Under those conditions a write would
    truncate the file to 0 bytes, which is the data-loss path reported
    against 1.3.0: a load mismatch (channel/path drift after a migration,
    or a transient I/O hiccup) leaves every entry with an empty
    ``custom_value``, and the unconditional close-time write then clobbers
    a populated user.ini with an empty one.

    All other cases return True:
      * Modified entries exist → write captures the user's edits.
      * File doesn't exist → first save, nothing to protect.
      * File is already empty → write is a no-op rewrite.

    Trade-off: a user who manually reverts *every* edit and closes will
    not have their clear persisted via autosave. The explicit Apply-to-Game
    path remains the authoritative "persist current state" action.
    """
    if any(e.is_modified for e in entries):
        return True
    try:
        if user_ini_path.exists() and user_ini_path.stat().st_size > 0:
            logger.warning(
                f"Skipping autosave: in-memory state has no overrides but "
                f"on-disk user.ini has {user_ini_path.stat().st_size} bytes "
                f"({user_ini_path}). Preserving disk contents to guard against "
                f"a load mismatch."
            )
            return False
    except OSError as e:
        logger.warning(f"Could not stat user.ini for autosave guard ({user_ini_path}): {e}")
    return True


@timed
def save_user_ini(entries: List[StringEntry], user_ini_path: Path) -> int:
    """Write only user-modified entries to user.ini.

    Args:
        entries: List of StringEntry objects from self.entries
        user_ini_path: Destination path for user.ini

    Returns:
        Number of entries written

    Raises:
        IOError: If write fails
    """
    # Filter to entries the user actually modified (custom differs from original)
    user_edits = {
        entry.key: entry.custom_value
        for entry in entries
        if entry.is_modified
    }

    user_ini_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(user_ini_path, 'w', encoding='utf-8') as f:
            for key, value in user_edits.items():
                f.write(f"{key}={value}\n")

        count = len(user_edits)
        logger.info(f"Saved {count} user edits to {user_ini_path}")
        return count

    except Exception as e:
        logger.error(f"Failed to save user.ini: {e}")
        raise


@timed
def save_user_ini_dict(data: Dict[str, str], user_ini_path: Path) -> int:
    """Write a raw key-value dict to user.ini.

    Used by the import flow where we have a pre-merged dict rather than
    StringEntry objects.

    Args:
        data: Dict of key → value pairs to write
        user_ini_path: Destination path for user.ini

    Returns:
        Number of entries written
    """
    user_ini_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(user_ini_path, 'w', encoding='utf-8') as f:
            for key, value in data.items():
                f.write(f"{key}={value}\n")

        count = len(data)
        logger.info(f"Saved {count} entries to {user_ini_path}")
        return count

    except Exception as e:
        logger.error(f"Failed to save user.ini: {e}")
        raise


@timed
def generate_user_ini_from_diff(
    reference_path: Path,
    current_path: Path,
    user_ini_path: Path
) -> int:
    """Diff reference vs current file, write differing keys as user.ini.

    Used on first run to bootstrap user edits from existing game file.

    Args:
        reference_path: Path to reference base file (base.ini)
        current_path: Path to current game file (global.ini)
        user_ini_path: Destination path for user.ini

    Returns:
        Number of entries written, or 0 if skipped (missing files, etc.)
    """
    if not reference_path.exists():
        logger.debug(f"Reference file not found: {reference_path}")
        return 0

    if not current_path.exists():
        logger.debug(f"Current file not found: {current_path}")
        return 0

    if user_ini_path.exists():
        logger.debug(f"user.ini already exists: {user_ini_path}")
        return 0

    try:
        reference = parse_ini_file(reference_path)
        current = parse_ini_file(current_path)

        diffs = {}
        for key, current_value in current.items():
            reference_value = reference.get(key, "")
            if current_value != reference_value:
                diffs[key] = current_value

        if not diffs:
            logger.info("No differences found between reference and current file")
            return 0

        user_ini_path.parent.mkdir(parents=True, exist_ok=True)
        with open(user_ini_path, 'w', encoding='utf-8') as f:
            for key, value in diffs.items():
                f.write(f"{key}={value}\n")

        logger.info(f"Bootstrapped {len(diffs)} user edits from diff")
        return len(diffs)

    except Exception as e:
        logger.warning(f"Failed to generate user.ini from diff: {e}")
        return 0
