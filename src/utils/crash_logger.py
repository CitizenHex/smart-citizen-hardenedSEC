"""Crash dialog shown by the crash handler (src/utils/crash_handler.py).

This module used to carry a second, parallel crash-capture system (its own
excepthook, report writer, and log dir). That was dead code — crash_handler.py
owns capture and dump-writing — so only the user-facing dialog survives.
"""
from pathlib import Path


def show_crash_dialog(exc_type, exc_value, crash_path: "Path | None") -> None:
    """Show a modal "Smart Citizen crashed" dialog pointing at *crash_path*.

    Safe to call from any state: degrades to a silent no-op when Qt or
    pyperclip is unavailable or no QApplication exists (e.g. an import-time
    crash before the GUI is constructed).
    """
    try:
        from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout
        from PyQt6.QtCore import Qt
        import pyperclip
    except ImportError:
        return

    if QApplication.instance() is None:
        return

    msg = f"{exc_type.__name__}: {exc_value}"
    path_str = str(crash_path) if crash_path else "(could not write crash log)"

    dlg = QDialog()
    dlg.setWindowTitle("Smart Citizen — Unexpected Error")
    dlg.setMinimumWidth(520)

    layout = QVBoxLayout(dlg)

    header = QLabel(
        "<b>Smart Citizen encountered an unexpected error and needs to close.</b><br>"
        "A crash report has been saved — please include it when reporting a bug."
    )
    header.setWordWrap(True)
    layout.addWidget(header)

    detail = QTextEdit()
    detail.setReadOnly(True)
    detail.setPlainText(msg)
    detail.setMaximumHeight(80)
    layout.addWidget(detail)

    path_label = QLabel(f"Crash log: <tt>{path_str}</tt>")
    path_label.setWordWrap(True)
    path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(path_label)

    btn_row = QHBoxLayout()
    btn_row.addStretch()

    copy_btn = QPushButton("Copy path")
    copy_btn.clicked.connect(lambda: pyperclip.copy(path_str))
    btn_row.addWidget(copy_btn)

    close_btn = QPushButton("Close")
    close_btn.setDefault(True)
    close_btn.clicked.connect(dlg.accept)
    btn_row.addWidget(close_btn)

    layout.addLayout(btn_row)
    dlg.exec()
