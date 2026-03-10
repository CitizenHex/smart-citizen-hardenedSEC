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
        base_layout = QVBoxLayout(base_group)

        # Description label
        base_desc = QLabel("Path to the base global.ini file (with language folder)")
        base_desc.setStyleSheet("font-size: 11px; color: #666; margin-bottom: 5px;")
        base_layout.addWidget(base_desc)

        # Input and browse button in horizontal layout
        base_input_layout = QHBoxLayout()
        self.base_path_input = QLineEdit()
        self.base_path_input.setText(AppSettings.get_base_global_path())
        self.base_path_input.setPlaceholderText("Roberts Space Industries/StarCitizen/LIVE/data/Localization/<LANG>/global.ini")
        base_input_layout.addWidget(self.base_path_input)

        base_browse_btn = QPushButton("Browse...")
        base_browse_btn.setMaximumWidth(100)
        base_browse_btn.clicked.connect(self.browse_base_global)
        base_input_layout.addWidget(base_browse_btn)
        base_layout.addLayout(base_input_layout)
        layout.addWidget(base_group)

        # Game install path group
        game_group = QGroupBox("Star Citizen Install Path")
        game_layout = QVBoxLayout(game_group)

        # Description label
        game_desc = QLabel("Path to Star Citizen root directory (where LIVE folder is located)")
        game_desc.setStyleSheet("font-size: 11px; color: #666; margin-bottom: 5px;")
        game_layout.addWidget(game_desc)

        # Input and browse button in horizontal layout
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
            game_path = self.game_path_input.text()

            if base_path and not Path(base_path).exists():
                QMessageBox.warning(self, "Warning", "Base global.ini path does not exist")
                return

            if game_path and not Path(game_path).exists():
                QMessageBox.warning(self, "Warning", "Game path does not exist")
                return

            AppSettings.set_base_global_path(base_path)
            AppSettings.set_game_install_path(game_path)

            QMessageBox.information(self, "Success", "Configuration saved")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {e}")
