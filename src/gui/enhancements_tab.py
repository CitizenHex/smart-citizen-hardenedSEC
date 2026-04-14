"""Enhancements tab for SC Localization Editor."""
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QCheckBox, QComboBox, QMessageBox
)
from PyQt6.QtCore import pyqtSignal

from src.utils.settings import AppSettings

logger = logging.getLogger(__name__)


class EnhancementsTab(QWidget):
    """Tab for optional enhancements: localization enhancements and ship favorites."""

    merge_requested = pyqtSignal()
    enhancements_pipeline_requested = pyqtSignal()   # extract DataForge if needed, then generate enhancements

    def __init__(self):
        super().__init__()
        self._loaded_prefix = AppSettings.get_favorite_prefix()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Enhancements")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        desc = QLabel(
            "Optional features that extend the base localization data. "
            "Each can be enabled or disabled independently."
        )
        desc.setStyleSheet("font-size: 11px; color: #666;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addWidget(self._build_enhancements_group())
        layout.addWidget(self._build_favorites_group())
        layout.addStretch()

    # ── Enhancements ─────────────────────────────────────────────────────────

    def _build_enhancements_group(self) -> QGroupBox:
        group = QGroupBox("Localization Enhancements")
        gl = QVBoxLayout(group)

        self.enhancements_enabled_checkbox = QCheckBox(
            "Enhance ship, component, and weapon descriptions with game data"
        )
        self.enhancements_enabled_checkbox.setChecked(AppSettings.get_enhancements_enabled())
        self.enhancements_enabled_checkbox.toggled.connect(self._on_enhancements_toggled)
        gl.addWidget(self.enhancements_enabled_checkbox)

        enhancements_desc = QLabel(
            "When enabled, numerical stats (speed, DPS, shield HP, etc.) are appended to "
            "description entries. Enhancements are generated from your installed Data.p4k."
        )
        enhancements_desc.setStyleSheet("font-size: 11px; color: #666;")
        enhancements_desc.setWordWrap(True)
        gl.addWidget(enhancements_desc)

        # Per-file status dots + single action button
        self._enhancements_status_labels: dict = {}
        status_row = QHBoxLayout()

        for key, label in {
            "ship_descs":        "Ships",
            "component_descs":   "Components",
            "ship_weapon_descs": "Ship Weapons",
            "fps_weapon_descs":  "FPS Weapons",
        }.items():
            dot = QLabel("●")
            dot.setStyleSheet("color: #999; font-size: 12px;")
            status_row.addWidget(dot)
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 11px;")
            status_row.addWidget(lbl)
            status_row.addSpacing(8)
            self._enhancements_status_labels[key] = dot

        status_row.addStretch()

        self._generate_enhancements_btn = QPushButton("Generate Enhancements")
        self._generate_enhancements_btn.setMaximumWidth(160)
        self._generate_enhancements_btn.setToolTip(
            "Generate enhanced localization files from your game's Data.p4k.\n"
            "DataForge data will be extracted automatically if not already cached\n"
            "(first run takes ~5–10 minutes; subsequent runs are fast)."
        )
        self._generate_enhancements_btn.clicked.connect(self.enhancements_pipeline_requested.emit)
        status_row.addWidget(self._generate_enhancements_btn)

        gl.addLayout(status_row)

        self._forge_status_label = QLabel()
        self._forge_status_label.setStyleSheet("font-size: 10px; color: #666;")
        gl.addWidget(self._forge_status_label)

        self._operation_label = QLabel()
        self._operation_label.setStyleSheet("font-size: 10px; color: #2196F3;")
        self._operation_label.setVisible(False)
        gl.addWidget(self._operation_label)

        self.refresh_enhancements_status()
        return group

    def _on_enhancements_toggled(self, checked: bool):
        AppSettings.set_enhancements_enabled(checked)
        self.merge_requested.emit()

    # ── Favorites ─────────────────────────────────────────────────────────────

    def _build_favorites_group(self) -> QGroupBox:
        group = QGroupBox("Favorites")
        gl = QVBoxLayout(group)

        favorites_desc = QLabel(
            "Favorited ships have a prefix character prepended to their name so they "
            "sort to the top of the in-game ship list. Choose which character to use:"
        )
        favorites_desc.setStyleSheet("font-size: 11px; color: #666;")
        favorites_desc.setWordWrap(True)
        gl.addWidget(favorites_desc)

        prefix_row = QHBoxLayout()
        prefix_row.addWidget(QLabel("Sort prefix:"))

        self.favorite_prefix_combo = QComboBox()
        self.favorite_prefix_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self.favorite_prefix_combo.addItem("  (space)", userData=" ")
        for code in range(33, 65):
            self.favorite_prefix_combo.addItem(chr(code), userData=chr(code))

        for i in range(self.favorite_prefix_combo.count()):
            if self.favorite_prefix_combo.itemData(i) == self._loaded_prefix:
                self.favorite_prefix_combo.setCurrentIndex(i)
                break

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
        gl.addLayout(prefix_row)
        return group

    def _apply_favorite_prefix(self):
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

    # ── Operation state ───────────────────────────────────────────────────────

    def set_operation_running(self, message: str):
        """Disable the enhancements button and show an inline progress message."""
        self._generate_enhancements_btn.setEnabled(False)
        self._operation_label.setText(message)
        self._operation_label.setVisible(True)

    def set_operation_progress(self, message: str):
        """Update the inline progress message without changing button state."""
        self._operation_label.setText(message)

    def set_operation_idle(self):
        """Re-enable the enhancements button and hide the progress message."""
        self._generate_enhancements_btn.setEnabled(True)
        self._operation_label.setVisible(False)
        self._operation_label.setText("")

    # ── Status refresh ────────────────────────────────────────────────────────

    def refresh_enhancements_status(self):
        """Update enhancement file status indicators and DataForge cache status."""
        cache_dir = AppSettings.get_cache_dir()
        for key, dot in self._enhancements_status_labels.items():
            filename = AppSettings.ENHANCEMENTS_FILES[key]
            present = (cache_dir / filename).exists()
            dot.setStyleSheet(f"color: {'#4caf50' if present else '#f44336'}; font-size: 12px;")
        self.refresh_forge_status()

    def refresh_forge_status(self):
        """Update the DataForge cache status label."""
        from src.utils.pak_extractor import dataforge_cache_is_fresh
        forge_dir = AppSettings.get_dataforge_cache_dir()
        p4k_path = AppSettings.get_p4k_path()
        if not (forge_dir / ".p4k_mtime").exists():
            self._forge_status_label.setText(
                "DataForge: not yet extracted — click 'Generate Enhancements' to begin"
            )
            self._forge_status_label.setStyleSheet("font-size: 10px; color: #f44336;")
        elif p4k_path.exists() and not dataforge_cache_is_fresh(p4k_path, forge_dir):
            self._forge_status_label.setText(
                "DataForge: cache outdated — click 'Generate Enhancements' to re-extract and update"
            )
            self._forge_status_label.setStyleSheet("font-size: 10px; color: #ff9800;")
        else:
            self._forge_status_label.setText("DataForge: cache up to date ✓")
            self._forge_status_label.setStyleSheet("font-size: 10px; color: #4caf50;")
