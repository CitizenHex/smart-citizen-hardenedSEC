"""Configuration tab for SC Localization Editor."""
import logging
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit,
    QPushButton, QLabel, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal

from src.utils.settings import AppSettings

logger = logging.getLogger(__name__)


class ConfigTab(QWidget):
    """Configuration tab — game path, P4K extraction, and import tools."""

    merge_requested = pyqtSignal()
    p4k_extract_requested = pyqtSignal()
    import_ini_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Configuration")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        instructions = QLabel(
            "Configure your Star Citizen installation path, extract base localization "
            "from Data.p4k, and import external INI files to customize your strings."
        )
        instructions.setStyleSheet("font-size: 11px; color: #666;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # ── Star Citizen Installation ────────────────────────────────────────
        game_group = QGroupBox("Star Citizen Installation")
        game_layout = QVBoxLayout(game_group)

        game_desc = QLabel("Path to Star Citizen LIVE directory")
        game_desc.setStyleSheet("font-size: 11px; color: #666; margin-bottom: 5px;")
        game_layout.addWidget(game_desc)

        game_input_layout = QHBoxLayout()
        self.game_path_input = QLineEdit()
        self.game_path_input.setText(AppSettings.get_game_install_path())
        self.game_path_input.setPlaceholderText(
            r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE"
        )
        self.game_path_input.editingFinished.connect(self._save_game_path)
        game_input_layout.addWidget(self.game_path_input)

        game_browse_btn = QPushButton("Browse...")
        game_browse_btn.setMaximumWidth(100)
        game_browse_btn.clicked.connect(self._browse_game_path)
        game_input_layout.addWidget(game_browse_btn)
        game_layout.addLayout(game_input_layout)
        layout.addWidget(game_group)

        # ── P4K Extraction ───────────────────────────────────────────────────
        p4k_group = QGroupBox("Base Localization (P4K Extraction)")
        p4k_layout = QVBoxLayout(p4k_group)

        p4k_desc = QLabel(
            "Extract global.ini from your installed Data.p4k to get stock game strings "
            "that always match your installed version."
        )
        p4k_desc.setStyleSheet("font-size: 11px; color: #666;")
        p4k_desc.setWordWrap(True)
        p4k_layout.addWidget(p4k_desc)

        p4k_status_row = QHBoxLayout()
        self._p4k_status_dot = QLabel("●")
        self._p4k_status_dot.setStyleSheet("font-size: 14px;")
        p4k_status_row.addWidget(self._p4k_status_dot)

        self._p4k_status_label = QLabel()
        self._p4k_status_label.setStyleSheet("font-size: 11px; color: #666;")
        p4k_status_row.addWidget(self._p4k_status_label)
        p4k_status_row.addStretch()

        extract_btn = QPushButton("Extract from Data.p4k")
        extract_btn.setMaximumWidth(180)
        extract_btn.clicked.connect(self.p4k_extract_requested.emit)
        p4k_status_row.addWidget(extract_btn)

        p4k_layout.addLayout(p4k_status_row)
        layout.addWidget(p4k_group)

        self._refresh_p4k_status()

        # ── Tools ────────────────────────────────────────────────────────────
        tools_group = QGroupBox("Tools")
        tools_layout = QVBoxLayout(tools_group)

        tools_desc = QLabel(
            "Import an external INI file to merge custom strings into your user.ini. "
            "Keys are validated against base.ini, and conflicts are resolved interactively."
        )
        tools_desc.setStyleSheet("font-size: 11px; color: #666;")
        tools_desc.setWordWrap(True)
        tools_layout.addWidget(tools_desc)

        button_layout = QHBoxLayout()

        import_btn = QPushButton("Import INI...")
        import_btn.setMaximumWidth(150)
        import_btn.clicked.connect(self.import_ini_requested.emit)
        button_layout.addWidget(import_btn)

        preview_btn = QPushButton("Preview Merge")
        preview_btn.setMaximumWidth(150)
        preview_btn.clicked.connect(self.preview_merge)
        button_layout.addWidget(preview_btn)

        button_layout.addStretch()
        tools_layout.addLayout(button_layout)
        layout.addWidget(tools_group)

        layout.addStretch()

    # ── Game path ────────────────────────────────────────────────────────────

    def _save_game_path(self):
        """Save game path when editing finishes."""
        game_path = self.game_path_input.text()
        if game_path and not Path(game_path).exists():
            logger.warning(f"Game path does not exist: {game_path}")
        else:
            AppSettings.set_game_install_path(game_path)

    def _browse_game_path(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select Star Citizen Installation Path"
        )
        if path:
            self.game_path_input.setText(path)
            self._save_game_path()

    # ── P4K status ───────────────────────────────────────────────────────────

    def _refresh_p4k_status(self):
        p4k_path = AppSettings.get_p4k_path()
        base_ini = AppSettings.get_cache_dir() / 'base.ini'

        if p4k_path.exists():
            self._p4k_status_dot.setStyleSheet("color: #4caf50; font-size: 14px;")
            if base_ini.exists():
                try:
                    last_str = datetime.fromtimestamp(
                        base_ini.stat().st_mtime
                    ).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    last_str = "unknown"
                self._p4k_status_label.setText(
                    f"Data.p4k found  |  base.ini last updated: {last_str}"
                )
            else:
                self._p4k_status_label.setText("Data.p4k found  |  base.ini not yet extracted")
        else:
            self._p4k_status_dot.setStyleSheet("color: #f44336; font-size: 14px;")
            if AppSettings.get_game_install_path():
                self._p4k_status_label.setText(f"Data.p4k not found at: {p4k_path}")
            else:
                self._p4k_status_label.setText("Game install path not configured")

    # ── Preview ──────────────────────────────────────────────────────────────

    def preview_merge(self):
        """Show a dry-run summary of the current merge configuration."""
        try:
            from src.parser.ini_parser import load_sources_from_settings, load_source_files

            sources_dict, hierarchy, _enhancements_cats = load_sources_from_settings()

            if not sources_dict:
                QMessageBox.warning(self, "Warning", "No sources available to merge.")
                return

            entries = load_source_files(sources_dict, hierarchy)

            source_counts = {}
            for entry in entries:
                source_counts[entry.source_file] = source_counts.get(entry.source_file, 0) + 1

            text = "Merge Preview\n\nMerge Order (top to bottom):\n"
            for i, name in enumerate(hierarchy, 1):
                text += f"  {i}. {name.capitalize()} ({source_counts.get(name, 0)} keys)\n"

            text += f"\nTotal Keys: {len(entries)}\nStatus Breakdown:\n"
            status_counts = {}
            for entry in entries:
                status_counts[entry.status] = status_counts.get(entry.status, 0) + 1
            for status, count in status_counts.items():
                text += f"  {status}: {count}\n"

            QMessageBox.information(self, "Merge Preview", text)

        except Exception as e:
            logger.exception(f"Error previewing merge: {e}")
            QMessageBox.critical(self, "Error", f"Failed to preview merge: {e}")
