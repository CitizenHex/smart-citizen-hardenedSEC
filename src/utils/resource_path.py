"""Resource-path helpers shared by the GUI and the worker thread modules.

PyInstaller bundles the project tree under ``sys._MEIPASS`` at runtime; outside
the bundle, resources are read from the project root. Both the main window
(asset images, ABOUT.md, HELP.md, tutorial.json) and the worker threads
(DataForge patch files) need to resolve paths against the same base, so the
helpers live here in one place.
"""

import os
import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> str:
    """Return the absolute path for a bundled resource.

    Works for both development runs (``python src/main.py``) and frozen
    PyInstaller builds (``sys._MEIPASS`` is set).
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        # Not running as a PyInstaller bundle — anchor at the project root
        # (this file lives at <root>/src/utils/resource_path.py).
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return os.path.join(base_path, relative_path)


def resolve_patches_dir() -> Path:
    """Return the path to the bundled DataForge patches directory."""
    return Path(get_resource_path("patches"))
