import hashlib
import json

from src.utils.package_integrity import MANIFEST_FILENAME, verify_portable_package


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_verified_package_passes(tmp_path):
    payload = tmp_path / "_internal" / "payload.bin"
    payload.parent.mkdir()
    payload.write_bytes(b"reviewed")
    (tmp_path / MANIFEST_FILENAME).write_text(json.dumps({"files": {
        "_internal/payload.bin": {"size": payload.stat().st_size, "sha256": _hash(payload)}
    }}), encoding="utf-8")
    result = verify_portable_package(tmp_path)
    assert result.ok
    assert result.files_checked == 1


def test_modified_package_file_is_rejected(tmp_path):
    payload = tmp_path / "app.exe"
    payload.write_bytes(b"original")
    (tmp_path / MANIFEST_FILENAME).write_text(json.dumps({"files": {
        "app.exe": {"size": len(b"original"), "sha256": _hash(payload)}
    }}), encoding="utf-8")
    payload.write_bytes(b"modified")
    result = verify_portable_package(tmp_path)
    assert not result.ok
    assert "hash changed" in result.message


def test_unlisted_package_file_is_rejected(tmp_path):
    payload = tmp_path / "app.exe"
    payload.write_bytes(b"reviewed")
    (tmp_path / MANIFEST_FILENAME).write_text(json.dumps({"files": {
        "app.exe": {"size": payload.stat().st_size, "sha256": _hash(payload)}
    }}), encoding="utf-8")
    (tmp_path / "unlisted.dll").write_bytes(b"not reviewed")

    result = verify_portable_package(tmp_path)

    assert not result.ok
    assert "Unexpected unverified" in result.message


def test_player_data_is_allowed_outside_the_manifest(tmp_path):
    payload = tmp_path / "app.exe"
    payload.write_bytes(b"reviewed")
    (tmp_path / MANIFEST_FILENAME).write_text(json.dumps({"files": {
        "app.exe": {"size": payload.stat().st_size, "sha256": _hash(payload)}
    }}), encoding="utf-8")
    user_ini = tmp_path / "data" / "LIVE" / "user.ini"
    user_ini.parent.mkdir(parents=True)
    user_ini.write_text("player setting")

    assert verify_portable_package(tmp_path).ok
