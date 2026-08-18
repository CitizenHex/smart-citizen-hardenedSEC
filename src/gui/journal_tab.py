"""Personal, offline activity journal UI."""
from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QLabel, QListWidget, QMessageBox, QPushButton, QVBoxLayout, QWidget

from src.utils.session_journal import journal_path, load_journal_events, save_journal_events
from src.utils.settings import AppSettings


class JournalTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Personal Journal\n"
            "Reads explicit activity from your local Star Citizen Game.log. "
            "Nothing is uploaded. Money, kills, cargo, and refinery jobs are "
            "not recorded unless the game log proves them explicitly."
        ))
        self.refresh = QPushButton("Refresh From Game Log")
        self.refresh.clicked.connect(self._refresh)
        layout.addWidget(self.refresh)
        self.summary = QLabel("No session history imported yet.")
        layout.addWidget(self.summary)
        self.listing = QListWidget()
        layout.addWidget(self.listing)

    def _refresh(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Star Citizen Game.log", "", "Game log (*.log)")
        if not path:
            return
        try:
            events = load_journal_events(Path(path))
            save_journal_events(journal_path(AppSettings.get_user_data_dir()), events)
        except OSError as exc:
            QMessageBox.warning(self, "Journal not updated", str(exc))
            return
        self.listing.clear()
        for event in events:
            self.listing.addItem(f"{event['timestamp']} — {event['summary']}")
        self.summary.setText(f"Imported {len(events)} verified activity events from the selected log.")
