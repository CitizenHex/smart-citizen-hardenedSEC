"""SC Localization Editor - Main entry point."""
import ctypes
import logging
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from src.gui.main_window import MainWindow
from src.utils.version import get_version
from src.utils.settings import AppSettings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Application entry point."""
    logger.info(f"Starting SC Localization Editor v{get_version()}")

    # Migrate legacy settings to new data source format
    AppSettings.migrate_legacy_settings()

    # Ensure overrides.ini exists (create empty if first run)
    AppSettings.ensure_overrides_file()

    # Required on Windows so the taskbar groups the app under its own icon
    # instead of the Python interpreter icon.
    if sys.platform == 'win32':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            'OsirisDevWorks.SCLocalizationEditor'
        )

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    logger.info("Application window shown")
    sys.exit(app.exec())


if __name__ == '__main__':
    main()