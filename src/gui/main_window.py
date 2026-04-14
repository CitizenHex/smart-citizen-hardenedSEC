"""Main window for SC Localization Editor."""
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QTableWidget,
    QTableWidgetItem, QFileDialog, QMessageBox, QTabWidget,
    QHeaderView, QStatusBar, QFrame, QStyledItemDelegate,
    QAbstractItemView, QMenu, QProgressDialog, QTextBrowser
)
from PyQt6.QtGui import QColor, QFont, QCursor, QPixmap, QIcon
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from src.gui.filter_header import FilterHeaderView

import re as _re

# Shared flag for grouped sort mode — checked by GroupSortItem.__lt__
_grouped_sort_enabled = True

# Pattern 1: item_Name{CONTENT} / item_Desc{CONTENT} (ship items, gear, etc.)
_ITEM_PREFIX_RE = _re.compile(r'^(item_)(Name|Desc|name|desc)(.*)', _re.IGNORECASE)

# Pattern 2: vehicle_Name{CONTENT} / vehicle_Desc{CONTENT} (ships)
_VEHICLE_PREFIX_RE = _re.compile(r'^(vehicle_)(Name|Desc)(.*)', _re.IGNORECASE)

# Pattern 3: {CONTENT}_Title or {CONTENT}_Desc with optional suffix (missions)
# Only match _Title/_Desc near the end — must NOT have another _Title/_Desc after
_MISSION_SUFFIX_RE = _re.compile(
    r'^(.*?)_(title|desc)'          # group + marker
    r'(_[a-zA-Z0-9]*)?$',          # optional single suffix like _001, _intro, _Hard
    _re.IGNORECASE,
)


def _group_sort_key(key: str) -> tuple[str, int]:
    """Return (group_key, sub_order) for grouped sorting.

    Groups related Name/Desc and Title/Desc keys together.
    Names/Titles sort before Descs within the same group.
    """
    # item_Name / item_Desc prefix pattern
    m = _ITEM_PREFIX_RE.match(key)
    if m:
        marker = m.group(2).lower()
        content = m.group(3)
        sub = 0 if marker == "name" else 1
        return (f"item_{content}".lower(), sub)

    # vehicle_Name / vehicle_Desc prefix pattern
    m = _VEHICLE_PREFIX_RE.match(key)
    if m:
        marker = m.group(2).lower()
        content = m.group(3)
        sub = 0 if marker == "name" else 1
        return (f"vehicle_{content}".lower(), sub)

    # Mission _Title / _Desc suffix pattern
    m = _MISSION_SUFFIX_RE.match(key)
    if m:
        group = m.group(1)
        marker = m.group(2).lower()
        sub = 0 if marker == "title" else 1
        return (group.lower(), sub)

    return (key.lower(), 0)


class GroupSortItem(QTableWidgetItem):
    """QTableWidgetItem that supports grouped sorting on the Key column."""

    def __lt__(self, other):
        if _grouped_sort_enabled:
            return _group_sort_key(self.text()) < _group_sort_key(other.text())
        return super().__lt__(other)


class AnimatedProgressDialog(QProgressDialog):
    """Reusable animated progress dialog for long-running operations.

    Creates an indeterminate progress bar that automatically animates.
    Use like: dialog = AnimatedProgressDialog("Loading...", parent)
    """

    def __init__(self, message: str, parent=None, title: str = "Processing"):
        """Initialize indeterminate progress dialog.

        Args:
            message: Status message to display
            parent: Parent widget
            title: Window title
        """
        # Range (0, 0) creates an indeterminate, auto-animating progress bar
        super().__init__(message, None, 0, 0, parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)
        self.show()

from src.models.string_model import StringEntry
from src.parser.ini_parser import load_source_files, load_sources_from_settings, parse_ini_file
from src.utils.settings import AppSettings
from src.merger.ini_merger import merge_sources_by_hierarchy
from src.utils.version import get_version
from src.utils.perf import timed
from src.gui.config_tab import ConfigTab
from src.gui.enhancements_tab import EnhancementsTab
from src.gui.log_tab import LogTab

logger = logging.getLogger(__name__)


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If not running as PyInstaller bundle, use the project root
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return os.path.join(base_path, relative_path)


class FileLoaderWorker(QThread):
    """Worker thread for loading INI files without blocking UI.

    Supports both old-style (single base file) and new-style (multiple sources
    from settings) loading. If sources_dict is provided, uses new system.
    Otherwise, loads configured sources from settings.
    """

    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(
        self,
        base_path: str | None = None,
        overrides_path: str | None = None,
        contracts_path: str | None = None,
        sources_dict=None,
        hierarchy=None
    ):
        super().__init__()
        self.base_path = base_path
        self.overrides_path = overrides_path
        self.contracts_path = contracts_path
        self.sources_dict = sources_dict
        self.hierarchy = hierarchy

    def run(self):
        try:
            logger.info("FileLoaderWorker starting...")

            # New system: load sources from settings if not provided
            if self.sources_dict is None and self.hierarchy is None:
                logger.info("No sources_dict provided, loading from settings...")
                self.sources_dict, self.hierarchy, self._enhancements_key_categories = load_sources_from_settings()
                logger.info(f"Loaded from settings: sources={list(self.sources_dict.keys())}, hierarchy={self.hierarchy}")
            else:
                self._enhancements_key_categories = None

            # If still no sources (empty settings), try legacy base_path
            if self.sources_dict and self.hierarchy:
                logger.info(f"Calling load_source_files with {len(self.sources_dict)} sources")
                entries = load_source_files(self.sources_dict, self.hierarchy, enhancements_key_categories=self._enhancements_key_categories)
                logger.info(f"load_source_files returned {len(entries)} entries")
            elif self.base_path:
                # Legacy: single base file loading
                logger.info(f"Using legacy base_path: {self.base_path}")
                base_data = parse_ini_file(self.base_path)
                sources_dict = {"global": base_data}
                hierarchy = ["global"]
                entries = load_source_files(sources_dict, hierarchy, None, self.overrides_path)
            else:
                raise ValueError("No sources configured and no base_path provided")

            logger.info("FileLoaderWorker finished successfully")
            self.finished.emit(entries)
        except Exception as e:
            logger.exception(f"Error loading files: {e}")
            self.error.emit(str(e))


class StartupSyncWorker(QThread):
    """Worker thread that syncs all enabled remote sources on startup.

    Uses conditional GET (If-Modified-Since) so only changed files are downloaded.
    Emits source_starting before each download, source_synced after, source_error on
    failure. Always emits finished so loading proceeds even when sources fail.
    """

    source_starting = pyqtSignal(str)        # source_name (about to sync)
    source_synced = pyqtSignal(str, bool)    # (source_name, was_updated)
    source_error = pyqtSignal(str, str)      # (source_name, error_message)
    finished = pyqtSignal()

    def run(self):
        from src.utils.updater import download_file_if_changed
        from src.utils.settings import AppSettings

        cache_dir = AppSettings.get_cache_dir()
        cache_mapping = {
            AppSettings.SOURCE_GLOBAL:      "base.ini",
        }

        for source_name in [
            AppSettings.SOURCE_GLOBAL,
        ]:
            if not AppSettings.is_source_enabled(source_name):
                continue
            if not AppSettings.get_source_auto_update(source_name):
                continue

            source_url = AppSettings.get_source_path(source_name)
            if not source_url or not source_url.startswith("http"):
                continue

            self.source_starting.emit(source_name)
            cache_file = cache_dir / cache_mapping.get(source_name, f"{source_name}.ini")
            try:
                updated = download_file_if_changed(source_url, cache_file)
                self.source_synced.emit(source_name, updated)
            except Exception as e:
                logger.warning(f"Startup sync failed for {source_name}: {e}")
                self.source_error.emit(source_name, str(e))

        self.finished.emit()


class EnhancementsGeneratorWorker(QThread):
    """Worker thread for generating enhancements INI files via generate_enhancements_ini.py."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)

    def __init__(self, categories: set[str] | None = None):
        super().__init__()
        self.categories = categories

    def run(self):
        import importlib.util
        import sys as sys_module
        try:
            if getattr(sys, 'frozen', False):
                script_path = Path(sys._MEIPASS) / 'scripts' / 'generate_enhancements_ini.py'
            else:
                script_path = Path(__file__).parent.parent.parent / 'scripts' / 'generate_enhancements_ini.py'

            if not script_path.exists():
                raise FileNotFoundError(f"Enhancements generator script not found: {script_path}")

            self.progress.emit("Loading enhancements generator...")

            module_name = "generate_enhancements_ini_worker"
            if module_name in sys_module.modules:
                del sys_module.modules[module_name]

            spec = importlib.util.spec_from_file_location(module_name, script_path)
            mod = importlib.util.module_from_spec(spec)
            sys_module.modules[module_name] = mod
            spec.loader.exec_module(mod)

            self.progress.emit("Generating enhancements (may take a few minutes on first run)...")
            logger.info("Enhancements generation worker: calling mod.main()")

            base_ini  = AppSettings.get_cache_dir() / 'base.ini'
            forge_dir = AppSettings.get_dataforge_cache_dir()

            cat_desc = ", ".join(sorted(self.categories)) if self.categories else "all"
            logger.info(f"Enhancements generation: base_ini={base_ini}, forge_dir={forge_dir}, categories={cat_desc}")
            mod.main(base_ini, forge_dir, categories=self.categories)
            logger.info("Enhancements generation worker: mod.main() completed successfully")

            self.finished.emit(True)
        except Exception as e:
            logger.exception(f"Enhancements generation failed: {e}")
            self.error.emit(str(e))
            self.finished.emit(False)


class P4kExtractWorker(QThread):
    """Worker thread for extracting global.ini from Data.p4k via unp4k.exe."""

    progress = pyqtSignal(str)   # status message
    finished = pyqtSignal(bool)  # True = success
    error = pyqtSignal(str)      # error message (emitted before finished(False))

    def __init__(self, p4k_path, output_path, unp4k_exe):
        super().__init__()
        self._p4k = p4k_path
        self._out = output_path
        self._exe = unp4k_exe

    def run(self):
        from src.utils.pak_extractor import extract_global_ini
        try:
            extract_global_ini(self._p4k, self._out, self._exe, self.progress.emit)
            self.finished.emit(True)
        except Exception as e:
            logger.exception(f"P4K extraction failed: {e}")
            self.error.emit(str(e))
            self.finished.emit(False)


class DataForgeExtractWorker(QThread):
    """Worker thread for extracting DataForge entity XMLs from Data.p4k."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)

    def __init__(self, p4k_path, unp4k_exe, unforge_exe, cache_dir):
        super().__init__()
        self._p4k       = p4k_path
        self._unp4k_exe = unp4k_exe
        self._unforge_exe = unforge_exe
        self._cache_dir = cache_dir

    def run(self):
        from src.utils.pak_extractor import extract_dataforge
        try:
            extract_dataforge(
                self._p4k,
                self._unp4k_exe,
                self._unforge_exe,
                self._cache_dir,
                self.progress.emit,
            )
            self.finished.emit(True)
        except Exception as e:
            logger.exception(f"DataForge extraction failed: {e}")
            self.error.emit(str(e))
            self.finished.emit(False)


class SelectAllDelegate(QStyledItemDelegate):
    """Custom delegate that selects all text on edit."""

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if hasattr(editor, 'selectAll'):
            editor.selectAll()
        return editor


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"SC Localization Editor v{get_version()}")
        self.setGeometry(100, 100, 1400, 800)

        # Set window icon (taskbar + window title bar + favicon)
        icon_path = get_resource_path(os.path.join("assets", "logo.ico"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Data
        self.entries: list[StringEntry] = []
        self.filtered_row_indices: list[int] = []
        self.default_values: dict = {}  # Store default values from cached base source

        # File loader worker
        self._loader_worker: Optional[FileLoaderWorker] = None

        # Startup sync worker
        self._startup_sync_worker: Optional[StartupSyncWorker] = None

        # P4K extraction worker and progress dialog
        self._p4k_worker: Optional[P4kExtractWorker] = None
        self._p4k_progress: Optional[QProgressDialog] = None

        # Enhancements generation worker
        self._enhancements_worker: Optional[EnhancementsGeneratorWorker] = None
        self._enhancements_progress_dialog: Optional[AnimatedProgressDialog] = None

        # DataForge extraction worker
        self._forge_worker: Optional[DataForgeExtractWorker] = None

        # Track whether we've prompted for enhancements on startup (prevents duplicate dialogs)
        self._enhancements_prompted_on_startup = False
        # Flag to defer enhancements checking until after file loading completes (avoid I/O contention)
        self._check_enhancements_after_loading = False

        # Status bar state (composed message) - tracks sync status per source
        self._source_status: dict[str, str] = {}  # source_name -> status_string

        # Progress dialogs
        self._startup_progress: Optional[AnimatedProgressDialog] = None
        self._loading_progress: Optional[QProgressDialog] = None

        # Build UI
        self.setup_ui()
        self.restore_window_state()

        # Ensure cache directory exists
        AppSettings.get_cache_dir()

        # Defer startup loading until after the window is shown.
        # QTimer.singleShot(0) fires on the next event loop iteration, after show().
        QTimer.singleShot(0, self._start_startup_sync)

        # Ensure user.cfg has language setting
        from src.utils.user_cfg import ensure_user_cfg_language
        ensure_user_cfg_language()

        logger.info("MainWindow initialized")

    def setup_ui(self):
        """Build user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Title bar
        title_label = QLabel("SC Localization Editor")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # Toolbar
        toolbar_layout = self.create_toolbar()
        main_layout.addLayout(toolbar_layout)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self.create_strings_tab(), "Strings")

        # Config tab
        self.config_tab = ConfigTab()
        self.config_tab.merge_requested.connect(self.perform_merge_and_reload)
        self.config_tab.p4k_extract_requested.connect(self._run_p4k_extraction)
        self.config_tab.import_ini_requested.connect(self._handle_import_ini)
        tabs.addTab(self.config_tab, "Config")

        # Enhancements tab
        self.enhancements_tab = EnhancementsTab()
        self.enhancements_tab.merge_requested.connect(self.perform_merge_and_reload)
        self.enhancements_tab.enhancements_pipeline_requested.connect(self._run_enhancements_pipeline)
        self._enhancements_tab_index = tabs.addTab(self.enhancements_tab, "Enhancements")

        self.log_tab = LogTab()
        tabs.addTab(self.log_tab, "Log")

        tabs.addTab(self.create_about_tab(), "About")

        # Revert unapplied enhancement checkbox changes when leaving the tab
        tabs.currentChanged.connect(self._on_tab_changed)
        self._previous_tab_index = tabs.currentIndex()

        main_layout.addWidget(tabs)

        # Footer
        footer_layout = self.create_footer()
        main_layout.addLayout(footer_layout)

    def _on_tab_changed(self, new_index: int):
        """Revert unapplied enhancement checkbox changes when leaving the Enhancements tab."""
        if self._previous_tab_index == self._enhancements_tab_index and new_index != self._enhancements_tab_index:
            self.enhancements_tab.revert_category_checkboxes()
        self._previous_tab_index = new_index

        # Status bar
        self.statusBar().showMessage("Ready")

    def create_toolbar(self) -> QVBoxLayout:
        """Create toolbar with buttons."""
        layout = QVBoxLayout()

        # Button row
        button_layout = QHBoxLayout()

        # Load buttons
        self.load_btn = QPushButton("Load Base File")
        self.load_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 6px;")
        self.load_btn.clicked.connect(self.load_files)
        button_layout.addWidget(self.load_btn)

        self.restore_backup_btn = QPushButton("Restore Backup")
        self.restore_backup_btn.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold; padding: 6px;")
        self.restore_backup_btn.clicked.connect(self.restore_backup)
        button_layout.addWidget(self.restore_backup_btn)

        self.apply_btn = QPushButton("Apply to Game")
        self.apply_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 6px;")
        self.apply_btn.clicked.connect(self.apply_to_game)
        button_layout.addWidget(self.apply_btn)

        self.clear_loc_btn = QPushButton("Clear Localization")
        self.clear_loc_btn.setStyleSheet("background-color: #9E9E9E; color: white; font-weight: bold; padding: 6px;")
        self.clear_loc_btn.setToolTip("Delete the applied global.ini from the game's localization directory, reverting to vanilla game text")
        self.clear_loc_btn.clicked.connect(self.clear_localization)
        button_layout.addWidget(self.clear_loc_btn)

        self.clear_cache_btn = QPushButton("Clear Cache")
        self.clear_cache_btn.setStyleSheet("background-color: #9E9E9E; color: white; font-weight: bold; padding: 6px;")
        self.clear_cache_btn.setToolTip("Delete all cached source files (base.ini, contracts.ini, etc.) from the local cache directory")
        self.clear_cache_btn.clicked.connect(self.clear_cache)
        button_layout.addWidget(self.clear_cache_btn)

        self.open_loc_dir_btn = QPushButton("Open Localization Dir")
        self.open_loc_dir_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 6px;")
        self.open_loc_dir_btn.setToolTip("Open the game's localization directory in Windows Explorer")
        self.open_loc_dir_btn.clicked.connect(self.open_localization_dir)
        button_layout.addWidget(self.open_loc_dir_btn)

        button_layout.addStretch()

        self.help_btn = QPushButton("Help")
        self.help_btn.setMaximumWidth(70)
        self.help_btn.clicked.connect(self.show_help)
        button_layout.addWidget(self.help_btn)

        layout.addLayout(button_layout)

        # Filter row
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(200)
        self.category_combo.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.category_combo)

        filter_layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["All", "Modified", "Unmodified", "New"])
        self.status_combo.setMaximumWidth(120)
        self.status_combo.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.status_combo)

        self.hide_unmodified_check = QCheckBox("Hide Unmodified")
        self.hide_unmodified_check.stateChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.hide_unmodified_check)

        self.favorites_only_check = QCheckBox("★ Favorites Only")
        self.favorites_only_check.stateChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.favorites_only_check)

        self.grouped_sort_check = QCheckBox("Grouped Sort")
        self.grouped_sort_check.setToolTip("Sort titles and descriptions together for the same entity")
        self.grouped_sort_check.setChecked(True)
        self.grouped_sort_check.stateChanged.connect(self._on_grouped_sort_changed)
        filter_layout.addWidget(self.grouped_sort_check)

        self.clear_filters_btn = QPushButton("Clear Filters")
        self.clear_filters_btn.setMaximumWidth(100)
        self.clear_filters_btn.clicked.connect(self.clear_filters)
        filter_layout.addWidget(self.clear_filters_btn)

        self.copy_filtered_btn = QPushButton("Copy Filtered")
        self.copy_filtered_btn.setMaximumWidth(100)
        self.copy_filtered_btn.setToolTip("Copy all visible filtered rows to clipboard (tab-separated)")
        self.copy_filtered_btn.clicked.connect(self.copy_filtered_to_clipboard)
        filter_layout.addWidget(self.copy_filtered_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        return layout

    def create_footer(self) -> QHBoxLayout:
        """Create footer with Osiris DevWorks branding and donation buttons."""
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(8, 8, 8, 0)

        # Osiris DevWorks button (left side)
        self.osiris_button = QLabel()
        osiris_image_path = get_resource_path(os.path.join("assets", "osiris-devworks.png"))

        # Try to load Osiris image, fall back to text if not found
        if os.path.exists(osiris_image_path):
            pixmap = QPixmap(osiris_image_path)
            # Scale to reasonable size (max height 40px)
            if pixmap.height() > 40:
                pixmap = pixmap.scaledToHeight(40, Qt.TransformationMode.SmoothTransformation)
            self.osiris_button.setPixmap(pixmap)
        else:
            # Fallback to styled text button
            self.osiris_button.setText("Osiris DevWorks")
            self.osiris_button.setStyleSheet("""
                QLabel {
                    background-color: #1a1f2e;
                    color: #c9a961;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QLabel:hover {
                    background-color: #242938;
                }
            """)

        self.osiris_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.osiris_button.mousePressEvent = self.open_discord_link
        footer_layout.addWidget(self.osiris_button)

        # Stretch to push donation buttons to the right
        footer_layout.addStretch()

        # Donation label
        donation_label = QLabel("Support this project:")
        donation_label.setStyleSheet("font-size: 12px; color: #666; margin-right: 5px;")
        footer_layout.addWidget(donation_label)

        # PayPal button (right side)
        self.paypal_button = QLabel()
        paypal_image_path = get_resource_path(os.path.join("assets", "paypal.png"))

        # Try to load PayPal image, fall back to text if not found
        if os.path.exists(paypal_image_path):
            paypal_pixmap = QPixmap(paypal_image_path)
            # Scale to match Osiris button (max height 40px)
            if paypal_pixmap.height() > 40:
                paypal_pixmap = paypal_pixmap.scaledToHeight(40, Qt.TransformationMode.SmoothTransformation)
            self.paypal_button.setPixmap(paypal_pixmap)
        else:
            # Fallback to styled text button
            self.paypal_button.setText("Donate via PayPal")
            self.paypal_button.setStyleSheet("""
                QLabel {
                    background-color: #0070ba;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QLabel:hover {
                    background-color: #005ea6;
                }
            """)

        self.paypal_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.paypal_button.mousePressEvent = self.open_paypal_donation
        footer_layout.addWidget(self.paypal_button)

        # Spacer between PayPal and Venmo
        footer_layout.addSpacing(10)

        # Venmo button (right side)
        self.venmo_button = QLabel()
        venmo_image_path = get_resource_path(os.path.join("assets", "venmo.png"))

        # Try to load Venmo image, fall back to text button
        if os.path.exists(venmo_image_path):
            venmo_pixmap = QPixmap(venmo_image_path)
            # Scale to match Osiris button (max height 40px)
            if venmo_pixmap.height() > 40:
                venmo_pixmap = venmo_pixmap.scaledToHeight(40, Qt.TransformationMode.SmoothTransformation)
            self.venmo_button.setPixmap(venmo_pixmap)
        else:
            # Fallback to styled text button
            self.venmo_button.setText("Venmo")
            self.venmo_button.setStyleSheet("""
                QLabel {
                    background-color: #008CFF;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QLabel:hover {
                    background-color: #0074D9;
                }
            """)

        self.venmo_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.venmo_button.mousePressEvent = self.open_venmo_donation
        footer_layout.addWidget(self.venmo_button)

        return footer_layout

    def open_discord_link(self, event):
        """Open Discord invite link in browser."""
        discord_url = "https://discord.gg/BNzRegKZ7k"
        QDesktopServices.openUrl(QUrl(discord_url))

    def open_paypal_donation(self, event):
        """Open PayPal donation link in browser."""
        paypal_url = "https://paypal.me/RighteousKill"
        QDesktopServices.openUrl(QUrl(paypal_url))

    def open_venmo_donation(self, event):
        """Open Venmo donation link in browser."""
        venmo_url = "https://venmo.com/u/Amr-Abouelleil"
        QDesktopServices.openUrl(QUrl(venmo_url))

    def create_strings_tab(self) -> QWidget:
        """Create strings table tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Category", "Key", "Default Value", "Current Value", "★", "Custom Value", "Status"
        ])

        # Per-column filter header
        column_names = ["Category", "Key", "Default Value", "Current Value", "★", "Custom Value", "Status"]
        self.filter_header = FilterHeaderView(column_names, self.table, skip_columns={0, 4, 6})
        self.table.setHorizontalHeader(self.filter_header)
        self.filter_header.filter_changed.connect(self.apply_filters)

        # Table settings
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        # Hide row numbers
        self.table.verticalHeader().setVisible(False)

        # Set column widths
        header = self.filter_header
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Category
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)           # Key
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)           # Default Value
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)           # Current Value
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # ★
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)           # Custom Value
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Status

        # Set custom delegate for editing Custom Value column (col 5)
        self.table.setItemDelegateForColumn(5, SelectAllDelegate())
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.cellClicked.connect(self.on_cell_clicked)

        layout.addWidget(self.table)

        # Status label
        self.table_status_label = QLabel("No data loaded")
        layout.addWidget(self.table_status_label)

        return widget

    def create_about_tab(self) -> QWidget:
        """Create about tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # About content in a scrollable text browser
        about_browser = QTextBrowser()
        about_browser.setOpenExternalLinks(True)

        try:
            # Load ABOUT.md file
            about_path = get_resource_path("ABOUT.md")
            with open(about_path, 'r', encoding='utf-8') as f:
                about_content = f.read()

            # Add version to the first heading
            about_content = about_content.replace(
                "# SC Localization Editor",
                f"# SC Localization Editor v{get_version()}"
            )

            # Convert markdown to HTML
            about_html = self.markdown_to_html(about_content)
            about_browser.setHtml(about_html)
        except Exception as e:
            logger.error(f"Error loading ABOUT.md: {e}", exc_info=True)
            about_browser.setHtml(f"<h1>About</h1><p>Unable to load about information.</p><p style='color: gray;'>{str(e)}</p>")

        layout.addWidget(about_browser)
        return widget

    @pyqtSlot()
    def load_files(self):
        """Load base global.ini."""
        base_path, _ = QFileDialog.getOpenFileName(
            self, "Select global.ini", "", "INI Files (*.ini);;All Files (*)"
        )
        if not base_path:
            return

        self._start_loading(base_path)

    def _start_loading(self, base_path: str):
        """Start file loading in background worker thread."""
        self._set_toolbar_enabled(False)

        # Show progress dialog
        self._progress_dialog = QProgressDialog(
            "Loading file...", None, 0, 0, self
        )
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.setAutoClose(False)
        self._progress_dialog.show()

        # Create and start worker
        overrides_path = AppSettings.get_user_ini_path()
        overrides_arg = str(overrides_path) if overrides_path.exists() else None

        contracts_ini = Path(__file__).parent.parent.parent / "data" / "contracts.ini"
        contracts_arg = str(contracts_ini) if contracts_ini.exists() else None

        self._loader_worker = FileLoaderWorker(base_path, overrides_arg, contracts_arg)
        self._loader_worker.finished.connect(self._on_files_loaded)
        self._loader_worker.error.connect(self._on_load_error)
        self._loader_worker.start()

    @pyqtSlot(list)
    def _on_files_loaded(self, entries: list):
        """Handle successful file loading."""
        if self._progress_dialog:
            self._progress_dialog.close()

        self.entries = entries
        self.update_category_combo()
        self.populate_table()
        self.apply_filters()

        # Show override count in status bar
        modified_count = sum(1 for e in self.entries if e.status in ("Modified", "New"))
        msg = f"Loaded {len(self.entries)} entries"
        if modified_count:
            msg += f" | {modified_count} overrides active"
        self.statusBar().showMessage(msg)

        logger.info(f"Loaded {len(self.entries)} entries")
        self._set_toolbar_enabled(True)

    @pyqtSlot(str)
    def _on_load_error(self, message: str):
        """Handle file loading error."""
        if self._progress_dialog:
            self._progress_dialog.close()

        QMessageBox.critical(self, "Error", f"Failed to load file: {message}")
        logger.error(f"Error loading file: {message}")

        self._set_toolbar_enabled(True)

    def _set_toolbar_enabled(self, enabled: bool):
        """Toggle toolbar button enabled states."""
        self.load_btn.setEnabled(enabled)
        self.apply_btn.setEnabled(enabled)
        self.restore_backup_btn.setEnabled(enabled)
        self.clear_loc_btn.setEnabled(enabled)

    @timed
    def load_default_values(self):
        """Load default values from cached base source in AppData."""
        from src.parser.ini_parser import parse_ini_file

        cache_file = AppSettings.get_cache_dir() / "base.ini"

        if cache_file.exists():
            try:
                # Parse cached base.ini and convert to dict for lookup
                parsed = parse_ini_file(cache_file)
                self.default_values = {key: value for key, value in parsed.items()}
                logger.info(f"Loaded {len(self.default_values)} default values from cache")
            except Exception as e:
                logger.warning(f"Failed to load default values from {cache_file}: {e}")
        else:
            logger.debug(f"Cache file not found: {cache_file}. Default values will be empty until sources are downloaded.")

    def auto_load_default_files(self):
        """Automatically load and merge configured sources, or fall back to legacy behavior."""
        try:
            # Try new system first: load configured sources from settings
            sources_dict, hierarchy, enhancements_key_categories = load_sources_from_settings()

            if sources_dict and hierarchy:
                logger.info(f"Loading configured sources: {list(sources_dict.keys())} with hierarchy {hierarchy}")
                self.statusBar().showMessage("Loading and merging configured sources...")

                try:
                    # Load synchronously in main thread to avoid threading issues
                    logger.info("Synchronously loading sources...")
                    entries = load_source_files(sources_dict, hierarchy, enhancements_key_categories=enhancements_key_categories)
                    logger.info(f"Loaded {len(entries)} entries")
                    self.entries = entries
                    self.update_category_combo()
                    self.populate_table()
                    self.apply_filters()

                    # Update status bar with entry counts and per-source status
                    self._update_status_bar()
                    return
                except Exception as e:
                    logger.exception(f"Error loading sources synchronously: {e}")
                    QMessageBox.critical(self, "Error", f"Failed to load sources: {e}")
                    return

        except Exception as e:
            logger.warning(f"Failed to load from configured sources, falling back to legacy: {e}")

        # Fall back to legacy single-file loading
        global_path = None

        # First, try to load from base_global_path setting (legacy)
        legacy_path = AppSettings.get_base_global_path()
        if legacy_path and Path(legacy_path).exists():
            global_path = legacy_path
            logger.info(f"Loading legacy base_global_path: {legacy_path}")
        else:
            # Try to load from game directory if configured
            game_path = AppSettings.get_game_install_path()
            if game_path:
                logger.info(f"Game path from registry/settings: {game_path}")
                # Handle both full SC path and LIVE directory path
                game_path_obj = Path(game_path)
                if game_path_obj.name == "LIVE":
                    # Path is already the LIVE directory
                    game_global = game_path_obj / "data/Localization/english/global.ini"
                else:
                    # Path is the SC root directory
                    game_global = game_path_obj / "LIVE/data/Localization/english/global.ini"

                logger.info(f"Looking for global.ini at: {game_global}")
                if game_global.exists():
                    global_path = game_global
                    logger.info(f"Found global.ini in game directory: {game_global}")

            # Fall back to data folder if game directory doesn't have it
            if not global_path:
                data_dir = Path(__file__).parent.parent.parent / "data"
                data_base = data_dir / "base.ini"
                logger.info(f"Falling back to data folder: {data_base}")
                if data_base.exists():
                    global_path = data_base
                    logger.info(f"Loading default base file from data folder")

        # Bootstrap overrides from diff if missing
        if global_path:
            overrides_path = AppSettings.get_user_ini_path()
            if not overrides_path.exists():
                data_dir = Path(__file__).parent.parent.parent / "data"
                data_base = data_dir / "base.ini"
                if data_base.exists():
                    try:
                        from src.utils.user_ini_manager import generate_user_ini_from_diff
                        count = generate_user_ini_from_diff(data_base, global_path, overrides_path)
                        if count:
                            logger.info(f"Bootstrapped {count} overrides from diff")
                    except Exception as e:
                        logger.warning(f"Failed to bootstrap overrides: {e}")

            # Load the file in background
            self._start_loading(str(global_path))
        else:
            logger.warning("No base file found in configured sources, game directory, or data folder")
            self.statusBar().showMessage("No base file found - please configure sources in Config tab or load a file manually")

    @pyqtSlot()
    @timed
    def apply_to_game(self):
        """Apply merged sources + user edits to game installation and backup existing file."""
        if not self.entries:
            QMessageBox.warning(self, "Warning", "Please load a file first")
            return

        game_path = AppSettings.get_game_install_path()
        if not game_path:
            QMessageBox.warning(self, "Warning", "Please configure game install path in Config tab")
            return

        game_path_obj = Path(game_path)
        if game_path_obj.name == "LIVE":
            target_path = game_path_obj / "data/Localization/english/global.ini"
        else:
            target_path = game_path_obj / "LIVE/data/Localization/english/global.ini"

        try:
            import shutil
            from datetime import datetime

            target_path.parent.mkdir(parents=True, exist_ok=True)

            backup_path = None  # Tracks the backup created this apply (used for restore on validation failure)

            # Backup existing file if it exists
            if target_path.exists():
                backup_dir = AppSettings.get_backups_dir()

                # Find all existing backups
                backup_files = sorted(
                    backup_dir.glob("global.ini.bak_*"),
                    key=lambda f: f.stat().st_mtime
                )

                # Delete oldest backup if we already have 5
                if len(backup_files) >= 5:
                    oldest_backup = backup_files[0]
                    oldest_backup.unlink()
                    logger.info(f"Deleted oldest backup: {oldest_backup.name}")

                # Create new backup
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = backup_dir / f"global.ini.bak_{timestamp}"
                shutil.copy2(target_path, backup_path)
                logger.info(f"Backed up existing file to {backup_path}")

            # Build final merged dict by re-merging all sources with user edits
            # This ensures Apply uses latest source versions and user edits
            sources_dict, hierarchy, _mrk = load_sources_from_settings()

            # Warn if any active sources are missing (only check sources actually in AVAILABLE_SOURCES)
            active_source_names = set(AppSettings.AVAILABLE_SOURCES)
            active_source_names.add("enhancements")
            missing_sources = [
                name for name in hierarchy
                if name in active_source_names
                and name != AppSettings.SOURCE_USER and name != "enhancements"
                and name not in sources_dict
                and AppSettings.is_source_enabled(name)
            ]
            if missing_sources:
                names = ", ".join(missing_sources)
                reply = QMessageBox.warning(
                    self, "Missing Sources",
                    f"The following enabled sources could not be loaded:\n\n  {names}\n\n"
                    "Their customizations will NOT be included in the applied file.\n\n"
                    "Apply anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            # Build user overrides dict from entries with custom_value
            user_overrides_dict = {
                entry.key: entry.custom_value
                for entry in self.entries
                if entry.custom_value
            }

            # Merge all sources in hierarchy order, with user edits on top
            merged_dict = merge_sources_by_hierarchy(sources_dict, hierarchy, user_overrides_dict)

            # Get a base file to use for structure preservation
            # Use the first source file from hierarchy
            base_file = None
            for source_name in hierarchy:
                source_path = AppSettings.get_source_path(source_name)
                # Check if it's a URL (remote source) - use cache
                if source_path and (source_path.startswith('http://') or source_path.startswith('https://')):
                    # Map source name to cache file
                    cache_mapping = {
                        AppSettings.SOURCE_GLOBAL:      "base.ini",
                    }
                    if source_name in cache_mapping:
                        cache_file = AppSettings.get_cache_dir() / cache_mapping[source_name]
                        if cache_file.exists():
                            base_file = cache_file
                            break
                # Otherwise check if it's a local file that exists
                elif source_path and Path(source_path).exists():
                    base_file = source_path
                    break

            if not base_file:
                raise FileNotFoundError("No base file found. Configure sources and download them first.")

            # Use merger to preserve original file structure
            from src.merger.ini_merger import merge_ini_files
            merge_ini_files(str(base_file), merged_dict, str(target_path))

            # Validate written file against stock base
            validation_msg = self._validate_applied_file(target_path)

            if validation_msg:
                # Delete the bad file and restore the backup we just made
                try:
                    target_path.unlink()
                    logger.warning(f"Deleted invalid output file: {target_path}")
                except Exception as del_err:
                    logger.error(f"Could not delete invalid file: {del_err}")

                if backup_path and backup_path.exists():
                    try:
                        shutil.copy2(backup_path, target_path)
                        logger.info(f"Restored backup: {backup_path.name}")
                        restore_note = f"\n\nThe previous file has been restored from backup:\n{backup_path.name}"
                    except Exception as restore_err:
                        logger.error(f"Could not restore backup: {restore_err}")
                        restore_note = "\n\nCould not restore backup — game will use vanilla text."
                else:
                    restore_note = "\n\nNo backup was available to restore."

                self.statusBar().showMessage("Apply failed — validation error")
                QMessageBox.critical(
                    self, "Validation Failed",
                    f"The written file failed validation and has been deleted.\n\n"
                    f"{validation_msg}"
                    f"{restore_note}"
                )
                return

            # Save user overrides to AppData
            from src.utils.user_ini_manager import save_user_ini
            user_count = save_user_ini(self.entries, AppSettings.get_user_ini_path())

            # Count enhancement entries
            enhancement_count = sum(
                1 for entry in self.entries
                if entry.source_file == "enhancements"
            )

            # Ensure user.cfg has language setting
            from src.utils.user_cfg import ensure_user_cfg_language
            ensure_user_cfg_language()

            logger.info(f"Applied to game: {target_path}")
            self.statusBar().showMessage(
                f"Applied to game | {user_count} user edits | {enhancement_count} enhancements"
            )
            QMessageBox.information(
                self, "Success",
                f"Applied to {target_path}\n\n"
                f"  User edits: {user_count}\n"
                f"  SCLE enhancements: {enhancement_count}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply to game: {e}")
            logger.error(f"Error applying to game: {e}")

    def _validate_applied_file(self, written_path: Path) -> str:
        """Validate the written global.ini against the stock base.ini.

        Checks that every key in base.ini is present in the written file.
        Values are allowed to differ. Extra keys (from components/contracts/
        commodities sources) are expected and not treated as errors.

        Args:
            written_path: Path to the global.ini just written to the game directory.

        Returns:
            Empty string if validation passed, or a human-readable warning message
            describing any missing keys.
        """
        from src.parser.ini_parser import parse_ini_file

        stock_path = AppSettings.get_cache_dir() / "base.ini"
        if not stock_path.exists():
            logger.warning("Validation skipped: base.ini not found in cache")
            return ""

        try:
            stock_keys = set(parse_ini_file(stock_path).keys())
            written_keys = set(parse_ini_file(written_path).keys())
        except Exception as e:
            logger.warning(f"Validation error reading files: {e}")
            return ""

        missing = stock_keys - written_keys
        extra = written_keys - stock_keys

        logger.info(
            f"Validation: stock={len(stock_keys)} keys, "
            f"written={len(written_keys)} keys, "
            f"missing={len(missing)}, extra={len(extra)}"
        )

        if not missing and not extra:
            return ""

        lines = []

        if missing:
            sample = sorted(missing)[:20]
            lines += [f"{len(missing)} key(s) from base.ini are missing from the written file:"]
            lines += [f"  {k}" for k in sample]
            if len(missing) > 20:
                lines.append(f"  ... and {len(missing) - 20} more")

        if extra:
            if lines:
                lines.append("")
            sample = sorted(extra)[:20]
            lines += [f"{len(extra)} unexpected key(s) in written file (not in base.ini):"]
            lines += [f"  {k}" for k in sample]
            if len(extra) > 20:
                lines.append(f"  ... and {len(extra) - 20} more")

        lines += ["", "The previous file has been restored. Check your source configuration."]
        return "\n".join(lines)

    @pyqtSlot()
    def clear_localization(self):
        """Delete global.ini from the game's localization directory, reverting to vanilla text."""
        game_path = AppSettings.get_game_install_path()
        if not game_path:
            QMessageBox.warning(self, "Warning", "Please configure game install path in Config tab")
            return

        game_path_obj = Path(game_path)
        if game_path_obj.name == "LIVE":
            loc_dir = game_path_obj / "data/Localization/english"
        else:
            loc_dir = game_path_obj / "LIVE/data/Localization/english"
        global_ini = loc_dir / "global.ini"

        if not global_ini.exists():
            QMessageBox.information(self, "Nothing to Clear",
                "No custom global.ini found in the game's localization directory.\n"
                "The game is already using vanilla text.")
            return

        reply = QMessageBox.question(
            self, "Clear Localization",
            f"This will delete the custom global.ini from:\n{loc_dir}\n\n"
            "The game will revert to its default (vanilla) localization text.\n\n"
            "Your overrides are preserved in the app and can be re-applied at any time.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            global_ini.unlink()
            logger.info(f"Deleted {global_ini}")
            self.statusBar().showMessage("Localization cleared — game reverted to vanilla text")
            QMessageBox.information(self, "Done",
                "Custom localization removed.\n"
                "The game will now use its default text.\n\n"
                "To re-apply your overrides and stat descriptions, click Apply to Game.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete global.ini: {e}")
            logger.error(f"Error clearing localization: {e}")

    @pyqtSlot()
    def clear_cache(self):
        """Delete cached source files from the cache directory. Optionally clear DataForge cache."""
        import shutil
        from PyQt6.QtWidgets import QApplication
        cache_dir = AppSettings.get_cache_dir()
        cached_files = list(cache_dir.glob("*.ini")) + list(cache_dir.glob("*.txt"))

        # Also check for dataforge directory
        dataforge_dir = cache_dir / "dataforge"
        has_dataforge = dataforge_dir.exists()

        if not cached_files and not has_dataforge:
            QMessageBox.information(self, "Cache Empty", "The cache directory is already empty.")
            return

        # First dialog: clear regular cache files
        file_list = "\n".join(f"  {f.name}" for f in sorted(cached_files))
        msg = f"This will delete the following cached files:\n\n{file_list}\n\n"
        msg += "base.ini will need to be re-extracted from Data.p4k before strings can be loaded."

        reply = QMessageBox.question(
            self, "Clear Cache", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        deleted, failed = [], []

        # Show progress dialog while deleting files
        progress = AnimatedProgressDialog("Clearing cache files...", parent=self, title="Clearing Cache")

        # Delete cache files
        for f in cached_files:
            try:
                progress.setLabelText(f"Deleting {f.name}...")
                QApplication.processEvents()  # Keep dialog responsive
                f.unlink()
                deleted.append(f.name)
            except Exception as e:
                failed.append(f"{f.name}: {e}")
                logger.error(f"Failed to delete cache file {f}: {e}")

        # Second dialog: ask about DataForge cache (only if it exists)
        clear_dataforge = False
        if has_dataforge:
            progress.close()  # Close progress dialog while asking user
            reply = QMessageBox.question(
                self, "Clear DataForge Cache?",
                "Also clear the DataForge entity cache?\n\n"
                "⚠️  Warning: Recreating the DataForge cache takes 5–10 minutes on first run.\n\n"
                "The DataForge cache contains extracted entity data used for generating\n"
                "ship and weapon stats. You can keep this cache and only clear the INI files\n"
                "if you just want to refresh the localization strings.\n\n"
                "Clear DataForge cache?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                clear_dataforge = True
                # Show progress dialog again for DataForge deletion
                progress = AnimatedProgressDialog("Clearing DataForge cache...", parent=self, title="Clearing Cache")

        # Delete dataforge directory if user agreed
        if clear_dataforge:
            try:
                progress.setLabelText("Deleting DataForge directory...")
                QApplication.processEvents()

                # Use a more robust deletion that handles locked files
                import stat
                import time

                def handle_remove_readonly(func, path, exc):
                    """Error handler for rmtree to handle read-only files."""
                    if not os.access(path, os.W_OK):
                        os.chmod(path, stat.S_IWUSR | stat.S_IRUSR)
                        func(path)
                    else:
                        raise

                # Try to remove with readonly handler, retry a few times if locked
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        shutil.rmtree(dataforge_dir, onerror=handle_remove_readonly)
                        deleted.append("dataforge/")
                        logger.info("Deleted DataForge cache directory")
                        break
                    except Exception as retry_err:
                        if attempt < max_retries - 1:
                            # Wait a bit before retrying (might be OneDrive sync or antivirus scan)
                            logger.warning(f"DataForge deletion attempt {attempt + 1} failed, retrying: {retry_err}")
                            time.sleep(1)
                        else:
                            # Final attempt failed
                            failed.append(f"dataforge/: {retry_err}")
                            logger.error(f"Failed to delete DataForge cache after {max_retries} attempts: {retry_err}")
            except Exception as e:
                failed.append(f"dataforge/: {e}")
                logger.error(f"Failed to delete DataForge cache: {e}")

        progress.close()

        self.config_tab._refresh_p4k_status()
        self.entries = []
        self.populate_table()

        msg = f"Deleted {len(deleted)} item(s) from cache."
        if failed:
            msg += f"\n\nFailed to delete:\n" + "\n".join(failed)
        QMessageBox.information(self, "Cache Cleared", msg)

        # Re-sync all remote sources so they're available for the next Apply.
        # The sync completion will also prompt for p4k extraction if base.ini is missing.
        if self._startup_sync_worker is None:
            self._start_startup_sync()

    @pyqtSlot()
    def open_localization_dir(self):
        """Open the game's localization directory in Windows Explorer."""
        game_path = AppSettings.get_game_install_path()
        if not game_path:
            QMessageBox.warning(self, "Warning", "Please configure game install path in Config tab")
            return

        game_path_obj = Path(game_path)
        if game_path_obj.name.upper() == "LIVE":
            loc_dir = game_path_obj / "data/Localization/english"
        else:
            loc_dir = game_path_obj / "LIVE/data/Localization/english"

        if not loc_dir.exists():
            QMessageBox.warning(
                self, "Directory Not Found",
                f"Localization directory not found:\n{loc_dir}\n\n"
                "Check your game install path in the Config tab."
            )
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(loc_dir)))

    @pyqtSlot()
    @timed
    def perform_merge_and_reload(self):
        """Perform merge of configured sources and reload table.

        Called when user saves configuration in Config tab. Loads all configured
        sources, merges them in hierarchy order, and updates the table display.
        """
        try:
            # Load all configured sources
            sources_dict, hierarchy, enhancements_key_categories = load_sources_from_settings()

            if not sources_dict or not hierarchy:
                QMessageBox.warning(self, "Warning", "No sources configured. Please configure data sources in Config tab.")
                return

            self.statusBar().showMessage("Merging sources...")

            try:
                # Load synchronously in main thread
                logger.info("Merging configured sources...")
                entries = load_source_files(sources_dict, hierarchy, enhancements_key_categories=enhancements_key_categories)
                logger.info(f"Merge complete: {len(entries)} entries")
                self.entries = entries
                self.update_category_combo()
                self.populate_table()
                self.apply_filters()

                # Update status bar with entry counts and per-source status
                self._update_status_bar()
            except Exception as e:
                logger.exception(f"Error during merge: {e}")
                QMessageBox.critical(self, "Error", f"Failed to merge sources: {e}")
                self.statusBar().showMessage("Merge failed")

        except Exception as e:
            logger.exception(f"Error in perform_merge_and_reload: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load sources: {e}")

    # ── INI Import ────────────────────────────────────────────────────────────

    @pyqtSlot()
    def _handle_import_ini(self):
        """Handle Import INI button: get source, validate, resolve conflicts, merge."""
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
            QPushButton, QLabel, QDialogButtonBox, QFileDialog
        )
        from src.parser.ini_parser import parse_ini_file
        from src.utils.user_ini_manager import save_user_ini_dict
        import tempfile
        import urllib.request

        # Step 1: Get source path/URL from user
        source = self._get_import_source()
        if not source:
            return

        temp_file = None
        try:
            # Step 2: Resolve to local file
            if source.startswith('http://') or source.startswith('https://'):
                # Auto-convert GitHub web URLs to raw URLs
                if source.startswith('https://github.com/'):
                    source = source.replace('https://github.com/', 'https://raw.githubusercontent.com/')
                    source = source.replace('/blob/', '/')

                self.statusBar().showMessage("Downloading INI file...")
                try:
                    temp_file = tempfile.NamedTemporaryFile(suffix='.ini', delete=False)
                    temp_file.close()
                    urllib.request.urlretrieve(source, temp_file.name)
                    resolved_path = temp_file.name
                except Exception as e:
                    QMessageBox.critical(self, "Download Error", f"Failed to download:\n{source}\n\n{e}")
                    return
            else:
                resolved_path = source
                if not Path(resolved_path).exists():
                    QMessageBox.warning(self, "File Not Found", f"File does not exist:\n{resolved_path}")
                    return

            # Step 3: Parse imported file
            imported = parse_ini_file(resolved_path)
            if not imported:
                QMessageBox.warning(self, "Empty File", "The imported file contains no valid key=value entries.")
                return

            # Step 4: Validate against base.ini keys
            if not self.default_values:
                QMessageBox.warning(self, "No Base Data",
                    "Base INI not loaded yet. Extract from Data.p4k first.")
                return

            valid_keys = {k: v for k, v in imported.items() if k in self.default_values}
            excluded_count = len(imported) - len(valid_keys)

            if not valid_keys:
                QMessageBox.warning(self, "No Valid Keys",
                    f"None of the {len(imported)} imported keys exist in base.ini.\n"
                    f"All keys were excluded.")
                return

            # Step 5: Load current user.ini
            user_ini_path = AppSettings.get_user_ini_path()
            current_user = parse_ini_file(user_ini_path) if user_ini_path.exists() else {}

            # Step 6: Categorize keys
            auto_add = {}
            conflicts = {}
            for key, imported_value in valid_keys.items():
                current_value = current_user.get(key)
                if current_value is None:
                    auto_add[key] = imported_value
                elif current_value != imported_value:
                    conflicts[key] = (current_value, imported_value)
                # else: identical, skip

            # Step 7: Handle cases
            if not auto_add and not conflicts:
                QMessageBox.information(self, "Nothing to Import",
                    "All imported keys already exist in user.ini with the same values.")
                return

            if not conflicts:
                reply = QMessageBox.question(self, "Import INI",
                    f"{len(auto_add)} new keys will be added to user.ini.\n"
                    f"{excluded_count} keys excluded (not in base.ini).\n\n"
                    "Proceed?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply != QMessageBox.StandardButton.Yes:
                    return
                resolutions = {}
            else:
                from src.gui.import_dialog import ImportConflictDialog
                dialog = ImportConflictDialog(conflicts, len(auto_add), excluded_count, self)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return
                resolutions = dialog.get_resolutions()

            # Step 8: Merge
            final = dict(current_user)
            final.update(auto_add)
            final.update(resolutions)

            # Step 9: Save
            save_user_ini_dict(final, user_ini_path)

            # Step 10: Reload
            self._show_loading_progress("Reloading with imported data...")

            # Step 11: Summary
            QMessageBox.information(self, "Import Complete",
                f"Import successful.\n\n"
                f"  Added: {len(auto_add)} keys\n"
                f"  Conflicts resolved: {len(resolutions)} keys\n"
                f"  Excluded: {excluded_count} keys")

        except Exception as e:
            logger.exception(f"Import failed: {e}")
            QMessageBox.critical(self, "Import Error", f"Failed to import INI file:\n{e}")
        finally:
            if temp_file:
                try:
                    Path(temp_file.name).unlink(missing_ok=True)
                except Exception:
                    pass

    def _get_import_source(self) -> str | None:
        """Show dialog to get a file path or URL for import."""
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
            QPushButton, QLabel, QDialogButtonBox, QFileDialog
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Import INI File")
        dialog.setMinimumWidth(500)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Enter a local file path or URL:"))

        input_row = QHBoxLayout()
        line_edit = QLineEdit()
        line_edit.setPlaceholderText(r"C:\path\to\file.ini or https://example.com/file.ini")
        input_row.addWidget(line_edit)

        browse_btn = QPushButton("Browse...")
        def browse():
            path, _ = QFileDialog.getOpenFileName(
                dialog, "Select INI File", "", "INI Files (*.ini);;All Files (*)")
            if path:
                line_edit.setText(path)
        browse_btn.clicked.connect(browse)
        input_row.addWidget(browse_btn)
        layout.addLayout(input_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted and line_edit.text().strip():
            return line_edit.text().strip()
        return None

    @pyqtSlot()
    def restore_backup(self):
        """Restore a backup file as the current global.ini."""
        game_path = AppSettings.get_game_install_path()
        if not game_path:
            QMessageBox.warning(self, "Warning", "Please configure game install path in Config tab")
            return

        backup_dir = AppSettings.get_backups_dir()

        # Open file dialog to select backup
        backup_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select Backup File to Restore",
            str(backup_dir),
            "Backup Files (*.bak_*);;INI Files (*.ini);;All Files (*)"
        )

        if not backup_file:
            return

        try:
            import shutil

            game_path_obj = Path(game_path)
            if game_path_obj.name == "LIVE":
                target_path = game_path_obj / "data/Localization/english/global.ini"
            else:
                target_path = game_path_obj / "LIVE/data/Localization/english/global.ini"
            backup_file_path = Path(backup_file)

            # Restore the backup
            shutil.copy2(str(backup_file_path), str(target_path))

            # Reload the file with overrides
            overrides_path = AppSettings.get_user_ini_path()
            overrides_arg = str(overrides_path) if overrides_path.exists() else None
            self.entries = load_source_files(str(target_path), overrides_arg)
            self.update_category_combo()
            self.populate_table()
            self.apply_filters()

            # Update status bar with entry counts and per-source status
            self._update_status_bar()

            logger.info(f"Restored backup from {backup_file} to {target_path}")
            QMessageBox.information(self, "Success", f"Backup restored from:\n{backup_file_path.name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to restore backup: {e}")
            logger.error(f"Error restoring backup: {e}")

    @pyqtSlot()
    def show_help(self):
        """Show help dialog with usage instructions."""
        from PyQt6.QtWidgets import QDialog

        help_markdown = """# SC Localization Editor - Quick Start Guide

## First Time Setup
On launch, the app automatically downloads the latest base localization file and mission contracts from GitHub. Your customizations from previous sessions are loaded automatically.

## 1. Load Game File
Click **Load Base File** to load strings from your configured sources. The installer pre-configures this path automatically.

## 2. Edit Localization Strings
- Double-click any **Custom Value** cell to edit text
- The **Default Value** shows the original text from the base source file
- The **Current Value** shows the merged value from all configured sources
- The **Custom Value** column holds your personal edits
- Changes are highlighted with a **Modified** status (green)
- Your edits are saved automatically and persist between sessions

## 3. Categories
Filter strings by category:
- **Ships** - Spaceship names (vehicle_Name*)
- **Ship Items** - Component names (shields, power, cooling, etc.)
- **Missions** - Mission briefings and contract text
- **Other** - Everything else, including stats descriptions

## 4. Search & Filter
- Use the search box to find strings by key or text content
- Filter by **Category** to focus on one type
- Filter by **Status** (Modified, Unmodified, New)
- Check **Hide Unmodified** to see only your changes
- Click any **column header** to sort by that column

## 5. Ship Favorites
- Click the **star (★)** column on any Ship row to mark it as a favorite
- Favorited ships get a prefix character prepended to their name, sorting them to the top of the in-game ship list
- Configure the prefix character in the Config tab

## 6. Apply Changes to Game
Click **Apply to Game** to write your edits to the game installation. A timestamped backup is saved automatically to your Documents folder before applying.

## 7. Restore a Backup
Click **Restore Backup** to revert to a previous version. The app keeps up to 5 automatic backups in Documents\\SC Localization Editor\\backups\\.

## 8. Clear Localization
Click **Clear Localization** to delete the custom global.ini from the game directory, reverting the game to its default (vanilla) text. Your saved overrides are not affected and can be re-applied at any time.

## 9. After Game Updates
When Star Citizen updates, your edits are preserved in your Documents folder. Simply reload the new base file and your customizations automatically re-apply.

## Enhancements
When enhancement files are present (generated by generate_enhancements_ini.py), numerical stats such as SCM speed, DPS, shield HP, cargo capacity, and weapon loadouts are automatically appended to ship and component descriptions. Toggle this on/off in the Config tab.

## Config Tab
- Configure data source paths (Global, Contracts, Components, Ships)
- Set your Star Citizen installation path
- Drag sources to reorder the merge hierarchy
- Enable or disable Enhancements

## Status Bar
Shows the sync status for each configured source. "✓" means up to date.
"""

        # Create a custom dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Help - SC Localization Editor")
        dialog.setGeometry(100, 100, 700, 600)

        # Create layout
        dialog_layout = QVBoxLayout(dialog)

        # Create text browser
        help_browser = QTextBrowser()
        help_browser.setOpenExternalLinks(True)
        help_html = self.markdown_to_html(help_markdown)
        help_browser.setHtml(help_html)

        dialog_layout.addWidget(help_browser)

        # Add close button
        close_btn = QPushButton("Close")
        close_btn.setMaximumWidth(100)
        close_btn.clicked.connect(dialog.accept)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        dialog_layout.addLayout(button_layout)

        dialog.exec()

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier:
            # Ctrl+Shift+C: Copy filtered rows
            self.copy_filtered_to_clipboard()
        else:
            super().keyPressEvent(event)

    def _update_status_bar(self):
        """Compose sync status from all configured sources plus entry counts and game version.

        Shows per-source sync status in hierarchy order, then entry count, override count, and game version.
        Example: "Global: 4.7.0-LIVE ✓  |  Contracts: ✓  |  Ships: ✓  |  82,934 entries | 5 overrides | SC v4.7.176"
        """
        # Build status message from all configured sources in hierarchy order
        hierarchy = AppSettings.get_merge_hierarchy()
        parts = []

        for source_name in hierarchy:
            if source_name in self._source_status:
                parts.append(self._source_status[source_name])

        # Add entry and override counts if data is loaded
        if self.entries:
            modified_count = sum(1 for e in self.entries if e.status in ("Modified", "New"))
            entry_info = f"{len(self.entries):,} entries"
            if modified_count:
                entry_info += f" | {modified_count} overrides"
            parts.append(entry_info)

        # Add game version if available
        game_version = AppSettings.get_game_version()
        if game_version:
            # Extract major version (e.g., "4.7.176" from "4.7.176.58286")
            version_parts = game_version.split(".")
            short_version = ".".join(version_parts[:3]) if len(version_parts) >= 3 else game_version
            parts.append(f"SC v{short_version}")

        self.statusBar().showMessage("  |  ".join(parts) if parts else "Ready")

    def _set_source_status(self, source_name: str, status: str) -> None:
        """Set sync status for a specific source and update status bar.

        Args:
            source_name: Name of the source (e.g., "global", "contracts")
            status: Status string to display (e.g., "Global: 4.7.0-LIVE ✓")
        """
        self._source_status[source_name] = status
        self._update_status_bar()

    def _start_startup_sync(self):
        """Start async sync of all enabled remote sources, then load files when done.

        If no remote sources need syncing, skip directly to loading.
        """
        # Check if any sources actually need syncing (remote URL + auto-update enabled)
        has_remote_sync = any(
            AppSettings.is_source_enabled(name)
            and AppSettings.get_source_auto_update(name)
            and AppSettings.get_source_path(name).startswith("http")
            for name in AppSettings.AVAILABLE_SOURCES
        )

        if not has_remote_sync:
            # Nothing to sync — go straight to loading
            self._on_startup_sync_finished()
            return

        self.statusBar().showMessage("Starting up — syncing sources...")
        self._startup_progress = AnimatedProgressDialog(
            "Syncing sources...", parent=self, title="Starting Up"
        )
        self._startup_sync_worker = StartupSyncWorker()
        self._startup_sync_worker.source_starting.connect(self._on_startup_source_starting)
        self._startup_sync_worker.source_synced.connect(self._on_startup_source_synced)
        self._startup_sync_worker.source_error.connect(self._on_startup_source_error)
        self._startup_sync_worker.finished.connect(self._on_startup_sync_finished)
        self._startup_sync_worker.start()

    @pyqtSlot(str)
    def _on_startup_source_starting(self, source_name: str):
        self.statusBar().showMessage(f"Syncing {source_name}...")
        if self._startup_progress is not None:
            self._startup_progress.setLabelText(f"Syncing {source_name}...")

    @pyqtSlot(str, bool)
    def _on_startup_source_synced(self, source_name: str, updated: bool):
        action = "updated" if updated else "up to date"
        logger.info(f"Startup sync: {source_name} {action}")
        label = "updated ↑" if updated else "✓"
        self._set_source_status(source_name, f"{source_name.title()}: {label}")

    @pyqtSlot(str, str)
    def _on_startup_source_error(self, source_name: str, message: str):
        logger.warning(f"Startup sync error ({source_name}): {message}")
        self._set_source_status(source_name, f"{source_name.title()}: ⚠ (offline?)")

    @pyqtSlot()
    def _on_startup_sync_finished(self):
        """Sync complete — clean up worker, check p4k freshness, then load sources."""
        if self._startup_sync_worker:
            self._startup_sync_worker.quit()
            self._startup_sync_worker.wait()
            self._startup_sync_worker = None

        # Close the startup progress dialog before any modal prompts (P4K, enhancements)
        if self._startup_progress is not None:
            self._startup_progress.close()
            self._startup_progress = None

        # Prompt user to extract from p4k if base.ini is missing or outdated
        p4k_extraction_started = self._check_p4k_freshness()

        # If P4K extraction was started, don't load files yet.
        # The P4K extraction finished handler will do the loading.
        if p4k_extraction_started:
            return

        # Don't check enhancements during startup - defer until after file loading completes
        # to avoid concurrent I/O contention between file loader and enhancements generator
        self._check_enhancements_after_loading = True

        # Show progress dialog during file loading
        self._show_loading_progress()

    def _check_p4k_freshness(self) -> bool:
        """Prompt to extract from Data.p4k if base.ini is missing or outdated.

        Returns:
            True if P4K extraction was started (caller should defer file loading).
            False if no extraction is needed or user declined.
        """
        unp4k_exe = AppSettings.get_unp4k_exe_path()
        p4k_path = AppSettings.get_p4k_path()
        base_ini = AppSettings.get_cache_dir() / 'base.ini'

        if not unp4k_exe.exists() or not p4k_path.exists():
            return False  # silently skip — unp4k not bundled yet or game path not set

        base_missing = not base_ini.exists()
        p4k_newer = (not base_missing) and (p4k_path.stat().st_mtime > base_ini.stat().st_mtime)

        if not base_missing and not p4k_newer:
            return False  # cache is present and up to date

        if base_missing:
            msg = (
                "No base localization file found in cache.\n\n"
                "Extract global.ini from Data.p4k now?\n"
                "(Required to load and display localization strings.)"
            )
        else:
            msg = (
                "Data.p4k is newer than your cached base.ini.\n\n"
                "Extract global.ini from Data.p4k now?\n"
                "(This gives you stock strings matching your exact installed game version.)"
            )

        reply = QMessageBox.question(
            self, "Extract from Data.p4k", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._run_p4k_extraction()
            return True
        return False

    def _check_enhancements_freshness(self):
        """If enabled enhancement files are missing, prompt to generate them.

        Shows a category selection dialog on startup. If called again after P4K
        extraction and we already prompted, runs generation with saved selections.
        """
        cache_dir = AppSettings.get_cache_dir()
        if not (cache_dir / 'base.ini').exists():
            return
        if self._enhancements_worker is not None or self._forge_worker is not None:
            return

        # Only check enabled categories
        enabled = AppSettings.get_enabled_enhancement_categories()
        missing = [key for key in enabled
                   if not (cache_dir / AppSettings.ENHANCEMENTS_FILES[key]).exists()]
        if not missing:
            return

        p4k_path = AppSettings.get_p4k_path()
        if not p4k_path.exists():
            return

        # If we already prompted and user chose to generate, just run with saved selections
        if self._enhancements_prompted_on_startup:
            self._run_enhancements_pipeline()
            return

        # Show category selection dialog
        self._enhancements_prompted_on_startup = True
        selected = self._show_enhancement_category_dialog(missing)
        if selected:
            self._run_enhancements_pipeline()

    def _show_enhancement_category_dialog(self, missing_keys: list[str]) -> set[str] | None:
        """Show a dialog letting the user select which enhancement categories to generate.

        Args:
            missing_keys: List of category keys that are currently missing.

        Returns:
            Set of selected category keys, or None if user clicked Skip.
        """
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QLabel, QCheckBox,
            QPushButton, QHBoxLayout
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Generate Enhancements")
        dialog.setMinimumWidth(400)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel(
            f"{len(missing_keys)} enhancement files are missing.\n"
            "Select which categories to generate.\n"
            "You can change this later in the Enhancements tab."
        ))

        layout.addSpacing(8)

        # Determine which checkbox categories have missing files
        missing_file_keys = set(missing_keys)
        missing_checkbox_keys = set()
        for checkbox_key, file_keys in AppSettings.ENHANCEMENT_CATEGORY_FILES.items():
            if any(fk in missing_file_keys for fk in file_keys):
                missing_checkbox_keys.add(checkbox_key)

        checkboxes: dict[str, QCheckBox] = {}
        for key, label in AppSettings.ENHANCEMENT_LABELS.items():
            cb = QCheckBox(label)
            if key in missing_checkbox_keys:
                cb.setChecked(True)
                cb.setText(f"{label}  (missing)")
            else:
                cb.setChecked(False)
            checkboxes[key] = cb
            layout.addWidget(cb)

        layout.addSpacing(8)

        info = QLabel(
            "DataForge data will be extracted automatically if not already cached.\n"
            "First run takes ~5-10 minutes."
        )
        info.setStyleSheet("font-size: 11px; color: #666;")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addSpacing(8)

        button_row = QHBoxLayout()
        generate_btn = QPushButton("Generate")
        generate_btn.setDefault(True)
        skip_btn = QPushButton("Skip")

        generate_btn.clicked.connect(dialog.accept)
        skip_btn.clicked.connect(dialog.reject)

        button_row.addStretch()
        button_row.addWidget(skip_btn)
        button_row.addWidget(generate_btn)
        layout.addLayout(button_row)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Only save state for categories that were missing — don't touch
            # the persisted state of categories that already have their files
            for key, cb in checkboxes.items():
                if key in missing_checkbox_keys:
                    AppSettings.set_enhancement_category_enabled(key, cb.isChecked())
            # Refresh enhancements tab checkboxes to match
            self.enhancements_tab.revert_category_checkboxes()
            self.enhancements_tab.refresh_enhancements_status()
            return AppSettings.get_enabled_enhancement_categories()

        return None

    def _show_loading_progress(self, message: str = "Loading localization strings...") -> None:
        """Show an animated progress dialog while loading files in a worker thread.

        Uses FileLoaderWorker to load files asynchronously so the progress dialog
        can animate properly. Shares the same progress dialog implementation as P4K extraction.

        Args:
            message: Status message to display in the progress dialog
        """
        # Guard against overlapping loads — clean up any prior worker first
        if self._loader_worker is not None:
            logger.warning("Previous FileLoaderWorker still exists — cleaning up before starting new load")
            try:
                self._loader_worker.finished.disconnect(self._on_loading_finished)
                self._loader_worker.error.disconnect(self._on_loading_error)
            except (TypeError, RuntimeError):
                pass  # signals already disconnected
            if self._loader_worker.isRunning():
                self._loader_worker.quit()
                self._loader_worker.wait(5000)  # 5s timeout to avoid deadlock
            self._loader_worker = None
        if self._loading_progress is not None:
            self._loading_progress.close()
            self._loading_progress = None

        # Load sources in background worker thread
        self._loader_worker = FileLoaderWorker()

        # Create reusable animated progress dialog
        self._loading_progress = AnimatedProgressDialog(message, parent=self, title="Loading")

        # Connect worker signals to progress dialog label updates
        self._loader_worker.finished.connect(self._on_loading_finished)
        self._loader_worker.error.connect(self._on_loading_error)
        self._loader_worker.start()

    @pyqtSlot(list)
    @timed
    def _on_loading_finished(self, entries: list):
        """Handle file loading completion."""
        from PyQt6.QtWidgets import QApplication

        # Close modal progress dialog and clean up worker FIRST so the modal
        # event loop exits before heavy synchronous UI work.
        if self._loading_progress is not None:
            self._loading_progress.close()
            self._loading_progress = None
        if self._loader_worker is not None:
            self._loader_worker.quit()
            self._loader_worker.wait()
            self._loader_worker = None

        # Show loading message in the table status area and force a repaint
        # so the user sees feedback before the main thread blocks
        self.table_status_label.setText("Populating table — please wait…")
        self.statusBar().showMessage("Populating table…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        # Force repaint so the messages are visible before blocking
        self.table_status_label.repaint()
        self.statusBar().repaint()

        try:
            self.load_default_values()
            self.entries = entries
            self.update_category_combo()
            self.populate_table()

            # Update status bar with entry counts and per-source status
            self._update_status_bar()
        finally:
            QApplication.restoreOverrideCursor()

        # If enhancements check was deferred during startup, do it now (after file loading completes)
        # This avoids concurrent I/O contention between file loader and enhancements generator
        if self._check_enhancements_after_loading:
            self._check_enhancements_after_loading = False
            self._check_enhancements_freshness()

    @pyqtSlot(str)
    def _on_loading_error(self, error_msg: str):
        """Handle file loading error."""
        self._loading_progress.close()
        self._loading_progress = None
        QMessageBox.critical(self, "Error", f"Failed to load sources: {error_msg}")
        if self._loader_worker:
            self._loader_worker.quit()
            self._loader_worker.wait()
            self._loader_worker = None

    def _run_enhancements_pipeline(self):
        """Entry point for the enhancements button: extract DataForge if needed, then generate enhancements."""
        if self._enhancements_worker is not None or self._forge_worker is not None:
            return  # already running

        from src.utils.pak_extractor import dataforge_cache_is_fresh
        forge_dir = AppSettings.get_dataforge_cache_dir()
        p4k_path  = AppSettings.get_p4k_path()

        if dataforge_cache_is_fresh(p4k_path, forge_dir):
            self._run_enhancements_generation()
        else:
            self._run_dataforge_extraction()

    def _run_enhancements_generation(self, categories: set[str] | None = None):
        """Launch EnhancementsGeneratorWorker in the background with animated progress dialog."""
        if self._enhancements_worker is not None:
            return  # already running

        # Use enabled categories from settings if none specified
        if categories is None:
            categories = AppSettings.get_enabled_enhancement_categories()

        self._enhancements_worker = EnhancementsGeneratorWorker(categories=categories)
        self.enhancements_tab.set_operation_running("Generating enhancements…")
        self.statusBar().showMessage("Generating enhancements in background…")

        # Show animated progress dialog
        self._enhancements_progress_dialog = AnimatedProgressDialog(
            "Generating enhanced localizations from DataForge…\n\nThis may take a few minutes on the first run.",
            parent=self,
            title="Generating Enhancements",
        )

        self._enhancements_worker.progress.connect(self.enhancements_tab.set_operation_progress)
        self._enhancements_worker.progress.connect(self.statusBar().showMessage)
        self._enhancements_worker.progress.connect(self._enhancements_progress_dialog.setLabelText)
        self._enhancements_worker.error.connect(self._on_enhancements_generation_error)
        self._enhancements_worker.finished.connect(self._on_enhancements_generation_finished)
        self._enhancements_worker.start()

    def _on_enhancements_generation_error(self, message: str):
        logger.error(f"Enhancements generation error: {message}")
        # Close progress dialog on error
        if self._enhancements_progress_dialog is not None:
            self._enhancements_progress_dialog.close()
            self._enhancements_progress_dialog = None

    def _on_enhancements_generation_finished(self, success: bool):
        # Close progress dialog
        if self._enhancements_progress_dialog is not None:
            self._enhancements_progress_dialog.close()
            self._enhancements_progress_dialog = None

        self._enhancements_worker.quit()
        self._enhancements_worker.wait()
        self._enhancements_worker = None
        self.enhancements_tab.set_operation_idle()
        self.enhancements_tab.refresh_enhancements_status()

        if success:
            self.statusBar().showMessage("Enhancements generated — reloading entries…")
            self._show_loading_progress("Reloading strings with updated enhancements…")
        else:
            self.statusBar().showMessage("Enhancement generation failed — check the Log tab for details")

    def _run_dataforge_extraction(self):
        """Launch DataForgeExtractWorker in the background (non-blocking)."""
        if self._forge_worker is not None:
            return

        p4k_path    = AppSettings.get_p4k_path()
        unp4k_exe   = AppSettings.get_unp4k_exe_path()
        unforge_exe = AppSettings.get_unforge_exe_path()
        forge_dir   = AppSettings.get_dataforge_cache_dir()

        self._forge_worker = DataForgeExtractWorker(p4k_path, unp4k_exe, unforge_exe, forge_dir)
        self.enhancements_tab.set_operation_running("Extracting DataForge from Data.p4k…")
        self.statusBar().showMessage("Extracting DataForge in background — this takes several minutes…")

        self._forge_worker.progress.connect(self.enhancements_tab.set_operation_progress)
        self._forge_worker.progress.connect(self.statusBar().showMessage)
        self._forge_worker.error.connect(self._on_dataforge_extract_error)
        self._forge_worker.finished.connect(self._on_dataforge_extract_finished)
        self._forge_worker.start()

    def _on_dataforge_extract_error(self, message: str):
        logger.error(f"DataForge extraction error: {message}")

    def _on_dataforge_extract_finished(self, success: bool):
        self._forge_worker.quit()
        self._forge_worker.wait()
        self._forge_worker = None
        self.enhancements_tab.refresh_forge_status()

        if success:
            self.statusBar().showMessage("DataForge extracted — generating enhancements…")
            self._run_enhancements_generation()
        else:
            self.enhancements_tab.set_operation_idle()
            self.statusBar().showMessage("DataForge extraction failed — check the Log tab for details")

    def _run_p4k_extraction(self):
        """Launch P4kExtractWorker with a progress dialog; reload sources on success."""
        p4k_path = AppSettings.get_p4k_path()
        output_path = AppSettings.get_cache_dir() / 'base.ini'
        unp4k_exe = AppSettings.get_unp4k_exe_path()

        self._p4k_worker = P4kExtractWorker(p4k_path, output_path, unp4k_exe)
        self._p4k_progress = AnimatedProgressDialog(
            "Extracting global.ini from Data.p4k...",
            parent=self,
            title="P4K Extraction"
        )

        self._p4k_worker.progress.connect(self._p4k_progress.setLabelText)
        self._p4k_worker.error.connect(lambda err: QMessageBox.warning(self, "Extraction Error", err))
        self._p4k_worker.finished.connect(self._on_p4k_extract_finished)
        self._p4k_worker.start()

    def _on_p4k_extract_finished(self, success: bool):
        """Handle P4K extraction completion."""
        self._p4k_progress.close()
        self._p4k_worker.quit()
        self._p4k_worker.wait()
        self._p4k_worker = None

        if success:
            # Lock Global source to the local cache path with auto-update off,
            # so future startups don't overwrite the extracted file from a remote URL.
            local_path = str(AppSettings.get_cache_dir() / 'base.ini')
            AppSettings.set_source_path(AppSettings.SOURCE_GLOBAL, local_path)
            AppSettings.set_source_auto_update(AppSettings.SOURCE_GLOBAL, False)
            # Refresh the config tab P4K status
            self.config_tab._refresh_p4k_status()

            # Defer enhancements check until after file loading completes (avoid I/O contention)
            self._check_enhancements_after_loading = True

            # Show progress dialog while reloading with extracted data
            self._show_loading_progress("Reloading with extracted base.ini...")

    def closeEvent(self, event):
        """Save state and overrides before closing."""
        # Auto-save overrides if there are unsaved edits
        if self.entries and not (self._loader_worker and self._loader_worker.isRunning()):
            try:
                from src.utils.user_ini_manager import save_user_ini
                save_user_ini(self.entries, AppSettings.get_user_ini_path())
            except Exception as e:
                logger.error(f"Failed to auto-save overrides on exit: {e}")

        # Detach log handler before widgets are destroyed
        self.log_tab.remove_handler()

        # Clean up workers
        if self._loader_worker:
            self._loader_worker.quit()
            self._loader_worker.wait()

        # Save window state
        AppSettings.set_window_geometry(self.saveGeometry())
        AppSettings.set_window_state(self.saveState())

        event.accept()

    @timed
    def _filtered_entry_indices(self) -> list[tuple[int, "StringEntry"]]:
        """Return (index, entry) pairs for entries passing the current filters."""
        column_filters = self.filter_header.get_filter_texts()
        category_filter = self.category_combo.currentText()
        status_filter = self.status_combo.currentText()
        hide_unmodified = self.hide_unmodified_check.isChecked()
        favorites_only = self.favorites_only_check.isChecked()
        prefix = AppSettings.get_favorite_prefix()
        active_col_filters = [(i, t) for i, t in enumerate(column_filters) if t]

        result = []
        for idx, entry in enumerate(self.entries):
            show = True

            if hide_unmodified and entry.status == "Unmodified":
                show = False
            elif category_filter != "All" and entry.category != category_filter:
                show = False
            elif status_filter != "All" and entry.status != status_filter:
                show = False
            elif favorites_only and not entry.custom_value.startswith(prefix):
                show = False
            elif active_col_filters:
                row_values = [
                    entry.category.lower(),
                    entry.key.lower(),
                    self.default_values.get(entry.key, "").lower(),
                    entry.original_value.lower(),
                    "★" if entry.custom_value.startswith(prefix) else "",
                    entry.custom_value.lower(),
                    entry.status.lower(),
                ]
                for col, filter_text in active_col_filters:
                    if filter_text not in row_values[col]:
                        show = False
                        break

            if show:
                result.append((idx, entry))
        return result

    @timed
    def populate_table(self):
        """Populate table with only the entries that pass current filters."""
        filtered = self._filtered_entry_indices()

        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)  # Clear existing items first to avoid destroy+create overhead
        self.table.setRowCount(len(filtered))
        self.table.blockSignals(True)

        # Cache values that would otherwise hit the Windows Registry per-row
        prefix = AppSettings.get_favorite_prefix()
        fav_bg = QColor("#3a3000")
        num_cols = self.table.columnCount()

        for row, (entry_idx, entry) in enumerate(filtered):
            # Col 0: Category — stores entry index as UserRole so row→entry
            # lookups stay correct after the user sorts a column.
            cat_item = self._create_item(entry.category)
            cat_item.setData(Qt.ItemDataRole.UserRole, entry_idx)
            self.table.setItem(row, 0, cat_item)

            # Col 1: Key — uses GroupSortItem for grouped sort support
            key_item = GroupSortItem(entry.key)
            key_item.setToolTip(entry.key)
            key_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 1, key_item)

            # Col 2: Default value from reference base file (for comparison)
            default_value = self.default_values.get(entry.key, "")
            self.table.setItem(row, 2, self._create_item(default_value))

            # Col 3: Current value (original_value from loaded file)
            self.table.setItem(row, 3, self._create_item(entry.original_value))

            # Col 4: Favorite star (Ships only — uses cached prefix)
            if entry.category != "Ships":
                star_item = QTableWidgetItem("")
                star_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            else:
                is_fav = entry.custom_value.startswith(prefix)
                star_item = QTableWidgetItem("★" if is_fav else "☆")
                star_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                star_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                if is_fav:
                    star_item.setForeground(QColor("#FFD700"))
                    star_item.setToolTip("Favorite — click to remove")
                else:
                    star_item.setForeground(QColor("#666666"))
                    star_item.setToolTip("Click to mark as favorite")
            self.table.setItem(row, 4, star_item)

            # Col 5: Custom value (editable)
            self.table.setItem(row, 5, self._create_item(entry.custom_value, editable=True))

            # Col 6: Status
            status_item = self._create_item(entry.status)
            status_item.setForeground(self._status_color(entry.status))
            self.table.setItem(row, 6, status_item)

            # Apply favorite row background (uses cached prefix, no registry read)
            if entry.category == "Ships" and entry.custom_value.startswith(prefix):
                for col in range(num_cols):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(fav_bg)

        self.table.blockSignals(False)
        self.table.setSortingEnabled(True)

        # Apply grouped sort if enabled
        if self.grouped_sort_check.isChecked():
            self.table.sortItems(1, Qt.SortOrder.AscendingOrder)

        self.table.setUpdatesEnabled(True)
        self.table_status_label.setText(f"Showing {len(filtered)} of {len(self.entries)} strings")

    def _create_item(self, text: str, editable: bool = False):
        """Create a read-only table item (editable only if explicitly requested)."""
        item = QTableWidgetItem(text)
        item.setToolTip(text)
        if not editable:
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        return item

    def _create_star_item(self, entry: "StringEntry") -> QTableWidgetItem:
        """Create the favorite star cell for a row. Only Ships get a clickable star."""
        if entry.category != "Ships":
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            return item

        prefix = AppSettings.get_favorite_prefix()
        is_fav = entry.custom_value.startswith(prefix)
        item = QTableWidgetItem("★" if is_fav else "☆")
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        if is_fav:
            item.setForeground(QColor("#FFD700"))  # gold
            item.setToolTip("Favorite — click to remove")
        else:
            item.setForeground(QColor("#666666"))
            item.setToolTip("Click to mark as favorite")
        return item

    def _apply_row_style(self, row: int, entry: "StringEntry"):
        """Apply background color to a row based on favorite state."""
        prefix = AppSettings.get_favorite_prefix()
        is_favorite = entry.category == "Ships" and entry.custom_value.startswith(prefix)
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                if is_favorite:
                    item.setBackground(QColor("#3a3000"))
                else:
                    # Clear to system default — avoids black cells in light mode
                    item.setData(Qt.ItemDataRole.BackgroundRole, None)

    def _status_color(self, status: str) -> QColor:
        """Get color for status."""
        colors = {
            "Modified": QColor("#4CAF50"),
            "Unmodified": QColor("#999999"),
            "New": QColor("#FF9800"),
        }
        return colors.get(status, QColor("black"))

    @timed
    def update_category_combo(self):
        """Update category combo with unique categories from entries.

        Always includes standard categories (Ships, Ship Items, Missions, Other)
        plus any custom categories found in the entries.
        """
        # Get unique categories from entries
        entry_categories = set(e.category for e in self.entries)

        # Always include standard categories, even if no entries exist for them yet
        standard_categories = {"Ships", "Ship Items", "Missions", "Commodities", "Other"}
        categories = sorted(standard_categories | entry_categories)

        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("All")
        self.category_combo.addItems(categories)
        self.category_combo.blockSignals(False)

    def _entry_index_for_row(self, table_row: int) -> int:
        """Return the self.entries index for a given table row.

        After sorting, visual row order differs from self.entries order.
        The entry index is stored as UserRole data on col 0 at populate time.
        """
        item = self.table.item(table_row, 0)
        if item is not None:
            idx = item.data(Qt.ItemDataRole.UserRole)
            if idx is not None:
                return idx
        return table_row  # fallback (pre-sort or empty table)

    @pyqtSlot()
    def apply_filters(self):
        """Apply filters by rebuilding the table with only matching entries."""
        if not self.entries:
            return
        self.populate_table()

    @pyqtSlot()
    def _on_grouped_sort_changed(self):
        """Toggle grouped sort mode and sort by Key column."""
        global _grouped_sort_enabled
        _grouped_sort_enabled = self.grouped_sort_check.isChecked()
        from PyQt6.QtWidgets import QApplication
        progress = AnimatedProgressDialog("Sorting...", parent=self, title="Grouped Sort")
        QApplication.processEvents()
        try:
            self.table.sortItems(1, Qt.SortOrder.AscendingOrder)
        finally:
            progress.close()

    @pyqtSlot()
    def clear_filters(self):
        """Clear all filters."""
        self.category_combo.blockSignals(True)
        self.status_combo.blockSignals(True)
        self.hide_unmodified_check.blockSignals(True)
        self.favorites_only_check.blockSignals(True)

        self.filter_header.clear_all()
        self.category_combo.setCurrentIndex(0)
        self.status_combo.setCurrentIndex(0)
        self.hide_unmodified_check.setChecked(False)
        self.favorites_only_check.setChecked(False)

        self.category_combo.blockSignals(False)
        self.status_combo.blockSignals(False)
        self.hide_unmodified_check.blockSignals(False)
        self.favorites_only_check.blockSignals(False)

        self.apply_filters()

    @pyqtSlot()
    def copy_filtered_to_clipboard(self):
        """Copy all visible filtered rows to clipboard (tab-separated)."""
        lines = []
        # Add header
        lines.append("Key\tOriginal Value\tCurrent Value\tCustom Value\tStatus")

        # Add visible rows
        for table_row in range(self.table.rowCount()):
            if self.table.isRowHidden(table_row):
                continue

            entry_idx = self._entry_index_for_row(table_row)
            if entry_idx >= len(self.entries):
                continue

            entry = self.entries[entry_idx]
            # Tab-separated: Key, Original Value, Current Value, Custom Value, Status
            line = f"{entry.key}\t{entry.original_value}\t{entry.original_value}\t{entry.custom_value}\t{entry.status}"
            lines.append(line)

        if len(lines) <= 1:
            QMessageBox.information(self, "Copy Filtered", "No rows to copy.")
            return

        text_to_copy = "\n".join(lines)
        try:
            import pyperclip
            pyperclip.copy(text_to_copy)
            QMessageBox.information(self, "Copy Filtered", f"Copied {len(lines) - 1} rows to clipboard.")
        except Exception as e:
            QMessageBox.warning(self, "Copy Error", f"Failed to copy to clipboard: {e}")

    @pyqtSlot(QTableWidgetItem)
    def on_item_changed(self, item: QTableWidgetItem):
        """Handle table item edit."""
        table_row = item.row()
        col = item.column()

        if col == 5:  # Custom Value column
            entry_idx = self._entry_index_for_row(table_row)
            if entry_idx >= len(self.entries):
                return
            entry = self.entries[entry_idx]
            entry.custom_value = item.text()
            entry.status = "Modified" if item.text() != entry.original_value else "Unmodified"
            status_item = self._create_item(entry.status)
            status_item.setForeground(self._status_color(entry.status))
            self.table.setItem(table_row, 6, status_item)
            self.table.setItem(table_row, 4, self._create_star_item(entry))
            self._apply_row_style(table_row, entry)

    def show_context_menu(self, position):
        """Show right-click context menu."""
        item = self.table.itemAt(position)
        if not item:
            return

        table_row = item.row()
        entry_idx = self._entry_index_for_row(table_row)
        if entry_idx >= len(self.entries):
            return

        entry = self.entries[entry_idx]
        prefix = AppSettings.get_favorite_prefix()
        is_favorite = entry.custom_value.startswith(prefix)

        menu = QMenu(self)
        menu.addAction("Copy Cell", lambda: self.copy_cell(item))
        menu.addAction("Copy Key", lambda: self.copy_key(table_row))
        menu.addSeparator()
        menu.addAction("Edit", lambda: self.edit_cell(table_row))
        menu.addAction("Reset to Original", lambda: self.reset_to_original(table_row))
        menu.addSeparator()
        menu.addAction("Copy All Filtered", lambda: self.copy_filtered_to_clipboard())

        if entry.category == "Ships":
            menu.addSeparator()
            if is_favorite:
                menu.addAction("★ Remove from Favorites", lambda: self.toggle_favorite(table_row))
            else:
                menu.addAction("★ Add to Favorites", lambda: self.toggle_favorite(table_row))

        menu.exec(self.table.mapToGlobal(position))

    def edit_cell(self, row: int):
        """Edit custom value cell."""
        self.table.editItem(self.table.item(row, 5))

    def reset_to_original(self, table_row: int):
        """Reset custom value to original."""
        entry_idx = self._entry_index_for_row(table_row)
        if entry_idx < len(self.entries):
            self.entries[entry_idx].custom_value = ""
            self.entries[entry_idx].status = "Unmodified"
            self.populate_table()

    def copy_cell(self, item: QTableWidgetItem):
        """Copy the clicked cell's text to clipboard."""
        import pyperclip
        try:
            pyperclip.copy(item.text())
        except Exception:
            pass

    def copy_key(self, table_row: int):
        """Copy key to clipboard."""
        entry_idx = self._entry_index_for_row(table_row)
        if entry_idx < len(self.entries):
            import pyperclip
            try:
                pyperclip.copy(self.entries[entry_idx].key)
                self.statusBar().showMessage(f"Copied: {self.entries[entry_idx].key}")
            except ImportError:
                self.statusBar().showMessage("pyperclip not installed")

    @pyqtSlot(int, int)
    def on_cell_clicked(self, row: int, col: int):
        """Handle cell clicks — col 4 (★) toggles favorite for Ship rows."""
        if col == 4:
            entry_idx = self._entry_index_for_row(row)
            if entry_idx < len(self.entries) and self.entries[entry_idx].category == "Ships":
                self.toggle_favorite(row)

    def toggle_favorite(self, table_row: int):
        """Add or remove the sort prefix from a ship's custom value."""
        entry_idx = self._entry_index_for_row(table_row)
        if entry_idx >= len(self.entries):
            return

        entry = self.entries[entry_idx]
        prefix = AppSettings.get_favorite_prefix()

        if entry.custom_value.startswith(prefix):
            # Remove favorite: strip prefix
            new_value = entry.custom_value[len(prefix):]
            entry.custom_value = new_value if new_value != entry.original_value else ""
        else:
            # Add favorite: prepend prefix to current display value
            base = entry.custom_value if entry.custom_value else entry.original_value
            entry.custom_value = prefix + base

        entry.status = "Modified" if entry.custom_value else "Unmodified"

        self.table.blockSignals(True)
        self.table.setItem(table_row, 4, self._create_star_item(entry))
        self.table.setItem(table_row, 5, self._create_item(entry.custom_value))
        status_item = self._create_item(entry.status)
        status_item.setForeground(self._status_color(entry.status))
        self.table.setItem(table_row, 6, status_item)
        self._apply_row_style(table_row, entry)
        self.table.blockSignals(False)

    def restore_window_state(self):
        """Restore window geometry and state."""
        geometry = AppSettings.get_window_geometry()
        state = AppSettings.get_window_state()

        if geometry:
            self.restoreGeometry(geometry)
        if state:
            self.restoreState(state)

    def create_anchor_id(self, text: str) -> str:
        """Convert text to anchor ID (used in markdown links)."""
        return text.lower().replace(" ", "-").replace(".", "").replace("&", "and")

    def markdown_to_html(self, markdown_text: str) -> str:
        """Convert markdown to HTML with theme-aware styling."""
        # Get theme-aware colors from the application palette
        palette = self.palette()
        text_color = palette.color(palette.ColorRole.Text).name()
        base_color = palette.color(palette.ColorRole.Base).name()
        link_color = palette.color(palette.ColorRole.Link).name()

        # Build HTML with styling
        html = "<html><head><style>"
        html += f"body {{ font-family: Segoe UI, Arial, sans-serif; line-height: 1.8; padding: 20px; font-size: 15px; color: {text_color}; background-color: {base_color}; }}"
        html += f"h1 {{ color: {link_color}; border-bottom: 3px solid {link_color}; padding-bottom: 10px; font-size: 32px; font-weight: bold; margin-top: 20px; }}"
        html += f"h2 {{ color: {link_color}; border-bottom: 2px solid {link_color}; padding-bottom: 5px; margin-top: 30px; font-size: 24px; font-weight: bold; }}"
        html += f"h3 {{ color: {link_color}; margin-top: 20px; font-size: 20px; font-weight: bold; }}"
        html += f"p {{ font-size: 15px; margin: 10px 0; color: {text_color}; }}"
        html += f"li {{ font-size: 15px; margin: 5px 0; color: {text_color}; }}"
        html += f"a {{ color: {link_color}; text-decoration: underline; font-weight: 500; }}"
        html += f"a:hover {{ text-decoration: underline; opacity: 0.8; cursor: pointer; }}"
        html += f"code {{ background-color: rgba(0,0,0,0.05); padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; font-size: 14px; }}"
        html += f"pre {{ background-color: rgba(0,0,0,0.05); padding: 10px; border-radius: 5px; overflow-x: auto; font-size: 14px; }}"
        html += f"ul {{ margin-left: 20px; font-size: 15px; }}"
        html += f"ol {{ margin-left: 20px; font-size: 15px; }}"
        html += f"strong {{ font-weight: bold; }}"
        html += f"blockquote {{ border-left: 4px solid {link_color}; padding-left: 15px; font-style: italic; font-size: 15px; }}"
        html += "</style></head><body>"

        lines = markdown_text.split('\n')
        in_code_block = False
        in_list = False
        list_type = None
        prev_blank = False

        for line in lines:
            # Code blocks
            if line.strip().startswith('```'):
                if in_code_block:
                    html += "</pre>"
                    in_code_block = False
                else:
                    html += "<pre><code>"
                    in_code_block = True
                continue

            if in_code_block:
                html += line + "\n"
                continue

            # Headers
            if line.startswith('# '):
                if in_list:
                    html += f"</{list_type}>"
                    in_list = False
                header_text = line[2:].strip()
                anchor_id = self.create_anchor_id(header_text)
                html += f"<h1 id='{anchor_id}'>{header_text}</h1>"
                prev_blank = False
            elif line.startswith('## '):
                if in_list:
                    html += f"</{list_type}>"
                    in_list = False
                header_text = line[3:].strip()
                anchor_id = self.create_anchor_id(header_text)
                html += f"<h2 id='{anchor_id}'>{header_text}</h2>"
                prev_blank = False
            elif line.startswith('### '):
                if in_list:
                    html += f"</{list_type}>"
                    in_list = False
                header_text = line[4:].strip()
                anchor_id = self.create_anchor_id(header_text)
                html += f"<h3 id='{anchor_id}'>{header_text}</h3>"
                prev_blank = False
            # Lists
            elif line.strip().startswith('- ') or line.strip().startswith('* '):
                if not in_list or list_type != 'ul':
                    if in_list:
                        html += f"</{list_type}>"
                    html += "<ul>"
                    in_list = True
                    list_type = 'ul'
                list_text = line.strip()[2:].strip()
                # Convert markdown links in list items
                list_text = self._convert_markdown_links(list_text)
                html += f"<li>{list_text}</li>"
                prev_blank = False
            elif line.strip() and line[0].isdigit() and '. ' in line:
                if not in_list or list_type != 'ol':
                    if in_list:
                        html += f"</{list_type}>"
                    html += "<ol>"
                    in_list = True
                    list_type = 'ol'
                list_text = line.strip()
                # Remove number and period
                list_text = list_text[list_text.index('. ') + 2:].strip()
                # Convert markdown links in list items
                list_text = self._convert_markdown_links(list_text)
                html += f"<li>{list_text}</li>"
                prev_blank = False
            # Empty lines (skip consecutive blank lines)
            elif not line.strip():
                if in_list:
                    html += f"</{list_type}>"
                    in_list = False
                    prev_blank = True
                elif not prev_blank:
                    # Only add one blank line, not consecutive ones
                    prev_blank = True
                continue
            # Paragraphs
            else:
                if in_list:
                    html += f"</{list_type}>"
                    in_list = False
                # Convert markdown links and bold
                line = self._convert_markdown_links(line)
                line = line.replace("**", "<strong>").replace("__", "<strong>")
                html += f"<p>{line}</p>"
                prev_blank = False

        # Close any open tags
        if in_list:
            html += f"</{list_type}>"
        if in_code_block:
            html += "</pre>"

        html += "</body></html>"
        return html

    def _convert_markdown_links(self, text: str) -> str:
        """Convert markdown links [text](url) to HTML links."""
        import re
        # Match [text](url) pattern
        pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        replacement = r'<a href="\2">\1</a>'
        return re.sub(pattern, replacement, text)
