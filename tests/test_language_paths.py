"""Per-language cache paths, enhancement stamps, and base.ini URL resolution
(src/utils/settings.py language layer, 2.0 #30).

These helpers decide where files land on disk and whether a language switch
regenerates enhancements, so the layout is locked here:

  * English base.ini stays at the channel cache root; every other language
    caches under ``cache/lang/{language}/`` (created on demand).
  * Enhancements always live next to the base.ini they were generated from
    (``get_enhancements_dir`` is just the base.ini's parent).
  * The ``.dataforge_stamp`` marker round-trips per language and is isolated
    between languages — French's stamp must not satisfy Portuguese's check.
  * ``get_language_base_url`` resolves user override first, then the bundled
    sources.json map, then ''.
  * ``get_sc_language_id`` maps app folder names to SC identifiers and falls
    back to the raw name for unknown languages.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from src.utils import settings as settings_module  # noqa: E402
from src.utils.json_settings import JsonSettings  # noqa: E402
from src.utils.settings import AppSettings  # noqa: E402

pytestmark = pytest.mark.unit


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Hermetic settings: tmp cache dir + tmp JsonSettings backend."""
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setattr(AppSettings, "get_cache_dir", staticmethod(lambda: cache))
    saved = AppSettings._backend
    AppSettings._backend = JsonSettings(tmp_path / "config.json")
    yield cache
    AppSettings._backend = saved


class TestBaseIniPath:
    def test_english_uses_cache_root(self, env):
        assert AppSettings.get_base_ini_path("english") == env / "base.ini"

    def test_english_does_not_create_lang_dir(self, env):
        AppSettings.get_base_ini_path("english")
        assert not (env / "lang").exists()

    def test_non_english_nests_under_lang(self, env):
        path = AppSettings.get_base_ini_path("french")
        assert path == env / "lang" / "french" / "base.ini"

    def test_non_english_creates_parent_dir(self, env):
        path = AppSettings.get_base_ini_path("french")
        assert path.parent.is_dir()

    def test_default_argument_uses_selected_language(self, env, monkeypatch):
        monkeypatch.setattr(
            AppSettings, "get_selected_language", staticmethod(lambda: "french")
        )
        assert AppSettings.get_base_ini_path() == env / "lang" / "french" / "base.ini"


class TestEnhancementsDir:
    def test_is_base_ini_parent_for_english(self, env):
        assert AppSettings.get_enhancements_dir("english") == env

    def test_is_base_ini_parent_for_non_english(self, env):
        assert (
            AppSettings.get_enhancements_dir("portuguese_br")
            == env / "lang" / "portuguese_br"
        )


class TestEnhancementsStamp:
    def test_absent_stamp_reads_empty(self, env):
        assert AppSettings.get_enhancements_stamp("french") == ""

    def test_round_trip(self, env):
        AppSettings.set_enhancements_stamp("p4k-2024-key", "french")
        assert AppSettings.get_enhancements_stamp("french") == "p4k-2024-key"

    def test_stamps_are_per_language(self, env):
        AppSettings.set_enhancements_stamp("french-key", "french")
        assert AppSettings.get_enhancements_stamp("portuguese_br") == ""

    def test_stamp_file_lives_in_enhancements_dir(self, env):
        AppSettings.set_enhancements_stamp("k", "french")
        stamp = (
            AppSettings.get_enhancements_dir("french")
            / AppSettings.ENHANCEMENTS_STAMP_NAME
        )
        assert stamp.is_file()


class TestLanguageBaseUrl:
    def test_unset_and_unbundled_resolves_empty(self, env, monkeypatch):
        monkeypatch.setattr(settings_module, "_bundled_language_sources", lambda: {})
        assert AppSettings.get_language_base_url("french") == ""

    def test_bundled_map_is_the_fallback(self, env, monkeypatch):
        monkeypatch.setattr(
            settings_module,
            "_bundled_language_sources",
            lambda: {"french": "https://example.test/bundled.ini"},
        )
        assert (
            AppSettings.get_language_base_url("french")
            == "https://example.test/bundled.ini"
        )

    def test_user_override_wins_over_bundled(self, env, monkeypatch):
        monkeypatch.setattr(
            settings_module,
            "_bundled_language_sources",
            lambda: {"french": "https://example.test/bundled.ini"},
        )
        AppSettings.set_language_source_override(
            "french", "https://example.test/override.ini"
        )
        assert (
            AppSettings.get_language_base_url("french")
            == "https://example.test/override.ini"
        )

    def test_clearing_override_restores_bundled(self, env, monkeypatch):
        monkeypatch.setattr(
            settings_module,
            "_bundled_language_sources",
            lambda: {"french": "https://example.test/bundled.ini"},
        )
        AppSettings.set_language_source_override("french", "https://x.test/o.ini")
        AppSettings.set_language_source_override("french", "")
        assert (
            AppSettings.get_language_base_url("french")
            == "https://example.test/bundled.ini"
        )

    def test_overrides_are_per_language(self, env, monkeypatch):
        monkeypatch.setattr(settings_module, "_bundled_language_sources", lambda: {})
        AppSettings.set_language_source_override("french", "https://x.test/fr.ini")
        assert AppSettings.get_language_base_url("portuguese_br") == ""


class TestScLanguageId:
    def test_known_mapping(self):
        assert AppSettings.get_sc_language_id("portuguese_br") == "portuguese_(brazil)"
        assert AppSettings.get_sc_language_id("english") == "english"

    def test_unknown_language_falls_back_to_raw_name(self):
        assert AppSettings.get_sc_language_id("klingon") == "klingon"

    def test_default_argument_uses_selected_language(self, monkeypatch):
        monkeypatch.setattr(
            AppSettings, "get_selected_language", staticmethod(lambda: "french")
        )
        assert AppSettings.get_sc_language_id() == "french_(france)"
