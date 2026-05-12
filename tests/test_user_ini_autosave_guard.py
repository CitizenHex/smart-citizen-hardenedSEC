"""Regression guard for the close-time user.ini autosave.

v1.3.0 shipped a path where ``MainWindow.closeEvent`` unconditionally wrote
``user.ini`` from the in-memory entry list. When a load mismatch (channel
drift after migration, transient I/O) left every entry with an empty
``custom_value``, the close write truncated a populated ``user.ini`` to
0 bytes — silent data loss. ``should_autosave_user_ini`` is the guard
that decides whether the write is safe.
"""

import pytest

from src.models.string_model import StringEntry
from src.utils.user_ini_manager import should_autosave_user_ini


def _entry(key: str, original: str, custom: str) -> StringEntry:
    return StringEntry(
        key=key,
        source_file="global",
        category="Other",
        original_value=original,
        custom_value=custom,
        status="Modified" if custom and custom != original else "Unmodified",
    )


class TestShouldAutosaveUserIni:
    @pytest.mark.regression
    def test_refuses_to_truncate_populated_user_ini_when_no_modifications(self, tmp_path):
        """The exact 1.3.0 bug: load mismatch leaves entries unmodified,
        existing user.ini has content, autosave would clobber it."""
        user_ini = tmp_path / "user.ini"
        user_ini.write_text("vehicle_NameHunter=Custom Hunter\n", encoding="utf-8")
        entries = [_entry("vehicle_NameHunter", "Stock Hunter", "")]

        assert should_autosave_user_ini(entries, user_ini) is False
        # Caller would skip the write, file content is preserved
        assert user_ini.read_text(encoding="utf-8") == "vehicle_NameHunter=Custom Hunter\n"

    def test_permits_write_when_any_entry_is_modified(self, tmp_path):
        user_ini = tmp_path / "user.ini"
        user_ini.write_text("old=value\n", encoding="utf-8")
        entries = [
            _entry("a", "stock_a", ""),
            _entry("b", "stock_b", "user_edit_b"),
        ]

        assert should_autosave_user_ini(entries, user_ini) is True

    def test_permits_write_when_user_ini_missing(self, tmp_path):
        user_ini = tmp_path / "user.ini"
        entries = [_entry("a", "stock_a", "")]

        assert should_autosave_user_ini(entries, user_ini) is True

    def test_permits_write_when_existing_user_ini_is_empty(self, tmp_path):
        user_ini = tmp_path / "user.ini"
        user_ini.touch()
        entries = [_entry("a", "stock_a", "")]

        assert should_autosave_user_ini(entries, user_ini) is True

    def test_handles_empty_entries_list(self, tmp_path):
        user_ini = tmp_path / "user.ini"
        user_ini.write_text("k=v\n", encoding="utf-8")

        assert should_autosave_user_ini([], user_ini) is False

    def test_custom_equals_original_is_not_treated_as_modified(self, tmp_path):
        """``is_modified`` requires custom != original; a no-op edit
        shouldn't satisfy the guard. Otherwise loading a user.ini whose
        values match stock would still permit a clobber of a different
        on-disk user.ini."""
        user_ini = tmp_path / "user.ini"
        user_ini.write_text("k=existing\n", encoding="utf-8")
        entries = [_entry("k", "same", "same")]

        assert should_autosave_user_ini(entries, user_ini) is False
