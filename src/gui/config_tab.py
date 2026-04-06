"""Configuration tab for SC Localization Editor."""
import logging
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit,
    QPushButton, QCheckBox, QLabel, QFileDialog, QMessageBox,
    QListWidget, QListWidgetItem, QScrollArea, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from src.utils.settings import AppSettings

logger = logging.getLogger(__name__)


class SourceConfigWidget(QWidget):
    """Widget for configuring a single data source."""

    def __init__(self, source_name: str, parent=None):
        super().__init__(parent)
        self.source_name = source_name
        self.source_display_name = source_name.capitalize()
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Build source configuration UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header with enable checkbox and source name
        header_layout = QHBoxLayout()
        self.enable_checkbox = QCheckBox(self.source_display_name)
        self.enable_checkbox.setMinimumWidth(100)
        header_layout.addWidget(self.enable_checkbox)

        # Status indicator (color dot) and stats
        self.status_label = QLabel("●")
        self.status_label.setStyleSheet("color: #999; font-size: 14px;")
        header_layout.addWidget(self.status_label)

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("font-size: 10px; color: #666;")
        header_layout.addWidget(self.stats_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Path/URL input
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
        path_layout.addWidget(self.path_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.setMaximumWidth(100)
        browse_btn.clicked.connect(self.browse_source)
        path_layout.addWidget(browse_btn)

        layout.addLayout(path_layout)

        # Auto-update checkbox (hidden for User source)
        if self.source_name != AppSettings.SOURCE_USER:
            self.auto_update_checkbox = QCheckBox("Auto-update from source")
            layout.addWidget(self.auto_update_checkbox)
        else:
            self.auto_update_checkbox = None

        # Separator
        layout.addWidget(QLabel(""))

    def load_settings(self):
        """Load source configuration from settings."""
        is_enabled = AppSettings.is_source_enabled(self.source_name)
        self.enable_checkbox.setChecked(is_enabled)

        path = AppSettings.get_source_path(self.source_name)
        self.path_input.setText(path)

        if self.auto_update_checkbox:
            auto_update = AppSettings.get_source_auto_update(self.source_name)
            self.auto_update_checkbox.setChecked(auto_update)

        self.update_status()

    def save_settings(self):
        """Save source configuration to settings."""
        AppSettings.set_source_enabled(self.source_name, self.enable_checkbox.isChecked())

        # Convert GitHub web URLs to raw URLs
        path = self.path_input.text()
        if path.startswith('https://github.com/'):
            # Convert https://github.com/user/repo/blob/branch/path to raw URL
            path = path.replace('https://github.com/', 'https://raw.githubusercontent.com/')
            path = path.replace('/blob/', '/')
            self.path_input.setText(path)  # Update UI to show converted URL

        AppSettings.set_source_path(self.source_name, path)

        if self.auto_update_checkbox:
            AppSettings.set_source_auto_update(self.source_name, self.auto_update_checkbox.isChecked())

    def browse_source(self):
        """Browse for source file."""
        if self.source_name == AppSettings.SOURCE_USER:
            # User source is auto-managed, can't browse
            QMessageBox.information(self, "Info", "User source is automatically managed in AppData")
            return

        path, _ = QFileDialog.getOpenFileName(
            self, f"Select {self.source_display_name} file",
            "", "INI Files (*.ini);;All Files (*)"
        )
        if path:
            self.path_input.setText(path)

    def update_status(self):
        """Update status indicator based on source availability."""
        if not self.enable_checkbox.isChecked():
            self.status_label.setText("●")
            self.status_label.setStyleSheet("color: #999; font-size: 14px;")
            self.stats_label.setText("(disabled)")
            return

        source_path = self.path_input.text()
        if not source_path:
            self.status_label.setText("●")
            self.status_label.setStyleSheet("color: #ff9800; font-size: 14px;")
            self.stats_label.setText("(no path configured)")
            return

        # Check if file exists (for local files)
        if not (source_path.startswith('http://') or source_path.startswith('https://')):
            if Path(source_path).exists():
                self.status_label.setText("●")
                self.status_label.setStyleSheet("color: #4caf50; font-size: 14px;")
                self.stats_label.setText("(available)")
            else:
                self.status_label.setText("●")
                self.status_label.setStyleSheet("color: #f44336; font-size: 14px;")
                self.stats_label.setText("(file not found)")
        else:
            # For URLs, we can't easily check without downloading
            self.status_label.setText("●")
            self.status_label.setStyleSheet("color: #4caf50; font-size: 14px;")
            self.stats_label.setText("(remote URL)")


class ConfigTab(QWidget):
    """Configuration tab widget with data source management."""

    merge_requested = pyqtSignal()  # Signal when merge should be performed

    def __init__(self):
        super().__init__()
        self.source_widgets = {}
        self.setup_ui()

    def setup_ui(self):
        """Build configuration UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        title = QLabel("Data Sources Configuration")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # Instructions
        instructions = QLabel(
            "Configure your data sources below. Sources are merged in the order shown, "
            "with sources lower in the list overwriting those above."
        )
        instructions.setStyleSheet("font-size: 11px; color: #666;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Data sources group
        sources_group = QGroupBox("Data Sources")
        sources_layout = QVBoxLayout(sources_group)

        # Scroll area for sources (in case many sources)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        sources_container = QWidget()
        container_layout = QVBoxLayout(sources_container)
        container_layout.setSpacing(12)

        # Create widgets for each source
        for source_name in AppSettings.AVAILABLE_SOURCES:
            widget = SourceConfigWidget(source_name, self)
            self.source_widgets[source_name] = widget
            container_layout.addWidget(widget)

        container_layout.addStretch()
        scroll.setWidget(sources_container)
        sources_layout.addWidget(scroll)
        layout.addWidget(sources_group)

        # Game install path group
        game_group = QGroupBox("Star Citizen Installation")
        game_layout = QVBoxLayout(game_group)

        game_desc = QLabel("Path to Star Citizen root directory (where LIVE folder is located)")
        game_desc.setStyleSheet("font-size: 11px; color: #666; margin-bottom: 5px;")
        game_layout.addWidget(game_desc)

        game_input_layout = QHBoxLayout()
        self.game_path_input = QLineEdit()
        self.game_path_input.setText(AppSettings.get_game_install_path())
        self.game_path_input.setPlaceholderText("C:/PATH/TO/Roberts Space Industries/StarCitizen")
        game_input_layout.addWidget(self.game_path_input)

        game_browse_btn = QPushButton("Browse...")
        game_browse_btn.setMaximumWidth(100)
        game_browse_btn.clicked.connect(self.browse_game_path)
        game_input_layout.addWidget(game_browse_btn)
        game_layout.addLayout(game_input_layout)
        layout.addWidget(game_group)

        # Stats data group
        # Stats enhancements group
        stats_group = QGroupBox("Stats Enhancements")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_enabled_checkbox = QCheckBox("Append stats to ship, component, and weapon descriptions")
        self.stats_enabled_checkbox.setChecked(AppSettings.get_stats_enabled())
        stats_layout.addWidget(self.stats_enabled_checkbox)

        stats_desc = QLabel(
            "When enabled, numerical stats (speed, DPS, shield HP, etc.) are appended to "
            "description entries."
        )
        stats_desc.setStyleSheet("font-size: 11px; color: #666;")
        stats_desc.setWordWrap(True)
        stats_layout.addWidget(stats_desc)

        # Status row for each stats file
        cache_dir = AppSettings.get_cache_dir()
        self._stats_status_labels: dict = {}
        stats_file_names = {
            "ship_descs":        "Ships",
            "component_descs":   "Components",
            "ship_weapon_descs": "Ship Weapons",
            "fps_weapon_descs":  "FPS Weapons",
        }
        status_row = QHBoxLayout()
        for key, label in stats_file_names.items():
            filename = AppSettings.STATS_FILES[key]
            present = (cache_dir / filename).exists()
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {'#4caf50' if present else '#f44336'}; font-size: 12px;")
            status_row.addWidget(dot)
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 11px;")
            status_row.addWidget(lbl)
            status_row.addSpacing(8)
            self._stats_status_labels[key] = dot
        status_row.addStretch()
        stats_layout.addLayout(status_row)
        layout.addWidget(stats_group)

        # Favorites settings group
        favorites_group = QGroupBox("Favorites")
        favorites_layout = QVBoxLayout(favorites_group)

        favorites_desc = QLabel(
            "Favorited ships have a prefix character prepended to their name so they "
            "sort to the top of the in-game ship list. Choose which character to use:"
        )
        favorites_desc.setStyleSheet("font-size: 11px; color: #666;")
        favorites_desc.setWordWrap(True)
        favorites_layout.addWidget(favorites_desc)

        prefix_row = QHBoxLayout()
        prefix_row.addWidget(QLabel("Sort prefix:"))
        self.favorite_prefix_combo = QComboBox()
        self.favorite_prefix_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        # ASCII 32–64: space through @
        self.favorite_prefix_combo.addItem("  (space)", userData=" ")
        for code in range(33, 65):
            char = chr(code)
            self.favorite_prefix_combo.addItem(char, userData=char)
        self._loaded_prefix = AppSettings.get_favorite_prefix()
        for i in range(self.favorite_prefix_combo.count()):
            if self.favorite_prefix_combo.itemData(i) == self._loaded_prefix:
                self.favorite_prefix_combo.setCurrentIndex(i)
                break
        # Widen the popup list so every label is fully visible
        self.favorite_prefix_combo.view().setMinimumWidth(
            self.favorite_prefix_combo.sizeHint().width() + 20
        )
        prefix_row.addWidget(self.favorite_prefix_combo)

        apply_prefix_btn = QPushButton("Apply")
        apply_prefix_btn.setToolTip(
            "Save the selected prefix and update all existing favorites to use it"
        )
        apply_prefix_btn.clicked.connect(self._apply_favorite_prefix)
        prefix_row.addWidget(apply_prefix_btn)

        prefix_row.addStretch()
        favorites_layout.addLayout(prefix_row)
        layout.addWidget(favorites_group)

        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Configuration & Merge")
        save_btn.setMaximumWidth(200)
        save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_btn)

        test_btn = QPushButton("Preview Merge")
        test_btn.setMaximumWidth(150)
        test_btn.clicked.connect(self.preview_merge)
        button_layout.addWidget(test_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def _apply_favorite_prefix(self):
        """Save the new prefix and migrate all existing favorites in overrides.ini."""
        new_prefix = self.favorite_prefix_combo.currentData()
        if not new_prefix:
            return

        old_prefix = self._loaded_prefix

        if new_prefix != old_prefix:
            overrides_path = AppSettings.get_overrides_path()
            if overrides_path.exists():
                try:
                    lines = overrides_path.read_text(encoding="utf-8").splitlines()
                    updated = []
                    migrated = 0
                    for line in lines:
                        if "=" in line:
                            key, _, value = line.partition("=")
                            if value.startswith(old_prefix):
                                value = new_prefix + value[len(old_prefix):]
                                migrated += 1
                            updated.append(f"{key}={value}")
                        else:
                            updated.append(line)
                    overrides_path.write_text("\n".join(updated), encoding="utf-8")
                    logger.info(f"Migrated {migrated} favorites from '{old_prefix}' to '{new_prefix}'")
                except Exception as e:
                    logger.exception(f"Failed to migrate favorites: {e}")
                    QMessageBox.critical(self, "Error", f"Failed to update favorites: {e}")
                    return

        AppSettings.set_favorite_prefix(new_prefix)
        self._loaded_prefix = new_prefix
        self.merge_requested.emit()

    def browse_game_path(self):
        """Browse for game installation path."""
        path = QFileDialog.getExistingDirectory(
            self, "Select Star Citizen Installation Path"
        )
        if path:
            self.game_path_input.setText(path)

    def save_config(self):
        """Save configuration and trigger merge."""
        try:
            # Save all source configurations
            for widget in self.source_widgets.values():
                widget.save_settings()

            # Save game path
            game_path = self.game_path_input.text()
            if game_path and not Path(game_path).exists():
                QMessageBox.warning(self, "Warning", "Game path does not exist")
                return

            AppSettings.set_game_install_path(game_path)

            # Save stats enhancements setting
            AppSettings.set_stats_enabled(self.stats_enabled_checkbox.isChecked())

            # Get enabled sources and hierarchy
            enabled_sources = [
                name for name in AppSettings.AVAILABLE_SOURCES
                if AppSettings.is_source_enabled(name)
            ]

            if not enabled_sources:
                QMessageBox.warning(self, "Warning", "No sources enabled. Please enable at least the Global source.")
                return

            # Update hierarchy with enabled sources only
            AppSettings.set_merge_hierarchy(enabled_sources)

            QMessageBox.information(self, "Success", "Configuration saved and sources merged.")
            self.merge_requested.emit()

        except Exception as e:
            logger.exception(f"Error saving configuration: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {e}")

    def preview_merge(self):
        """Preview the merge result."""
        try:
            from src.parser.ini_parser import load_sources_from_settings, load_source_files

            sources_dict, hierarchy = load_sources_from_settings()

            # Check for missing sources (skip user source - it's optional)
            missing_sources = []
            for source_name in hierarchy:
                # User source is optional - skip it
                if source_name == AppSettings.SOURCE_USER:
                    continue

                if source_name not in sources_dict:
                    source_path = AppSettings.get_source_path(source_name)
                    missing_sources.append((source_name, source_path))

            if missing_sources:
                msg = "Missing or uncached sources:\n\n"
                for source_name, source_path in missing_sources:
                    if source_path.startswith('http'):
                        msg += f"• {source_name}: Remote source not downloaded yet\n"
                        msg += f"  URL: {source_path}\n\n"
                    else:
                        msg += f"• {source_name}: Local file not found\n"
                        msg += f"  Path: {source_path}\n\n"

                msg += "\nNote: Remote sources are downloaded when you save configuration.\n"
                msg += "Save the configuration first to cache all sources, then preview again."
                QMessageBox.information(self, "Info", msg)
                return

            if not sources_dict:
                QMessageBox.warning(self, "Warning", "No sources available to merge. Check your source paths.")
                return

            entries = load_source_files(sources_dict, hierarchy)

            # Count by source
            source_counts = {}
            for entry in entries:
                source = entry.source_file
                source_counts[source] = source_counts.get(source, 0) + 1

            # Build preview message
            preview_text = "Merge Preview\n\n"
            preview_text += f"Merge Order (top to bottom):\n"
            for i, source_name in enumerate(hierarchy, 1):
                count = source_counts.get(source_name, 0)
                preview_text += f"  {i}. {source_name.capitalize()} ({count} keys)\n"

            preview_text += f"\nTotal Keys: {len(entries)}\n"
            preview_text += f"Status Breakdown:\n"
            status_counts = {}
            for entry in entries:
                status = entry.status
                status_counts[status] = status_counts.get(status, 0) + 1

            for status, count in status_counts.items():
                preview_text += f"  {status}: {count}\n"

            QMessageBox.information(self, "Merge Preview", preview_text)

        except Exception as e:
            logger.exception(f"Error previewing merge: {e}")
            QMessageBox.critical(self, "Error", f"Failed to preview merge: {e}")
