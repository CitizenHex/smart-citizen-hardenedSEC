"""Configuration tab for SC Localization Editor."""
import logging
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit,
    QPushButton, QCheckBox, QLabel, QFileDialog, QMessageBox,
    QScrollArea
)
from PyQt6.QtCore import pyqtSignal

from src.utils.settings import AppSettings

logger = logging.getLogger(__name__)


class SourceConfigWidget(QWidget):
    """Widget for configuring a single data source."""

    changed = pyqtSignal()   # emitted whenever any field is edited

    def __init__(self, source_name: str, parent=None):
        super().__init__(parent)
        self.source_name = source_name
        self.source_display_name = source_name.capitalize()
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header: enable checkbox + status dot
        header_layout = QHBoxLayout()
        self.enable_checkbox = QCheckBox(self.source_display_name)
        self.enable_checkbox.setMinimumWidth(100)
        self.enable_checkbox.toggled.connect(self.changed)
        header_layout.addWidget(self.enable_checkbox)

        self.status_label = QLabel("●")
        self.status_label.setStyleSheet("color: #999; font-size: 14px;")
        header_layout.addWidget(self.status_label)

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("font-size: 10px; color: #666;")
        header_layout.addWidget(self.stats_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Path / URL input
        path_layout = QHBoxLayout()
        path_label = QLabel("Path/URL:")
        path_label.setMaximumWidth(80)
        path_layout.addWidget(path_label)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText(f"Enter path or URL for {self.source_display_name}")
        self.path_input.setToolTip(
            "Enter a local file path or a URL.\n"
            "For GitHub URLs, you can paste either:\n"
            "  • Web URL: github.com/user/repo/blob/branch/file.ini\n"
            "  • Raw URL: raw.githubusercontent.com/user/repo/branch/file.ini\n"
            "Both formats will work - web URLs are auto-converted."
        )
        self.path_input.editingFinished.connect(self.changed)
        path_layout.addWidget(self.path_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.setMaximumWidth(100)
        browse_btn.clicked.connect(self._browse_source)
        path_layout.addWidget(browse_btn)

        layout.addLayout(path_layout)

        # Auto-update checkbox (hidden for User source)
        if self.source_name != AppSettings.SOURCE_USER:
            self.auto_update_checkbox = QCheckBox("Auto-update from source")
            self.auto_update_checkbox.toggled.connect(self.changed)
            layout.addWidget(self.auto_update_checkbox)
        else:
            self.auto_update_checkbox = None

        layout.addWidget(QLabel(""))   # spacer

    def load_settings(self):
        """Load source configuration from settings (does not emit changed)."""
        # Block signals so load doesn't fire auto-save
        self.enable_checkbox.blockSignals(True)
        self.path_input.blockSignals(True)
        if self.auto_update_checkbox:
            self.auto_update_checkbox.blockSignals(True)

        self.enable_checkbox.setChecked(AppSettings.is_source_enabled(self.source_name))
        self.path_input.setText(AppSettings.get_source_path(self.source_name))
        if self.auto_update_checkbox:
            self.auto_update_checkbox.setChecked(
                AppSettings.get_source_auto_update(self.source_name)
            )

        self.enable_checkbox.blockSignals(False)
        self.path_input.blockSignals(False)
        if self.auto_update_checkbox:
            self.auto_update_checkbox.blockSignals(False)

        self.update_status()

    def save_settings(self):
        """Persist current widget state to settings."""
        AppSettings.set_source_enabled(self.source_name, self.enable_checkbox.isChecked())

        path = self.path_input.text()
        # Auto-convert GitHub web URLs to raw URLs
        if path.startswith('https://github.com/'):
            path = path.replace('https://github.com/', 'https://raw.githubusercontent.com/')
            path = path.replace('/blob/', '/')
            self.path_input.blockSignals(True)
            self.path_input.setText(path)
            self.path_input.blockSignals(False)

        AppSettings.set_source_path(self.source_name, path)

        if self.auto_update_checkbox:
            AppSettings.set_source_auto_update(
                self.source_name, self.auto_update_checkbox.isChecked()
            )

    def _browse_source(self):
        if self.source_name == AppSettings.SOURCE_USER:
            QMessageBox.information(self, "Info", "User source is automatically managed in AppData")
            return

        path, _ = QFileDialog.getOpenFileName(
            self, f"Select {self.source_display_name} file",
            "", "INI Files (*.ini);;All Files (*)"
        )
        if path:
            self.path_input.setText(path)
            self.changed.emit()

    def update_status(self):
        """Update the status dot based on source availability."""
        if not self.enable_checkbox.isChecked():
            self.status_label.setStyleSheet("color: #999; font-size: 14px;")
            self.stats_label.setText("(disabled)")
            return

        source_path = self.path_input.text()
        if not source_path:
            self.status_label.setStyleSheet("color: #ff9800; font-size: 14px;")
            self.stats_label.setText("(no path configured)")
            return

        if source_path.startswith('http://') or source_path.startswith('https://'):
            self.status_label.setStyleSheet("color: #4caf50; font-size: 14px;")
            self.stats_label.setText("(remote URL)")
        elif Path(source_path).exists():
            self.status_label.setStyleSheet("color: #4caf50; font-size: 14px;")
            self.stats_label.setText("(available)")
        else:
            self.status_label.setStyleSheet("color: #f44336; font-size: 14px;")
            self.stats_label.setText("(file not found)")


class ConfigTab(QWidget):
    """Configuration tab — data sources and game path, auto-saves on any change."""

    merge_requested = pyqtSignal()
    p4k_extract_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.source_widgets = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Data Sources Configuration")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        instructions = QLabel(
            "Changes are saved and reloaded automatically. "
            "Sources are merged in the order shown, with sources lower in the list "
            "overwriting those above."
        )
        instructions.setStyleSheet("font-size: 11px; color: #666;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Data sources
        sources_group = QGroupBox("Data Sources")
        sources_layout = QVBoxLayout(sources_group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        sources_container = QWidget()
        container_layout = QVBoxLayout(sources_container)
        container_layout.setSpacing(12)

        for source_name in AppSettings.AVAILABLE_SOURCES:
            widget = SourceConfigWidget(source_name, self)
            widget.changed.connect(self._auto_save)
            self.source_widgets[source_name] = widget
            container_layout.addWidget(widget)

        container_layout.addStretch()
        scroll.setWidget(sources_container)
        sources_layout.addWidget(scroll)
        layout.addWidget(sources_group)

        # Game install path
        game_group = QGroupBox("Star Citizen Installation")
        game_layout = QVBoxLayout(game_group)

        game_desc = QLabel("Path to Star Citizen root directory (where LIVE folder is located)")
        game_desc.setStyleSheet("font-size: 11px; color: #666; margin-bottom: 5px;")
        game_layout.addWidget(game_desc)

        game_input_layout = QHBoxLayout()
        self.game_path_input = QLineEdit()
        self.game_path_input.setText(AppSettings.get_game_install_path())
        self.game_path_input.setPlaceholderText(
            r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE"
        )
        self.game_path_input.editingFinished.connect(self._auto_save)
        game_input_layout.addWidget(self.game_path_input)

        game_browse_btn = QPushButton("Browse...")
        game_browse_btn.setMaximumWidth(100)
        game_browse_btn.clicked.connect(self._browse_game_path)
        game_input_layout.addWidget(game_browse_btn)
        game_layout.addLayout(game_input_layout)
        layout.addWidget(game_group)

        # P4K extraction
        p4k_group = QGroupBox("P4K Extraction")
        p4k_layout = QVBoxLayout(p4k_group)

        p4k_desc = QLabel(
            "Extract global.ini directly from your installed Data.p4k. "
            "This gives you stock game strings that always match your installed version."
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

        # Preview button (Save button removed — changes auto-save)
        button_layout = QHBoxLayout()
        preview_btn = QPushButton("Preview Merge")
        preview_btn.setMaximumWidth(150)
        preview_btn.clicked.connect(self.preview_merge)
        button_layout.addWidget(preview_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

    # ── Auto-save ─────────────────────────────────────────────────────────────

    def _auto_save(self):
        """Save all source and game-path settings, then trigger a merge reload."""
        try:
            for widget in self.source_widgets.values():
                widget.save_settings()
                widget.update_status()

            game_path = self.game_path_input.text()
            if game_path and not Path(game_path).exists():
                # Don't block the user — just log; they may still be typing
                logger.warning(f"Game path does not exist: {game_path}")
            else:
                AppSettings.set_game_install_path(game_path)

            enabled_sources = [
                name for name in AppSettings.AVAILABLE_SOURCES
                if AppSettings.is_source_enabled(name)
            ]
            if enabled_sources:
                AppSettings.set_merge_hierarchy(enabled_sources)
                self.merge_requested.emit()
            else:
                logger.warning("Auto-save skipped merge: no sources enabled")

        except Exception as e:
            logger.exception(f"Auto-save error: {e}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _browse_game_path(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select Star Citizen Installation Path"
        )
        if path:
            self.game_path_input.setText(path)
            self._auto_save()

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

    def preview_merge(self):
        """Show a dry-run summary of the current merge configuration."""
        try:
            from src.parser.ini_parser import load_sources_from_settings, load_source_files

            sources_dict, hierarchy, _mrk = load_sources_from_settings()

            missing_sources = [
                (name, AppSettings.get_source_path(name))
                for name in hierarchy
                if name != AppSettings.SOURCE_USER and name not in sources_dict
            ]

            if missing_sources:
                msg = "Missing or uncached sources:\n\n"
                for name, path in missing_sources:
                    if path.startswith('http'):
                        msg += f"• {name}: remote source not yet downloaded\n  URL: {path}\n\n"
                    else:
                        msg += f"• {name}: local file not found\n  Path: {path}\n\n"
                QMessageBox.information(self, "Preview Merge", msg)
                return

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
