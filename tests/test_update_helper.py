import zipfile

import pytest

from src.update_helper import safe_extract, sha256_file


def test_safe_extract_rejects_path_traversal(tmp_path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("../outside.txt", "no")
    with pytest.raises(ValueError):
        safe_extract(archive, tmp_path / "stage")


def test_safe_extract_writes_normal_package_file(tmp_path):
    archive = tmp_path / "good.zip"
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("app.exe", "reviewed")
    stage = tmp_path / "stage"
    safe_extract(archive, stage)
    assert (stage / "app.exe").read_text() == "reviewed"


def test_sha256_file_is_stable(tmp_path):
    path = tmp_path / "package.zip"
    path.write_bytes(b"reviewed")
    assert sha256_file(path) == "e4f934f321eb76c9bf8b5103e0a0d9afe72d6e62ace3d3ea849790619bf7487a"
