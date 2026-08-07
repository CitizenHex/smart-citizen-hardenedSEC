"""Read-only Crafting Planner UI."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)
from src.utils.i18n import tr


class CraftingPlannerTab(QWidget):
    """Search local crafting recipes and show their authored ingredients."""
    refresh_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._recipes = []
        self._setup_ui()

    def _setup_ui(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.title = QLabel(tr("crafting_planner.title"))
        self.title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.title)
        self.description = QLabel(tr("crafting_planner.description"))
        self.description.setWordWrap(True)
        self.description.setProperty("role", "secondary")
        layout.addWidget(self.description)
        self.refresh_button = QPushButton(tr("crafting_planner.refresh"))
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        layout.addWidget(self.refresh_button)
        self.status = QLabel(tr("crafting_planner.not_loaded"))
        self.status.setProperty("role", "secondary")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("crafting_planner.search"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._render_list)
        layout.addWidget(self.search)
        row = QHBoxLayout()
        self.recipe_list = QListWidget()
        self.recipe_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.recipe_list.currentRowChanged.connect(self._render_details)
        row.addWidget(self.recipe_list, 1)
        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.TextFormat.RichText)
        self.details.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.details.setMinimumWidth(280)
        self.details.setFrameShape(QFrame.Shape.StyledPanel)
        self.details.setContentsMargins(12, 12, 12, 12)
        row.addWidget(self.details, 1)
        layout.addLayout(row, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def set_loading(self, loading: bool):
        self.refresh_button.setEnabled(not loading)
        if loading:
            self.status.setText(tr("crafting_planner.loading"))

    def set_recipes(self, recipes):
        self._recipes = list(recipes)
        self.status.setText(tr("crafting_planner.loaded", count=len(self._recipes)))
        self._render_list()

    def set_error(self, message: str):
        self.status.setText(message)

    def _filtered_recipes(self):
        query = self.search.text().strip().casefold()
        return self._recipes if not query else [r for r in self._recipes if query in r.name.casefold() or query in r.category.casefold()]

    def _render_list(self):
        recipes = self._filtered_recipes()
        self.recipe_list.clear()
        for recipe in recipes:
            item = QListWidgetItem(recipe.name)
            item.setData(Qt.ItemDataRole.UserRole, recipe)
            item.setToolTip(recipe.category)
            self.recipe_list.addItem(item)
        if recipes:
            self.recipe_list.setCurrentRow(0)
        else:
            self.details.setText(tr("crafting_planner.no_matches"))

    def _render_details(self, row: int):
        item = self.recipe_list.item(row)
        if item is None:
            return
        recipe = item.data(Qt.ItemDataRole.UserRole)
        lines = [f"<b>{recipe.name}</b>", f"<br><span style='color:#888'>{recipe.category}</span>", "<br><br><b>Materials needed</b>"]
        for ingredient in recipe.ingredients:
            suffix = "" if ingredient.resolved else " <span style='color:#c88'>(unresolved)</span>"
            lines.append(f"<br>• {ingredient.quantity} × {ingredient.name}{suffix}")
        self.details.setText("".join(lines))

    def retranslate_ui(self):
        self.title.setText(tr("crafting_planner.title"))
        self.description.setText(tr("crafting_planner.description"))
        self.refresh_button.setText(tr("crafting_planner.refresh"))
        self.search.setPlaceholderText(tr("crafting_planner.search"))
