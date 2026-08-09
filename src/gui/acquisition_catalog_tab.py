"""UI for reviewing and locally tagging loot/item acquisition status."""
from __future__ import annotations

import re

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from src.utils.acquisition_catalog import (
    DISPLAY_TAGS, catalog_to_json, load_catalog_file, set_item_status, status_for_entry,
)
from src.utils.settings import AppSettings
from src.utils.loot_tag_categories import (
    CATEGORY_LABELS, classify_loot_item, normalize_category_settings,
)


class AcquisitionCatalogTab(QWidget):
    """Local item list for [Shop], [Keep], and [Limited] labels."""
    catalog_changed = pyqtSignal()
    refresh_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._entries = []
        self._catalog = AppSettings.get_acquisition_catalog()
        self._categories = AppSettings.get_loot_tag_categories()
        self._category_checks = {}
        self._setup_ui()

    def _setup_ui(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        title = QLabel("Loot Tags")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        note = QLabel(
            "Add a local tag to item names before applying changes. [Shop] means "
            "you have personally confirmed it can be purchased; [Keep] means "
            "you want to retain it; [Limited] is for confirmed limited/event items. "
            "[Unlisted] means the name exactly matches an item in the Finder community catalog "
            "that is not marked sold. Nothing is guessed or shared automatically."
        )
        note.setWordWrap(True)
        note.setProperty("role", "secondary")
        layout.addWidget(note)
        groups = QLabel("Show tags for")
        groups.setStyleSheet("font-weight: bold;")
        layout.addWidget(groups)
        category_grid = QGridLayout()
        for index, (name, label) in enumerate(CATEGORY_LABELS.items()):
            check = QCheckBox(label)
            check.setChecked(self._categories[name])
            check.toggled.connect(self._categories_changed)
            check.setToolTip("Controls visible [Shop]/[Unlisted] labels; it does not remove catalog data.")
            self._category_checks[name] = check
            category_grid.addWidget(check, index // 2, index % 2)
        layout.addLayout(category_grid)
        category_note = QLabel(
            "Clothing, food/drink, and medical supplies start off to keep everyday loot uncluttered. "
            "Enable any group whenever you want it tagged."
        )
        category_note.setWordWrap(True)
        category_note.setProperty("role", "secondary")
        layout.addWidget(category_note)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search loaded item names")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._render)
        layout.addWidget(self.search)
        self.items = QListWidget()
        self.items.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.items.currentItemChanged.connect(self._update_details)
        layout.addWidget(self.items, 1)
        self.details = QLabel("Load game data to review item names.")
        self.details.setWordWrap(True)
        self.details.setProperty("role", "secondary")
        layout.addWidget(self.details)
        buttons = QHBoxLayout()
        for label, status in (("Mark Shop", "shop"), ("Mark Keep", "keep"), ("Mark Limited", "limited"), ("Clear Tag", None)):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, s=status: self._mark_selected(s))
            buttons.addWidget(button)
        layout.addLayout(buttons)
        files = QHBoxLayout()
        export_btn = QPushButton("Export Catalog")
        export_btn.setToolTip("Save your reviewed local catalog as a JSON file.")
        export_btn.clicked.connect(self._export_catalog)
        files.addWidget(export_btn)
        import_btn = QPushButton("Import Catalog")
        import_btn.setToolTip("Explicitly replace the local catalog with a reviewed JSON file.")
        import_btn.clicked.connect(self._import_catalog)
        files.addWidget(import_btn)
        self.refresh_btn = QPushButton("Refresh Finder Shop Data")
        self.refresh_btn.setToolTip(
            "Explicitly fetch the reviewed Finder GetSearch endpoint. Manual tags are preserved."
        )
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        files.addWidget(self.refresh_btn)
        layout.addLayout(files)
        self.catalog_status = QLabel(self._catalog_status_text())
        self.catalog_status.setWordWrap(True)
        self.catalog_status.setProperty("role", "secondary")
        layout.addWidget(self.catalog_status)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def set_entries(self, entries):
        self._entries = [e for e in entries if e.key.lower().startswith("item_name")]
        self._render()

    def _filtered_entries(self):
        query = self.search.text().strip().casefold()
        if not query:
            return self._entries
        return [e for e in self._entries if query in e.original_value.casefold() or query in e.key.casefold()]

    def _catalog_status_text(self):
        version = self._catalog.get("shop_catalog_version", "No Finder catalog loaded")
        return f"Finder catalog: {version}. {len(self._catalog['names']):,} exact-name records; {len(self._catalog['items'])} manual override(s)."

    def _categories_changed(self):
        self._categories = normalize_category_settings({
            name: check.isChecked() for name, check in self._category_checks.items()
        })
        AppSettings.set_loot_tag_categories(self._categories)
        self.catalog_changed.emit()
        self._render()

    def set_refreshing(self, refreshing: bool):
        self.refresh_btn.setEnabled(not refreshing)
        self.refresh_btn.setText("Refreshing Finder Data…" if refreshing else "Refresh Finder Shop Data")

    def replace_finder_catalog(self, catalog: dict, count: int):
        self._catalog = catalog
        AppSettings.set_acquisition_catalog(catalog)
        self.catalog_status.setText(self._catalog_status_text())
        self._render()
        self.catalog_changed.emit()

    def _render(self):
        selected = {i.data(Qt.ItemDataRole.UserRole).key for i in self.items.selectedItems()}
        self.items.clear()
        for entry in self._filtered_entries():
            status = status_for_entry(entry.key, entry.original_value, self._catalog)
            group = classify_loot_item(entry.key, entry.original_value, getattr(entry, "category", ""))
            suffix = f" {DISPLAY_TAGS[status]}" if status else ""
            display_name = re.sub(r"\s*<EM4>\[(?:Shop|Keep|Limited|Unlisted)\]</EM4>", "", entry.original_value)
            hidden = " (group off)" if status and not self._categories[group] else ""
            item = QListWidgetItem(f"{display_name}{suffix}{hidden}")
            item.setData(Qt.ItemDataRole.UserRole, entry)
            item.setToolTip(entry.key)
            self.items.addItem(item)
            if entry.key in selected:
                item.setSelected(True)
        self._update_details()

    def _update_details(self, *_args):
        item = self.items.currentItem()
        if item is None:
            self.details.setText(self._catalog_status_text())
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        record = self._catalog["items"].get(entry.key)
        computed_status = status_for_entry(entry.key, entry.original_value, self._catalog)
        status = DISPLAY_TAGS[computed_status] if computed_status else "No acquisition tag"
        source = record.get("source", "") if record else "Shop catalog reverse match" if computed_status == "unlisted" else ""
        self.details.setText(f"{status}\n{entry.key}" + (f"\nSource: {source}" if source else ""))

    def _mark_selected(self, status):
        selected = [i.data(Qt.ItemDataRole.UserRole) for i in self.items.selectedItems()]
        if not selected:
            return
        catalog = self._catalog
        for entry in selected:
            catalog = set_item_status(catalog, entry.key, status)
        self._catalog = catalog
        AppSettings.set_acquisition_catalog(catalog)
        self.catalog_status.setText(self._catalog_status_text())
        self._render()
        self.catalog_changed.emit()

    def _export_catalog(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Loot Tag Catalog", "acquisition-catalog.json", "JSON files (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(catalog_to_json(self._catalog))
        except OSError as exc:
            QMessageBox.warning(self, "Export failed", str(exc))

    def _import_catalog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Loot Tag Catalog", "", "JSON files (*.json)")
        if not path:
            return
        try:
            catalog = load_catalog_file(path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Catalog not imported", str(exc))
            return
        self._catalog = catalog
        AppSettings.set_acquisition_catalog(catalog)
        self.catalog_status.setText(self._catalog_status_text())
        self._render()
        self.catalog_changed.emit()
