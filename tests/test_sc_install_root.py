"""Unit tests for AppSettings.get_sc_install_root cross-check logic.

When SC_INSTALL_ROOT and GAME_INSTALL_PATH disagree (stale root from a
pre-1.4.2 installer), GAME_INSTALL_PATH wins. The comparison uses
os.path.normcase so drive-letter casing differences on Windows don't
cause spurious mismatches.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from src.utils.json_settings import JsonSettings  # noqa: E402
from src.utils.settings import AppSettings  # noqa: E402

pytestmark = pytest.mark.unit


@pytest.fixture
def json_backend(tmp_path, monkeypatch):
    """Swap AppSettings._backend for a tmp JsonSettings so each test is hermetic."""
    saved = AppSettings._backend
    AppSettings._backend = JsonSettings(tmp_path / "config.json")
    yield AppSettings._backend
    AppSettings._backend = saved


class TestInstallRootCrossCheck:
    def test_matching_root_returns_unchanged(self, json_backend):
        """SC_INSTALL_ROOT matches GAME_INSTALL_PATH parent -- returns as-is."""
        root = r"D:\Games\StarCitizen"
        game_path = r"D:\Games\StarCitizen\LIVE"
        json_backend.setValue(AppSettings.SC_INSTALL_ROOT, root)
        json_backend.setValue(AppSettings.GAME_INSTALL_PATH, game_path)

        result = AppSettings.get_sc_install_root()
        assert os.path.normcase(result) == os.path.normcase(root)

    def test_disagreeing_root_derives_from_game_path(self, json_backend):
        """SC_INSTALL_ROOT disagrees with GAME_INSTALL_PATH -- derives from game path."""
        stale_root = r"C:\OldLocation\StarCitizen"
        game_path = r"D:\NewLocation\StarCitizen\LIVE"
        json_backend.setValue(AppSettings.SC_INSTALL_ROOT, stale_root)
        json_backend.setValue(AppSettings.GAME_INSTALL_PATH, game_path)

        result = AppSettings.get_sc_install_root()
        expected = r"D:\NewLocation\StarCitizen"
        assert os.path.normcase(result) == os.path.normcase(expected)

    def test_only_sc_install_root_set(self, json_backend):
        """Only SC_INSTALL_ROOT set (no GAME_INSTALL_PATH) -- returns SC_INSTALL_ROOT."""
        root = r"E:\RSI\StarCitizen"
        json_backend.setValue(AppSettings.SC_INSTALL_ROOT, root)
        # GAME_INSTALL_PATH not set (defaults to "")

        result = AppSettings.get_sc_install_root()
        assert result == root

    def test_neither_set_falls_through(self, json_backend, monkeypatch):
        """Neither setting set -- falls through to auto-detection.

        We monkeypatch Path.exists to return False for the standard
        install locations so the method returns empty string.
        """
        # Ensure neither key is set
        json_backend.remove(AppSettings.SC_INSTALL_ROOT)
        json_backend.remove(AppSettings.GAME_INSTALL_PATH)

        # Block the filesystem auto-detection candidates
        original_exists = Path.exists
        def _fake_exists(self):
            s = str(self)
            if "Roberts Space Industries" in s:
                return False
            return original_exists(self)
        monkeypatch.setattr(Path, "exists", _fake_exists)

        result = AppSettings.get_sc_install_root()
        assert result == ""

    def test_ptu_channel_recognized(self, json_backend):
        """GAME_INSTALL_PATH ending in PTU is recognized as a channel folder."""
        root = r"D:\Games\StarCitizen"
        game_path = r"D:\Games\StarCitizen\PTU"
        json_backend.setValue(AppSettings.SC_INSTALL_ROOT, root)
        json_backend.setValue(AppSettings.GAME_INSTALL_PATH, game_path)

        result = AppSettings.get_sc_install_root()
        assert os.path.normcase(result) == os.path.normcase(root)

    def test_disagreeing_ptu_path_overrides(self, json_backend):
        """Stale root + fresh PTU game path -- derives from PTU path."""
        stale_root = r"C:\Old\StarCitizen"
        game_path = r"D:\New\StarCitizen\PTU"
        json_backend.setValue(AppSettings.SC_INSTALL_ROOT, stale_root)
        json_backend.setValue(AppSettings.GAME_INSTALL_PATH, game_path)

        result = AppSettings.get_sc_install_root()
        expected = r"D:\New\StarCitizen"
        assert os.path.normcase(result) == os.path.normcase(expected)

    def test_game_path_without_channel_suffix_used_as_root(self, json_backend, monkeypatch):
        """GAME_INSTALL_PATH that doesn't end in a channel name is treated
        as the root itself when SC_INSTALL_ROOT is not set."""
        json_backend.remove(AppSettings.SC_INSTALL_ROOT)
        json_backend.setValue(AppSettings.GAME_INSTALL_PATH, r"D:\Games\StarCitizen")

        # Block filesystem auto-detection
        original_exists = Path.exists
        def _fake_exists(self):
            s = str(self)
            if "Roberts Space Industries" in s:
                return False
            return original_exists(self)
        monkeypatch.setattr(Path, "exists", _fake_exists)

        result = AppSettings.get_sc_install_root()
        assert result == r"D:\Games\StarCitizen"
