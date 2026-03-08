"""Configuration tab for SC Localization Editor."""
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit,
    QPushButton, QCheckBox, QLabel, QFileDialog, QMessageBox
)

from src.utils.settings import AppSettings


class ConfigTab(QWidget):
    """Configuration tab widget."""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Build configuration UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Base Global.ini group
        base_group = QGroupBox("Base global.ini")
        base_layout = QHBoxLayout(base_group)
        self.base_path_input = QLineEdit()
        self.base_path_input.setText(AppSettings.get_base_global_path())
        self.base_path_input.setPlaceholderText("Path to base global.ini (CIG original or existing pack)")
        base_layout.addWidget(self.base_path_input)

        base_browse_btn = QPushButton("Browse...")
        base_browse_btn.setMaximumWidth(100)
        base_browse_btn.clicked.connect(self.browse_base_global)
        base_layout.addWidget(base_browse_btn)
        layout.addWidget(base_group)

        # Vehicles.ini group
        vehicles_group = QGroupBox("vehicles.ini")
        vehicles_layout = QHBoxLayout(vehicles_group)
        self.vehicles_path_input = QLineEdit()
        self.vehicles_path_input.setText(AppSettings.get_vehicles_path())
        self.vehicles_path_input.setPlaceholderText("Path to vehicles.ini")
        vehicles_layout.addWidget(self.vehicles_path_input)

        vehicles_browse_btn = QPushButton("Browse...")
        vehicles_browse_btn.setMaximumWidth(100)
        vehicles_browse_btn.clicked.connect(self.browse_vehicles)
        vehicles_layout.addWidget(vehicles_browse_btn)
        layout.addWidget(vehicles_group)

        # Game install path group
        game_group = QGroupBox("Star Citizen Install Path")
        game_layout = QHBoxLayout(game_group)
        self.game_path_input = QLineEdit()
        self.game_path_input.setText(AppSettings.get_game_install_path())
        self.game_path_input.setPlaceholderText("Path to Star Citizen installation")
        game_layout.addWidget(self.game_path_input)

        game_browse_btn = QPushButton("Browse...")
        game_browse_btn.setMaximumWidth(100)
        game_browse_btn.clicked.connect(self.browse_game_path)
        game_layout.addWidget(game_browse_btn)
        layout.addWidget(game_group)

        # Auto-write group
        auto_group = QGroupBox("Output")
        auto_layout = QVBoxLayout(auto_group)
        self.auto_write_check = QCheckBox("Auto-write to game installation after merge")
        self.auto_write_check.setChecked(AppSettings.get_auto_write_enabled())
        auto_layout.addWidget(self.auto_write_check)
        layout.addWidget(auto_group)

        # Save button
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Configuration")
        save_btn.setMaximumWidth(150)
        save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        layout.addStretch()

    def browse_base_global(self):
        """Browse for base global.ini."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Base global.ini", "", "INI Files (*.ini);;All Files (*)"
        )
        if path:
            self.base_path_input.setText(path)

    def browse_vehicles(self):
        """Browse for vehicles.ini."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select vehicles.ini", "", "INI Files (*.ini);;All Files (*)"
        )
        if path:
            self.vehicles_path_input.setText(path)

    def browse_game_path(self):
        """Browse for game installation path."""
        path = QFileDialog.getExistingDirectory(
            self, "Select Star Citizen Installation Path"
        )
        if path:
            self.game_path_input.setText(path)

    def save_config(self):
        """Save configuration."""
        try:
            base_path = self.base_path_input.text()
            vehicles_path = self.vehicles_path_input.text()
            game_path = self.game_path_input.text()
            auto_write = self.auto_write_check.isChecked()

            if base_path and not Path(base_path).exists():
                QMessageBox.warning(self, "Warning", "Base global.ini path does not exist")
                return

            if vehicles_path and not Path(vehicles_path).exists():
                QMessageBox.warning(self, "Warning", "vehicles.ini path does not exist")
                return

            if game_path and not Path(game_path).exists():
                QMessageBox.warning(self, "Warning", "Game path does not exist")
                return

            AppSettings.set_base_global_path(base_path)
            AppSettings.set_vehicles_path(vehicles_path)
            AppSettings.set_game_install_path(game_path)
            AppSettings.set_auto_write_enabled(auto_write)

            QMessageBox.information(self, "Success", "Configuration saved")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {e}")
