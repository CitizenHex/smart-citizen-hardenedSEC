"""Update-available dialog with scrollable release notes (#211).

Replaces the old QMessageBox prompt so the full release notes render in a
scrollable pane instead of a 600-character excerpt. The caller pre-renders
the notes markdown to HTML (via ``MainWindow.markdown_to_html``, which
supplies palette colours) so this module stays free of theme logic.

The user's decision is exposed as ``.choice`` after ``exec()``:

- ``CHOICE_UPDATE``    — auto-update authorized; caller downloads + installs.
- ``CHOICE_OPEN_PAGE`` — open the GitHub release page in the browser.
- ``CHOICE_LATER``     — dismissed; startup continues normally.

``can_auto_update=False`` (portable build, or a release published without an
installer asset) swaps the primary button from Update Now to Open Release
Page — the download/install path is never offered where it can't work.
"""
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from src.utils.i18n import tr


class UpdateDialog(QDialog):
    CHOICE_UPDATE = "update"
    CHOICE_OPEN_PAGE = "open_page"
    CHOICE_LATER = "later"

    def __init__(self, parent, latest: str, current: str, notes_html: str,
                 can_auto_update: bool):
        super().__init__(parent)
        self.choice = self.CHOICE_LATER

        self.setWindowTitle(tr("dialogs.update_available_title"))
        self.setModal(True)
        self.resize(560, 480)

        layout = QVBoxLayout(self)

        headline = QLabel(
            tr("dialogs.update_available_body", latest=latest, current=current)
        )
        headline.setWordWrap(True)
        layout.addWidget(headline)

        notes = QTextBrowser(self)
        notes.setHtml(notes_html)
        notes.setOpenExternalLinks(True)
        layout.addWidget(notes, stretch=1)

        if can_auto_update:
            note = QLabel(tr("dialogs.update_auto_note"))
            note.setWordWrap(True)
            note.setProperty("role", "secondary")
            layout.addWidget(note)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        if can_auto_update:
            primary = QPushButton(tr("dialogs.update_now"))
            primary.clicked.connect(self._choose_update)
        else:
            primary = QPushButton(tr("dialogs.update_open_release"))
            primary.clicked.connect(self._choose_open_page)
        primary.setDefault(True)
        later = QPushButton(tr("dialogs.update_later"))
        later.clicked.connect(self.reject)
        buttons.addWidget(primary)
        buttons.addWidget(later)
        layout.addLayout(buttons)

    def _choose_update(self) -> None:
        self.choice = self.CHOICE_UPDATE
        self.accept()

    def _choose_open_page(self) -> None:
        self.choice = self.CHOICE_OPEN_PAGE
        self.accept()
