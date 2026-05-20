"""Tests for the DataForge cache-directory split (1.4.1).

Pre-1.4.1 ``AppSettings.get_dataforge_cache_dir()`` was hard-pinned to
``%LOCALAPPDATA%\\Smart Citizen\\{channel}\\cache\\dataforge\\`` with no
way to redirect it. The motivation for LOCALAPPDATA was sound
(OneDrive churn on the ~1.4 GB / ~28k-file XML tree) but it ignored
two cases the user could reasonably control:

  * **Registry-mode override** — a user who has explicitly moved
    USER_DATA_DIR off OneDrive Documents has already opted out of
    OneDrive, but the cache stayed in LOCALAPPDATA regardless.
  * **Portable mode** — the whole point is everything-next-to-exe,
    but the cache still landed in LOCALAPPDATA, breaking relocatability.

The fix introduces a CACHE_DIR setting independent from USER_DATA_DIR
and routes ``get_dataforge_cache_dir`` through a base resolver that
checks override → portable → LOCALAPPDATA in that order. The historic
LOCALAPPDATA default is preserved so unchanged installs see no path
movement on upgrade. These tests lock the resolution order and the
override I/O contract.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from src.utils import build_mode  # noqa: E402
from src.utils.json_settings import JsonSettings  # noqa: E402
from src.utils.settings import AppSettings  # noqa: E402

pytestmark = pytest.mark.unit


@pytest.fixture
def json_backend(tmp_path, monkeypatch):
    """Use a tmp JsonSettings so each test gets a clean key-value store
    and never touches the real registry. Also pins the active channel so
    path comparisons are deterministic across machines."""
    saved = AppSettings._backend
    AppSettings._backend = JsonSettings(tmp_path / "config.json")
    monkeypatch.setattr(AppSettings, "get_active_channel", staticmethod(lambda: "LIVE"))
    yield AppSettings._backend
    AppSettings._backend = saved


@pytest.fixture
def registry_mode(monkeypatch):
    """Ensure build_mode.IS_PORTABLE is False for registry-mode tests.

    Patches via the dotted-string form so the attribute lookup happens
    at apply-time against ``sys.modules["src.utils.build_mode"]``. The
    module-level ``build_mode`` import above can go stale when
    test_build_info_fallback.py reloads the module via ``sys.modules.pop``
    — keying the patch by string instead avoids that staleness.
    """
    monkeypatch.setattr("src.utils.build_mode.IS_PORTABLE", False)


@pytest.fixture
def portable_mode(monkeypatch, tmp_path):
    """Flip IS_PORTABLE and pin _portable_data_dir to a tmp path so the
    next-to-exe resolution becomes hermetic. Dotted-string patch to
    survive test_build_info_fallback's sys.modules reload (see
    ``registry_mode`` for the same reason)."""
    monkeypatch.setattr("src.utils.build_mode.IS_PORTABLE", True)
    monkeypatch.setattr(
        AppSettings, "_portable_data_dir",
        staticmethod(lambda: tmp_path / "portable_data"),
    )


class TestOverrideIO:
    def test_get_returns_empty_when_unset(self, json_backend):
        assert AppSettings.get_cache_dir_override() == ""

    def test_set_then_get_roundtrips(self, json_backend, tmp_path):
        target = tmp_path / "my-cache"
        AppSettings.set_cache_dir(target)
        assert AppSettings.get_cache_dir_override() == str(target)

    def test_set_none_clears_override(self, json_backend, tmp_path):
        AppSettings.set_cache_dir(tmp_path / "x")
        AppSettings.set_cache_dir(None)
        assert AppSettings.get_cache_dir_override() == ""

    def test_set_empty_string_clears_override(self, json_backend, tmp_path):
        AppSettings.set_cache_dir(tmp_path / "x")
        AppSettings.set_cache_dir("")
        assert AppSettings.get_cache_dir_override() == ""

    def test_set_whitespace_only_clears_override(self, json_backend, tmp_path):
        """A user who blanks the input shouldn't end up with a literal
        whitespace path stored. Mirrors the user-data-dir guard."""
        AppSettings.set_cache_dir(tmp_path / "x")
        AppSettings.set_cache_dir("   ")
        assert AppSettings.get_cache_dir_override() == ""


class TestRegistryModeDefault:
    """No override + registry mode → unchanged %LOCALAPPDATA% path.

    Locks the back-compat contract: a user upgrading from 1.4.0 with no
    CACHE_DIR set must continue to read/write the same path so their
    existing 1.4 GB cache stays valid without re-extraction.
    """

    def test_default_uses_localappdata(self, json_backend, registry_mode, monkeypatch, tmp_path):
        fake_local = tmp_path / "LocalAppData"
        monkeypatch.setenv("LOCALAPPDATA", str(fake_local))
        path = AppSettings.get_dataforge_cache_dir()
        assert path == fake_local / "Smart Citizen" / "LIVE" / "cache" / "dataforge"
        assert path.exists(), "get_dataforge_cache_dir should mkdir on the leaf"

    def test_base_resolver_strips_channel(self, json_backend, registry_mode, monkeypatch, tmp_path):
        """get_dataforge_cache_base returns the *base* (no channel suffix)
        so the Config tab can show the user the "root" they configured
        rather than a per-channel leaf."""
        fake_local = tmp_path / "LocalAppData"
        monkeypatch.setenv("LOCALAPPDATA", str(fake_local))
        assert AppSettings.get_dataforge_cache_base() == fake_local / "Smart Citizen"


class TestRegistryModeOverride:
    def test_override_redirects_base(self, json_backend, registry_mode, tmp_path):
        target = tmp_path / "ssd-cache"
        AppSettings.set_cache_dir(target)
        assert AppSettings.get_dataforge_cache_base() == target.resolve()

    def test_override_preserves_channel_nesting(self, json_backend, registry_mode, tmp_path):
        target = tmp_path / "ssd-cache"
        AppSettings.set_cache_dir(target)
        path = AppSettings.get_dataforge_cache_dir()
        assert path == target.resolve() / "LIVE" / "cache" / "dataforge"

    def test_override_expands_env_vars(self, json_backend, registry_mode, monkeypatch, tmp_path):
        """%CUSTOM_VAR% in the override should expand at resolution time.
        Users pasting registry-style paths shouldn't be surprised by a
        literal '%' surviving."""
        target_root = tmp_path / "expanded-root"
        monkeypatch.setenv("MY_SC_CACHE", str(target_root))
        AppSettings.set_cache_dir("%MY_SC_CACHE%")
        assert AppSettings.get_dataforge_cache_base() == target_root.resolve()

    def test_override_independent_of_user_data_dir(self, json_backend, registry_mode, tmp_path):
        """The whole point of the split: setting one doesn't move the other."""
        user_data = tmp_path / "documents-sc"
        cache = tmp_path / "ssd-sc"
        AppSettings.set_user_data_dir(user_data)
        AppSettings.set_cache_dir(cache)
        assert AppSettings.get_user_data_dir() == user_data.resolve()
        assert AppSettings.get_dataforge_cache_base() == cache.resolve()


class TestPortableMode:
    def test_default_is_next_to_exe(self, json_backend, portable_mode, tmp_path):
        """Portable + no override = next to exe. This was the user-reported
        bug: pre-fix, portable builds still pointed at LOCALAPPDATA."""
        path = AppSettings.get_dataforge_cache_dir()
        # tmp_path/portable_data/cache/LIVE/cache/dataforge
        assert path == tmp_path / "portable_data" / "cache" / "LIVE" / "cache" / "dataforge"

    def test_override_wins_over_portable_default(self, json_backend, portable_mode, tmp_path):
        """Portable users still get the override option (e.g. cache off
        a slow USB stick onto a fast local SSD)."""
        target = tmp_path / "ssd-cache"
        AppSettings.set_cache_dir(target)
        assert AppSettings.get_dataforge_cache_base() == target.resolve()


class TestPendingCleanup:
    """When the user changes the cache path and opts to delete the old
    cache after re-extraction, the old path is stashed in a setting that
    MainWindow consumes after the next successful P4K extraction."""

    def test_get_returns_empty_when_unset(self, json_backend):
        assert AppSettings.get_pending_cache_cleanup() == ""

    def test_set_then_get_roundtrips(self, json_backend, tmp_path):
        AppSettings.set_pending_cache_cleanup(tmp_path / "old-cache")
        assert AppSettings.get_pending_cache_cleanup() == str(tmp_path / "old-cache")

    def test_set_none_clears(self, json_backend, tmp_path):
        AppSettings.set_pending_cache_cleanup(tmp_path / "old-cache")
        AppSettings.set_pending_cache_cleanup(None)
        assert AppSettings.get_pending_cache_cleanup() == ""

    def test_set_empty_string_clears(self, json_backend, tmp_path):
        AppSettings.set_pending_cache_cleanup(tmp_path / "old-cache")
        AppSettings.set_pending_cache_cleanup("")
        assert AppSettings.get_pending_cache_cleanup() == ""
