"""Small, reusable safety checks for user-selected local import files."""
from __future__ import annotations

from pathlib import Path


MAX_INI_IMPORT_BYTES = 4 * 1024 * 1024


def validate_ini_import(path: str | Path) -> Path:
    """Return a safe local INI file path or raise a clear ValueError."""
    candidate = Path(path)
    if not candidate.is_file():
        raise FileNotFoundError(f"Import file not found: {candidate}")
    size = candidate.stat().st_size
    if size > MAX_INI_IMPORT_BYTES:
        raise ValueError(
            f"Import file is too large ({size / 1024 / 1024:.1f} MiB). "
            f"The limit is {MAX_INI_IMPORT_BYTES / 1024 / 1024:.0f} MiB."
        )
    return candidate
