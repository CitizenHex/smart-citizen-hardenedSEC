"""Version reader utility."""
from pathlib import Path


def get_version() -> str:
    """Read version from VERSION.TXT file.

    Returns:
        Version string (e.g., "0.1.0"), or "0.1.0" if file not found
    """
    version_file = Path(__file__).parent.parent.parent / 'VERSION.TXT'

    if version_file.exists():
        try:
            return version_file.read_text(encoding='utf-8').strip()
        except Exception:
            pass

    return '0.1.0'
