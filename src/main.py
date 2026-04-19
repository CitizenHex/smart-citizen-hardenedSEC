"""Smart Citizen - Main entry point."""
import ctypes
import logging
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from src.gui.main_window import MainWindow
from src.gui.theme import apply_theme, load_application_fonts
from src.utils.version import get_version
from src.utils.settings import AppSettings

# Setup logging — use --debug flag or LOG_LEVEL env var for perf timing output
import os
_log_level = logging.DEBUG if ('--debug' in sys.argv or os.environ.get('LOG_LEVEL', '').upper() == 'DEBUG') else logging.INFO
logging.basicConfig(
    level=_log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Application entry point."""
    logger.info(f"Starting Smart Citizen v{get_version()}")

    # Migrate legacy settings to new data source format
    AppSettings.migrate_legacy_settings()

    # Migrate global source from any remote URL to local P4K cache path (v0.6.0+)
    AppSettings.migrate_global_to_p4k_local()

    # Move user data files from old AppData location to Documents (idempotent)
    AppSettings.migrate_data_to_documents()

    # Always keep user source path in sync with canonical user.ini location
    AppSettings.set_source_path(AppSettings.SOURCE_USER, str(AppSettings.get_user_ini_path()))

    # Ensure user.ini exists (create empty if first run)
    AppSettings.ensure_user_ini_file()

    # Required on Windows so the taskbar groups the app under its own icon
    # instead of the Python interpreter icon.
    if sys.platform == 'win32':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            'OsirisDevWorks.SmartCitizen'
        )

    app = QApplication(sys.argv)
    load_application_fonts()
    apply_theme(app, AppSettings.get_theme())
    window = MainWindow()
    window.show()

    logger.info("Application window shown")
    sys.exit(app.exec())


if __name__ == '__main__':
    main()