"""Tests for ``ErrorDialogHandler`` — the bridge between Python logging
and the user-facing modal in ``MainWindow``.

The handler itself is pure logic (level filter + signal emit) and can be
tested without a Qt event loop by mocking the emitter. The actual dialog
behaviour (cooldown, suppressed-count message, "Show Log" button) lives
on ``MainWindow._show_error_dialog`` and requires ``pytest-qt`` to drive,
which isn't currently a dev dependency — those interactions are covered
by the manual smoke checklist instead. What we lock here is the
contract every dialog-show path depends on:

  * INFO/WARNING records do NOT trigger a signal — only ERROR and
    CRITICAL do.
  * The signal payload's first element is the formatted message body.
  * The signal payload's second element is the formatted traceback when
    ``exc_info`` is present, empty string otherwise.
  * Handler errors are swallowed (defer to ``handleError``) so a misuse
    of the dialog channel can never recurse into itself.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from src.gui.error_dialog import ErrorDialogHandler

pytestmark = pytest.mark.unit


def _make_record(
    level: int,
    msg: str = "test message",
    args: tuple | None = None,
    exc_info=None,
) -> logging.LogRecord:
    return logging.LogRecord(
        name="test.module",
        level=level,
        pathname="test.py",
        lineno=1,
        msg=msg,
        args=args,
        exc_info=exc_info,
    )


@pytest.fixture
def emitter():
    """A stand-in for the Qt signal emitter. The handler only calls
    ``.error_emitted.emit(...)`` on its emitter, so a MagicMock with the
    right attribute path is sufficient and avoids needing a QApplication."""
    m = MagicMock()
    m.error_emitted = MagicMock()
    return m


@pytest.fixture
def handler(emitter):
    return ErrorDialogHandler(emitter)


class TestLevelFilter:
    """The handler's ``setLevel(logging.ERROR)`` is gated by
    ``Logger.callHandlers`` — records below ERROR never reach the
    handler at all, so the test must route through a real logger to
    exercise the actual production path.
    """

    @pytest.mark.parametrize(
        "level_call",
        [
            ("debug", logging.DEBUG),
            ("info", logging.INFO),
            ("warning", logging.WARNING),
        ],
    )
    def test_records_below_error_are_filtered_out(self, handler, emitter, level_call):
        """Critical guard: WARNING is dropped — this codebase logs
        WARNINGs routinely (patch targets missing, lookup misses, etc.)
        and they would flood the user with dialogs if surfaced."""
        method_name, _level = level_call
        logger = logging.getLogger(f"test.dialog.filter.{method_name}")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)  # let the logger forward everything; handler still filters at ERROR
        try:
            getattr(logger, method_name)("should not fire")
            emitter.error_emitted.emit.assert_not_called()
        finally:
            logger.removeHandler(handler)

    @pytest.mark.parametrize(
        "method_name",
        ["error", "critical"],
    )
    def test_error_and_critical_records_fire_signal(self, handler, emitter, method_name):
        logger = logging.getLogger(f"test.dialog.fire.{method_name}")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        try:
            getattr(logger, method_name)("something broke")
            emitter.error_emitted.emit.assert_called_once()
        finally:
            logger.removeHandler(handler)


class TestSignalPayload:
    def test_message_is_first_arg(self, handler, emitter):
        record = _make_record(logging.ERROR, msg="something broke")
        handler.handle(record)
        args, _ = emitter.error_emitted.emit.call_args
        assert args[0] == "something broke"

    def test_message_supports_formatting_args(self, handler, emitter):
        record = _make_record(logging.ERROR, msg="value=%s code=%d", args=("foo", 42))
        handler.handle(record)
        args, _ = emitter.error_emitted.emit.call_args
        assert args[0] == "value=foo code=42"

    def test_traceback_is_empty_when_no_exc_info(self, handler, emitter):
        record = _make_record(logging.ERROR)
        handler.handle(record)
        args, _ = emitter.error_emitted.emit.call_args
        assert args[1] == "", (
            "Second payload arg must be empty string when exc_info is None — "
            "the dialog conditions 'Show Details' on this being non-empty."
        )

    def test_traceback_is_populated_when_exc_info_provided(self, handler, emitter):
        """Equivalent to ``logger.error("...", exc_info=True)`` or
        ``logger.exception(...)`` — both common in this codebase. The
        handler must serialise the traceback so the dialog can offer a
        Show Details expand."""
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            import sys
            exc_info = sys.exc_info()

        record = _make_record(logging.ERROR, msg="failed to do thing", exc_info=exc_info)
        handler.handle(record)
        args, _ = emitter.error_emitted.emit.call_args
        tb_text = args[1]
        assert "RuntimeError" in tb_text
        assert "boom" in tb_text
        assert "Traceback" in tb_text


class TestErrorIsolation:
    def test_emit_exceptions_do_not_propagate(self, handler):
        """If the emitter itself throws (signal disconnected, slot raised),
        the handler must swallow the error rather than letting it bubble
        up. Otherwise a logging call would raise and the original error
        would mask under a handler bug — and worse, a logger.error in
        ``handleError`` would feed back into this handler, infinite-loop."""
        handler._emitter.error_emitted.emit.side_effect = RuntimeError("emitter broken")
        record = _make_record(logging.ERROR)
        # Should NOT raise.
        handler.handle(record)


class TestLoggerIntegration:
    """End-to-end: install the handler on a logger, fire records, observe
    the signal payload. This is the path real code takes."""

    def test_logger_error_with_string_fires_signal(self, handler, emitter):
        logger = logging.getLogger("test.dialog.string")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)  # ensure the LOGGER lets the record through; handler still filters at ERROR
        try:
            logger.error("a simple error")
            args, _ = emitter.error_emitted.emit.call_args
            assert args[0] == "a simple error"
            assert args[1] == ""
        finally:
            logger.removeHandler(handler)

    def test_logger_exception_fires_signal_with_traceback(self, handler, emitter):
        logger = logging.getLogger("test.dialog.exception")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        try:
            try:
                raise ValueError("structural")
            except ValueError:
                logger.exception("operation failed")
            args, _ = emitter.error_emitted.emit.call_args
            assert args[0] == "operation failed"
            assert "ValueError" in args[1]
            assert "structural" in args[1]
        finally:
            logger.removeHandler(handler)

    def test_logger_warning_does_not_fire_signal(self, handler, emitter):
        logger = logging.getLogger("test.dialog.warning")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        try:
            logger.warning("just a warning")
            emitter.error_emitted.emit.assert_not_called()
        finally:
            logger.removeHandler(handler)
