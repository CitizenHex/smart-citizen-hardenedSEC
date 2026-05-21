"""User-facing error-dialog handler.

Bridges Python's ``logging.ERROR`` / ``CRITICAL`` records to a Qt modal so
end users see when something went wrong rather than having to open the
Log tab to discover it. Mirrors the pattern in ``log_tab.py``: a
``logging.Handler`` posts records through a ``QObject`` signal so the
dialog construction always runs on the main thread — workers can fire
``logger.error`` freely and the dialog still serialises correctly.

Spam protection lives on the slot side (a short cooldown after each
shown dialog) rather than here, so the handler stays a stateless,
fully-formatted-line transport. See ``MainWindow._show_error_dialog``
for the cooldown + "N suppressed" coalescing behaviour.
"""
from __future__ import annotations

import logging
import traceback as tb_module

from PyQt6.QtCore import QObject, pyqtSignal


class _ErrorDialogEmitter(QObject):
    """Thread-safe bridge from ``logging`` records to the main thread.

    The signal carries two strings — a short one-line message body and an
    optional multi-line traceback (empty string when the record had no
    ``exc_info``). Two separate fields rather than one combined blob so
    the dialog can render the body prominently and tuck the traceback
    behind a "Show Details" toggle.
    """

    error_emitted = pyqtSignal(str, str)  # (message, traceback_or_empty)


class ErrorDialogHandler(logging.Handler):
    """logging.Handler that forwards ERROR/CRITICAL records to a dialog
    signal. The ``setLevel(logging.ERROR)`` call in ``__init__`` is what
    causes ``Logger.callHandlers`` to skip this handler entirely for
    INFO/WARNING records — the gate lives at the logger level, not on
    the handler's emit path.
    """

    def __init__(self, emitter: _ErrorDialogEmitter):
        super().__init__(level=logging.ERROR)
        self._emitter = emitter

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Use ``record.getMessage()`` rather than ``self.format(record)``
            # because the default ``Formatter.format`` auto-appends the
            # ``exc_info`` traceback to the message string — and we want
            # the two as SEPARATE signal-payload slots so the dialog can
            # show a short body up top and tuck the traceback behind a
            # "Show Details" toggle. ``getMessage()`` returns the
            # ``msg % args`` substitution only, no formatter framing.
            message = record.getMessage()
            # ``exc_info`` is set when callers use ``logger.error(...,
            # exc_info=True)`` or ``logger.exception(...)`` — both common
            # in this codebase. Format the traceback explicitly so the
            # dialog can offer a "Show Details" expand.
            tb_text = ""
            if record.exc_info:
                tb_text = "".join(tb_module.format_exception(*record.exc_info))
            self._emitter.error_emitted.emit(message, tb_text)
        except Exception:
            # Logging handler exceptions must never bubble — they'd cause
            # an infinite loop (handler error → emit log → handler emit
            # error → ...). Defer to handleError which prints to stderr
            # and stays out of the way.
            self.handleError(record)
