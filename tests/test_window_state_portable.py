"""Window geometry/state must round-trip through the portable (JsonSettings)
backend without crashing on close (issue #141).

QWidget.saveGeometry()/saveState() return a QByteArray. The registry backend
(QSettings) stores it natively, but the portable backend json.dumps its store
and a QByteArray is not JSON-serialisable, so storing it raw raised a
TypeError out of closeEvent and crashed the app on exit (portable build only).

AppSettings now base64-encodes geometry/state to text so both backends can
store it, and JsonSettings degrades a non-serialisable write to a warning
instead of raising.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PyQt6.QtCore import QByteArray

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Import via src.X so the backend swap matches the class production code uses.
from src.utils.json_settings import JsonSettings  # noqa: E402
from src.utils.settings import AppSettings  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.regression]

# Full byte range, including 0x00 and high bytes — exercises base64 on data
# that is neither ASCII nor null-free.
SAMPLE = bytes(range(256))


@pytest.fixture
def portable_settings(tmp_path):
    """Back AppSettings with a JsonSettings instance — the portable backend."""
    saved = AppSettings._backend
    AppSettings._backend = JsonSettings(tmp_path / "config.json")
    yield AppSettings._backend
    AppSettings._backend = saved


# ── round-trip through the portable backend ─────────────────────────────────

def test_geometry_roundtrip_portable(portable_settings):
    AppSettings.set_window_geometry(QByteArray(SAMPLE))   # must not raise
    assert AppSettings.get_window_geometry() == SAMPLE


def test_state_roundtrip_portable(portable_settings):
    AppSettings.set_window_state(QByteArray(SAMPLE))      # must not raise
    assert AppSettings.get_window_state() == SAMPLE


def test_persist_writes_valid_json(portable_settings, tmp_path):
    AppSettings.set_window_geometry(QByteArray(SAMPLE))
    # The store must be valid JSON with the geometry as base64 text — a raw
    # QByteArray would have broken json.dump (the #141 crash).
    data = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert isinstance(data[AppSettings.WINDOW_GEOMETRY], str)


def test_absent_geometry_is_falsy(portable_settings):
    # restore_window_state() guards with `if geometry:` — absent must be falsy.
    assert AppSettings.get_window_geometry() == b""
    assert AppSettings.get_window_state() == b""


# ── encode/decode helpers ────────────────────────────────────────────────────

def test_decode_handles_legacy_and_empty():
    # Legacy registry installs stored a raw QByteArray / bytes; still decodes.
    assert AppSettings._decode_qbytes(QByteArray(SAMPLE)) == SAMPLE
    assert AppSettings._decode_qbytes(SAMPLE) == SAMPLE
    # Absent / empty values come back as b"".
    assert AppSettings._decode_qbytes("") == b""
    assert AppSettings._decode_qbytes(None) == b""


def test_encode_empty_is_empty_string():
    assert AppSettings._encode_qbytes(QByteArray()) == ""
    assert AppSettings._encode_qbytes(b"") == ""


# ── JsonSettings safety net ──────────────────────────────────────────────────

def test_persist_does_not_crash_on_non_serializable(tmp_path):
    """A stray non-serialisable value must degrade to a warning, not crash —
    a write on close can never take the process down."""
    js = JsonSettings(tmp_path / "c.json")
    js.setValue("ok", "value")
    # Inject a QByteArray directly (bypassing AppSettings' encoding). Must not
    # raise; the earlier good value stays on disk.
    js.setValue("bad", QByteArray(b"\x00\x01\x02"))
    data = json.loads((tmp_path / "c.json").read_text(encoding="utf-8"))
    assert data["ok"] == "value"
