"""Crash logger — catches unhandled exceptions, writes a report, and shows a dialog."""
import logging
import os
import platform
import sys
import traceback
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_MAX_CRASH_LOGS = 10

_original_excepthook = sys.excepthook


def get_crash_log_dir() -> Path:
    """Return the crash log directory, creating it if needed.

    Mirrors the DataForge cache convention: AppData\\Local\\Osiris DevWorks\\Smart Citizen\\logs\\
    so crash files stay out of OneDrive / Documents.
    """
    local_appdata = Path(
        os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
    )
    crash_dir = local_appdata / "Osiris DevWorks" / "Smart Citizen" / "logs"
    crash_dir.mkdir(parents=True, exist_ok=True)
    return crash_dir


def _prune_old_logs(crash_dir: Path) -> None:
    logs = sorted(crash_dir.glob("crash_*.log"), key=lambda p: p.stat().st_mtime)
    for old in logs[:-_MAX_CRASH_LOGS]:
        try:
            old.unlink()
        except OSError as exc:
            logger.warning(f"Could not prune old crash log {old}: {exc}")


def _write_crash_report(exc_type, exc_value, exc_tb) -> Path | None:
    try:
        from src.utils.version import get_version
        version = get_version()
    except Exception:
        version = "unknown"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    crash_dir = get_crash_log_dir()
    crash_path = crash_dir / f"crash_{timestamp}.log"

    lines = [
        "=" * 72,
        f"Smart Citizen v{version} — Crash Report",
        f"Time       : {datetime.now().isoformat(sep=' ', timespec='seconds')}",
        f"OS         : {platform.platform()}",
        f"Python     : {sys.version}",
        f"Executable : {sys.executable}",
        "=" * 72,
        "",
        "Traceback (most recent call last):",
    ]
    lines += traceback.format_tb(exc_tb)
    lines += [
        f"{exc_type.__name__}: {exc_value}",
        "",
        "=" * 72,
    ]

    report = "\n".join(lines)
    try:
        crash_path.write_text(report, encoding="utf-8")
        _prune_old_logs(crash_dir)
        return crash_path
    except Exception:
        return None


def _show_crash_dialog(exc_type, exc_value, crash_path: Path | None) -> None:
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


def _excepthook(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        _original_excepthook(exc_type, exc_value, exc_tb)
        return

    logger.critical(
        "Unhandled exception",
        exc_info=(exc_type, exc_value, exc_tb),
    )

    crash_path = _write_crash_report(exc_type, exc_value, exc_tb)
    if crash_path:
        print(f"\nCrash log written to: {crash_path}", file=sys.stderr)
    else:
        print("\nCould not write crash log.", file=sys.stderr)

    _show_crash_dialog(exc_type, exc_value, crash_path)
    _original_excepthook(exc_type, exc_value, exc_tb)


def install() -> None:
    """Install the crash logger. Call once, early in main(), before Qt starts."""
    sys.excepthook = _excepthook
    logger.debug("Crash logger installed")
