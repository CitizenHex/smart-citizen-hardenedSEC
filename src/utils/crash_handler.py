"""Crash handler — dump traceback + recent log buffer when the app dies unexpectedly.

The frozen PyInstaller build runs without a console window, so anything Python
prints to stderr (including the default tracebacks for uncaught exceptions) is
invisible to end users. Without this module a user who hits a crash sees the
window vanish with no diagnostic trail and no way to file a useful bug report.

What this module does:

* Installs an independent in-memory ring buffer ``logging.Handler`` so the
  crash hook has access to recent log lines even when the GUI's LogTab buffer
  is unreachable (the GUI may be the thing that crashed).
* Wraps ``sys.excepthook`` (uncaught exceptions on the main thread) and
  ``threading.excepthook`` (uncaught exceptions in worker threads, including
  ``QThread`` subclasses) so a crash dump is written before the default hook
  runs.
* Dumps the traceback plus the ring-buffer contents to
  ``{logs_dir}/crash_YYYYMMDD_HHMMSS.log`` and then calls through to the
  original hook — preserving the default-stderr behavior so dev runs still
  see tracebacks at the console.

Idempotent: calling ``install_crash_handler`` twice is a no-op on the second
call so re-entry (e.g. from a worker that imports the module) doesn't chain
hooks.
"""
from __future__ import annotations

import logging
import sys
import threading
import traceback
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Callable, Deque, Optional

logger = logging.getLogger(__name__)

# Tunable — 5,000 formatted lines is ~500 KB at typical log-line widths and
# covers ~10 minutes of normal operation, which is plenty of context for
# crash triage without writing huge dump files.
_RING_BUFFER_MAXLEN = 5000


class _RingBufferHandler(logging.Handler):
    """Bounded in-memory ring buffer of formatted log lines.

    The crash hook reads from this buffer when writing a crash dump file.
    Independent of the GUI's LogTab handler so the dump still works when the
    GUI is the thing that crashed.
    """

    def __init__(self, maxlen: int = _RING_BUFFER_MAXLEN):
        super().__init__()
        self.buffer: Deque[str] = deque(maxlen=maxlen)
        # Match main.py's basicConfig format so on-disk dumps read identically
        # to whatever the user saw in stdout while the app was alive.
        self.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.buffer.append(self.format(record))
        except Exception:
            self.handleError(record)

    def snapshot(self) -> list[str]:
        """Return a stable copy of the buffer for crash-dump writers."""
        return list(self.buffer)


# Module-level state. The hook installer mutates these on first call and
# refuses to chain hooks on subsequent calls — re-entrancy guard.
_buffer_handler: Optional[_RingBufferHandler] = None
_original_excepthook: Optional[Callable] = None
_original_threading_excepthook: Optional[Callable] = None
_installed = False


def install_crash_handler(logs_dir: Path) -> None:
    """Install the ring-buffer log handler + ``sys.excepthook`` + threading hook.

    Safe to call multiple times — only the first invocation wires anything up.
    The ``logs_dir`` argument is captured at install time; the crash hook
    creates the directory on first use (idempotent ``mkdir(parents=True,
    exist_ok=True)``) so a fresh install doesn't carry an empty ``logs/``
    until the first crash.
    """
    global _buffer_handler, _original_excepthook, _original_threading_excepthook, _installed
    if _installed:
        return
    _installed = True

    _buffer_handler = _RingBufferHandler()
    logging.getLogger().addHandler(_buffer_handler)

    _original_excepthook = sys.excepthook
    _original_threading_excepthook = threading.excepthook

    sys.excepthook = _make_main_thread_hook(logs_dir, _original_excepthook)
    threading.excepthook = _make_thread_hook(logs_dir, _original_threading_excepthook)


def _write_crash_dump(
    logs_dir: Path,
    exc_type: type,
    exc_value: BaseException,
    exc_tb,
    thread_name: str = "MainThread",
) -> Optional[Path]:
    """Write a timestamped crash file. Returns the path on success, None on failure.

    Failure modes are swallowed deliberately — a write error inside the crash
    handler must NOT mask the real exception. We log the write error but
    continue so the original excepthook still runs.
    """
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dump_path = logs_dir / f"crash_{stamp}.log"

        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        buffer_lines = _buffer_handler.snapshot() if _buffer_handler is not None else []

        with dump_path.open("w", encoding="utf-8") as f:
            f.write(f"Smart Citizen crash dump — {stamp}\n")
            f.write(f"Thread: {thread_name}\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"Platform: {sys.platform}\n")
            f.write("\n")
            f.write("─── Traceback ────────────────────────────────────────────────\n")
            f.write(tb_text)
            f.write("\n")
            f.write(f"─── Recent log buffer ({len(buffer_lines)} lines) ─────────────\n")
            for line in buffer_lines:
                f.write(line + "\n")
        return dump_path
    except Exception as write_err:
        # Don't raise — we're already in a crash path and the original hook
        # still needs to run. Best-effort logging only.
        try:
            logger.error(f"Failed to write crash dump: {write_err}")
        except Exception:
            pass
        return None


def _make_main_thread_hook(logs_dir: Path, original):
    def hook(exc_type, exc_value, exc_tb):
        # KeyboardInterrupt should pass straight through — Ctrl+C in dev runs
        # isn't a crash, and writing a dump file for it is noisy.
        if issubclass(exc_type, KeyboardInterrupt):
            if original is not None:
                original(exc_type, exc_value, exc_tb)
            return
        crash_path = _write_crash_dump(logs_dir, exc_type, exc_value, exc_tb, "MainThread")
        try:
            from src.utils.crash_logger import show_crash_dialog
            show_crash_dialog(exc_type, exc_value, crash_path)
        except Exception as dlg_err:
            # The dump is already written; don't let a broken crash-dialog
            # module hide that from the user entirely.
            try:
                logger.error(f"crash_logger unavailable, crash dialog suppressed: {dlg_err}")
            except Exception:
                pass
        if original is not None:
            original(exc_type, exc_value, exc_tb)
    return hook


def _make_thread_hook(logs_dir: Path, original):
    def hook(args):
        # ``args`` is a ``threading.ExceptHookArgs`` namedtuple-like with
        # fields: exc_type, exc_value, exc_traceback, thread.
        if issubclass(args.exc_type, SystemExit):
            if original is not None:
                original(args)
            return
        thread_name = args.thread.name if args.thread is not None else "UnknownThread"
        _write_crash_dump(
            logs_dir, args.exc_type, args.exc_value, args.exc_traceback, thread_name
        )
        if original is not None:
            original(args)
    return hook
