from src.utils.import_safety import MAX_INI_IMPORT_BYTES, validate_ini_import

import pytest


def test_ini_import_accepts_small_local_file(tmp_path):
    source = tmp_path / "settings.ini"
    source.write_text("key=value\n", encoding="utf-8")
    assert validate_ini_import(source) == source


def test_ini_import_rejects_oversized_file(tmp_path):
    source = tmp_path / "oversized.ini"
    source.write_bytes(b"x" * (MAX_INI_IMPORT_BYTES + 1))
    with pytest.raises(ValueError, match="too large"):
        validate_ini_import(source)
