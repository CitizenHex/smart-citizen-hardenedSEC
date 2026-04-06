"""Version reader utility."""
import sys
from pathlib import Path


def get_version() -> str:
    """Read version from VERSION.TXT file.

    Returns:
        Version string (e.g., "0.5.0"), or "0.1.0" if file not found
    """
    # When running from a PyInstaller bundle, data files land in sys._MEIPASS
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent.parent.parent

    version_file = base_path / 'VERSION.TXT'
    if version_file.exists():
        try:
            return version_file.read_text(encoding='utf-8').strip()
        except Exception:
            pass

    return '0.1.0'
