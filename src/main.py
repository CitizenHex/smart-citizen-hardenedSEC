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

    # Migrate global source from any remote URL to local P4K cache path (v0.6.0+)
    AppSettings.migrate_global_to_p4k_local()

    # Migrate contracts source from MrKraken to OsirisDevworks-hosted (v0.6.0+)
    AppSettings.migrate_contracts_to_osiris()

    # Configure Components source to OsirisDevworks default if not already set (v0.5.1+)
    AppSettings.migrate_components_source_to_default()

    # Configure Commodities source to OsirisDevworks default if not already set (v0.5.1+)
    AppSettings.migrate_commodities_source_to_default()

    # Configure Ships source to OsirisDevworks default if not already set (v0.5.2+)
    AppSettings.migrate_ships_source_to_default()

    # Configure Gear source to OsirisDevworks default if not already set (v0.5.2+)
    AppSettings.migrate_gear_source_to_default()

    # Move user data files from old AppData location to Documents (idempotent)
    AppSettings.migrate_data_to_documents()

    # Always keep user source path in sync with canonical overrides location
    AppSettings.set_source_path(AppSettings.SOURCE_USER, str(AppSettings.get_overrides_path()))

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