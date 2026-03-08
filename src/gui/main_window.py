"""Main window for SC Localization Editor."""
import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QCheckBox, QTableWidget,
    QTableWidgetItem, QFileDialog, QMessageBox, QTabWidget,
    QHeaderView, QStatusBar, QFrame, QStyledItemDelegate,
    QAbstractItemView, QMenu
)
from PyQt6.QtGui import QColor, QFont

from src.models.string_model import StringEntry
from src.parser.ini_parser import load_source_files
from src.utils.settings import AppSettings
from src.utils.version import get_version
from src.gui.config_tab import ConfigTab

logger = logging.getLogger(__name__)


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

        # Data
        self.entries: list[StringEntry] = []
        self.filtered_row_indices: list[int] = []
        self.default_values: dict = {}  # Store default values from data/global.ini

        # Debounce timer for filtering
        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self.apply_filters)
        self.filter_timer.setInterval(300)  # 300ms delay

        # Build UI
        self.setup_ui()
        self.restore_window_state()
        self.load_default_values()
        self.auto_load_default_files()

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
        tabs.addTab(ConfigTab(), "Config")
        tabs.addTab(self.create_about_tab(), "About")
        main_layout.addWidget(tabs)

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

        layout.addLayout(button_layout)

        # Filter row
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search key or value...")
        self.search_input.setMaximumWidth(200)
        self.search_input.textChanged.connect(self.on_search_changed)
        filter_layout.addWidget(self.search_input)

        filter_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.setMaximumWidth(150)
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

        self.clear_filters_btn = QPushButton("Clear Filters")
        self.clear_filters_btn.setMaximumWidth(100)
        self.clear_filters_btn.clicked.connect(self.clear_filters)
        filter_layout.addWidget(self.clear_filters_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        return layout

    def create_strings_tab(self) -> QWidget:
        """Create strings table tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Category", "Key", "Default Value", "Current Value", "Custom Value", "Status"
        ])

        # Table settings
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        # Hide row numbers
        self.table.verticalHeader().setVisible(False)

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        # Set custom delegate for editing
        self.table.setItemDelegateForColumn(4, SelectAllDelegate())
        self.table.itemChanged.connect(self.on_item_changed)

        layout.addWidget(self.table)

        # Status label
        self.table_status_label = QLabel("No data loaded")
        layout.addWidget(self.table_status_label)

        return widget

    def create_about_tab(self) -> QWidget:
        """Create about tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        about_text = QLabel(
            f"<h2>SC Localization Editor</h2>"
            f"<p>Version: {get_version()}</p>"
            f"<p>A PyQt6 GUI for editing Star Citizen localization strings.</p>"
            f"<p>Load base global.ini and vehicles.ini, customize strings, and merge them back.</p>"
        )
        about_text.setWordWrap(True)
        layout.addWidget(about_text)

        layout.addStretch()
        return widget

    @pyqtSlot()
    def load_files(self):
        """Load base global.ini and optional target_strings.ini."""
        # File dialogs
        base_path, _ = QFileDialog.getOpenFileName(
            self, "Select global.ini", "", "INI Files (*.ini);;All Files (*)"
        )
        if not base_path:
            return

        custom_path, _ = QFileDialog.getOpenFileName(
            self, "Select target_strings.ini (optional)", "", "INI Files (*.ini);;All Files (*)"
        )

        try:
            self.entries = load_source_files(base_path, custom_path or None)
            self.update_category_combo()
            self.populate_table()
            self.apply_filters()
            logger.info(f"Loaded {len(self.entries)} entries")
            self.statusBar().showMessage(f"Loaded {len(self.entries)} entries")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load files: {e}")
            logger.error(f"Error loading files: {e}")

    def load_default_values(self):
        """Load default values from data/global.ini for reference."""
        data_dir = Path(__file__).parent.parent.parent / "data"
        default_global = data_dir / "global.ini"

        if default_global.exists():
            try:
                self.default_values = load_source_files(str(default_global), None)
                # Convert to dictionary for quick lookup
                self.default_values = {entry.key: entry.original_value for entry in self.default_values}
                logger.info(f"Loaded {len(self.default_values)} default values")
            except Exception as e:
                logger.warning(f"Failed to load default values: {e}")

    def auto_load_default_files(self):
        """Automatically load global.ini from game directory or data folder."""
        global_path = None

        # First, try to load from game directory if configured
        game_path = AppSettings.get_game_install_path()
        if game_path:
            game_global = Path(game_path) / "LIVE/data/Localization/english/global.ini"
            if game_global.exists():
                global_path = game_global
                logger.info(f"Found global.ini in game directory: {game_global}")

        # Fall back to data folder if game directory doesn't have it
        if not global_path:
            data_dir = Path(__file__).parent.parent.parent / "data"
            data_global = data_dir / "global.ini"
            if data_global.exists():
                global_path = data_global
                logger.info(f"Loading default global.ini from data folder: {data_dir}")

        # Load the file if found
        if global_path:
            try:
                self.entries = load_source_files(str(global_path), None)
                self.update_category_combo()
                self.populate_table()
                self.apply_filters()

                # Determine which file was loaded
                if "LIVE/data/Localization" in str(global_path):
                    source = "Game Directory"
                else:
                    source = "Data Folder"

                message = f"Loaded {len(self.entries)} entries from {source}"
                logger.info(f"Auto-loaded {len(self.entries)} entries from {global_path}")
                self.statusBar().showMessage(message)
            except Exception as e:
                logger.warning(f"Failed to auto-load files: {e}")
                self.statusBar().showMessage("Failed to auto-load files")

    @pyqtSlot()
    def apply_to_game(self):
        """Apply custom strings to game installation and backup existing file."""
        if not self.entries:
            QMessageBox.warning(self, "Warning", "Please load a file first")
            return

        game_path = AppSettings.get_game_install_path()
        if not game_path:
            QMessageBox.warning(self, "Warning", "Please configure game install path in Config tab")
            return

        target_path = Path(game_path) / "LIVE/data/Localization/english/global.ini"

        try:
            import shutil
            from datetime import datetime

            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Backup existing file if it exists
            if target_path.exists():
                backup_dir = target_path.parent

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

            # Write custom strings to game directory
            with open(target_path, 'w', encoding='utf-8') as f:
                for entry in self.entries:
                    # Use custom value if available, otherwise use original
                    value = entry.custom_value if entry.custom_value else entry.original_value
                    f.write(f"{entry.key}={value}\n")

            logger.info(f"Applied to game: {target_path}")
            self.statusBar().showMessage(f"Applied to {target_path}")
            QMessageBox.information(self, "Success", f"Applied to {target_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply to game: {e}")
            logger.error(f"Error applying to game: {e}")

    @pyqtSlot()
    def restore_backup(self):
        """Restore a backup file as the current global.ini."""
        game_path = AppSettings.get_game_install_path()
        if not game_path:
            QMessageBox.warning(self, "Warning", "Please configure game install path in Config tab")
            return

        backup_dir = Path(game_path) / "LIVE/data/Localization/english"

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

            target_path = Path(game_path) / "LIVE/data/Localization/english/global.ini"
            backup_file_path = Path(backup_file)

            # Restore the backup
            shutil.copy2(str(backup_file_path), str(target_path))

            # Reload the file
            self.entries = load_source_files(str(target_path), None)
            self.update_category_combo()
            self.populate_table()
            self.apply_filters()

            logger.info(f"Restored backup from {backup_file} to {target_path}")
            self.statusBar().showMessage(f"Restored backup from {backup_file_path.name}")
            QMessageBox.information(self, "Success", f"Backup restored from:\n{backup_file_path.name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to restore backup: {e}")
            logger.error(f"Error restoring backup: {e}")

    def populate_table(self):
        """Populate table with entries."""
        self.table.setRowCount(len(self.entries))
        self.table.blockSignals(True)

        for row, entry in enumerate(self.entries):
            self.table.setItem(row, 0, self._create_item(entry.category))
            self.table.setItem(row, 1, self._create_item(entry.key))

            # Default value from data/global.ini
            default_value = self.default_values.get(entry.key, "")
            self.table.setItem(row, 2, self._create_item(default_value))

            # Current value (original_value from loaded file)
            self.table.setItem(row, 3, self._create_item(entry.original_value))

            # Custom value (editable)
            custom_item = self._create_item(entry.custom_value)
            self.table.setItem(row, 4, custom_item)

            # Status
            status_item = self._create_item(entry.status)
            status_item.setForeground(self._status_color(entry.status))
            self.table.setItem(row, 5, status_item)

        self.table.blockSignals(False)

    def _create_item(self, text: str):
        """Create table item with text."""
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        return item

    def _status_color(self, status: str) -> QColor:
        """Get color for status."""
        colors = {
            "Modified": QColor("#4CAF50"),
            "Unmodified": QColor("#999999"),
            "New": QColor("#FF9800"),
        }
        return colors.get(status, QColor("black"))

    def update_category_combo(self):
        """Update category combo with unique categories."""
        categories = sorted(set(e.category for e in self.entries))
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("All")
        self.category_combo.addItems(categories)
        self.category_combo.blockSignals(False)

    @pyqtSlot()
    def on_search_changed(self):
        """Handle search input change with debounce."""
        self.filter_timer.stop()
        self.filter_timer.start()

    @pyqtSlot()
    def apply_filters(self):
        """Apply filters to table rows."""
        if not self.entries:
            return

        search_text = self.search_input.text().lower()
        category_filter = self.category_combo.currentText()
        status_filter = self.status_combo.currentText()
        hide_unmodified = self.hide_unmodified_check.isChecked()

        self.table.blockSignals(True)
        visible_count = 0
        for row, entry in enumerate(self.entries):
            show = True

            if search_text and not (
                search_text in entry.key.lower() or
                search_text in entry.original_value.lower() or
                search_text in entry.custom_value.lower()
            ):
                show = False

            if category_filter != "All" and entry.category != category_filter:
                show = False

            if status_filter != "All" and entry.status != status_filter:
                show = False

            if hide_unmodified and entry.status == "Unmodified":
                show = False

            self.table.setRowHidden(row, not show)
            if show:
                visible_count += 1

        self.table.blockSignals(False)

        self.table_status_label.setText(f"Showing {visible_count} of {len(self.entries)} strings")

    @pyqtSlot()
    def clear_filters(self):
        """Clear all filters."""
        self.search_input.blockSignals(True)
        self.category_combo.blockSignals(True)
        self.status_combo.blockSignals(True)
        self.hide_unmodified_check.blockSignals(True)

        self.search_input.clear()
        self.category_combo.setCurrentIndex(0)
        self.status_combo.setCurrentIndex(0)
        self.hide_unmodified_check.setChecked(False)

        self.search_input.blockSignals(False)
        self.category_combo.blockSignals(False)
        self.status_combo.blockSignals(False)
        self.hide_unmodified_check.blockSignals(False)

        self.apply_filters()

    @pyqtSlot(QTableWidgetItem)
    def on_item_changed(self, item: QTableWidgetItem):
        """Handle table item edit."""
        row = item.row()
        col = item.column()

        if col == 4 and row < len(self.entries):  # Custom Value column
            self.entries[row].custom_value = item.text()
            self.entries[row].status = "Modified" if item.text() != self.entries[row].original_value else "Unmodified"
            self.table.setItem(row, 5, self._create_item(self.entries[row].status))

    def show_context_menu(self, position):
        """Show right-click context menu."""
        item = self.table.itemAt(position)
        if not item:
            return

        row = item.row()
        if row >= len(self.entries):
            return

        menu = QMenu(self)
        menu.addAction("Edit", lambda: self.edit_cell(row))
        menu.addAction("Reset to Original", lambda: self.reset_to_original(row))
        menu.addAction("Copy Key", lambda: self.copy_key(row))
        menu.exec(self.table.mapToGlobal(position))

    def edit_cell(self, row: int):
        """Edit custom value cell."""
        self.table.editItem(self.table.item(row, 3))

    def reset_to_original(self, row: int):
        """Reset custom value to original."""
        if row < len(self.entries):
            self.entries[row].custom_value = ""
            self.entries[row].status = "Unmodified"
            self.populate_table()

    def copy_key(self, row: int):
        """Copy key to clipboard."""
        if row < len(self.entries):
            import pyperclip
            try:
                pyperclip.copy(self.entries[row].key)
                self.statusBar().showMessage(f"Copied: {self.entries[row].key}")
            except ImportError:
                self.statusBar().showMessage("pyperclip not installed")

    def restore_window_state(self):
        """Restore window geometry and state."""
        geometry = AppSettings.get_window_geometry()
        state = AppSettings.get_window_state()

        if geometry:
            self.restoreGeometry(geometry)
        if state:
            self.restoreState(state)

    def closeEvent(self, event):
        """Save window state on close."""
        AppSettings.set_window_geometry(self.saveGeometry())
        AppSettings.set_window_state(self.saveState())
        event.accept()
