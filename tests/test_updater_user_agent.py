"""download_file_if_changed sends an explicit User-Agent (#300).

Some source hosts (ini.42kit.com, the Chinese base.ini source) reject
urllib's default "Python-urllib/x.y" agent with a 403, so every request
must carry the SmartCitizen UA. Locks the header on both request shapes:
the fresh download and the If-Modified-Since conditional re-check.
"""
import io

import pytest

from src.utils import updater
from src.utils.version import get_version

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _network_unlocked(monkeypatch):
    """These tests exercise the downloader after the policy gate."""
    monkeypatch.setattr(updater, "require_network_allowed", lambda *args: None)


class _Response(io.BytesIO):
    """Minimal urlopen context-manager stand-in."""

    headers = {}

    def geturl(self):
        return "https://ini.42kit.com/full/global.ini"

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _capture_urlopen(captured):
    def fake_urlopen(req, timeout=None):
        captured.append(req)
        return _Response(b"key=value\n")

    return fake_urlopen


def test_fresh_download_sends_smartcitizen_user_agent(tmp_path, monkeypatch):
    captured = []
    monkeypatch.setattr(updater, "urlopen", _capture_urlopen(captured))
    target = tmp_path / "base.ini"

    assert updater.download_file_if_changed("https://ini.42kit.com/full/global.ini", target)

    (req,) = captured
    assert req.get_header("User-agent") == f"SmartCitizen/{get_version()}"
    assert target.read_bytes() == b"key=value\n"


def test_conditional_recheck_keeps_user_agent(tmp_path, monkeypatch):
    captured = []
    monkeypatch.setattr(updater, "urlopen", _capture_urlopen(captured))
    target = tmp_path / "base.ini"
    target.write_bytes(b"old\n")

    updater.download_file_if_changed("https://ini.42kit.com/full/global.ini", target)

    (req,) = captured
    assert req.get_header("User-agent") == f"SmartCitizen/{get_version()}"
    assert req.get_header("If-modified-since") is not None


def test_rejects_unapproved_source_before_network_access(tmp_path, monkeypatch):
    monkeypatch.setattr(
        updater,
        "urlopen",
        lambda *args, **kwargs: pytest.fail("network should not be reached"),
    )
    with pytest.raises(ValueError, match="not allowlisted"):
        updater.download_file_if_changed(
            "https://example.test/global.ini", tmp_path / "base.ini"
        )


def test_invalid_payload_does_not_replace_existing_cache(tmp_path, monkeypatch):
    target = tmp_path / "base.ini"
    target.write_bytes(b"trusted=old\n")

    def invalid_response(*args, **kwargs):
        return _Response(b"<html>not an ini</html>")

    monkeypatch.setattr(updater, "urlopen", invalid_response)
    with pytest.raises(ValueError, match="not a localization INI"):
        updater.download_file_if_changed(
            "https://ini.42kit.com/full/global.ini", target
        )
    assert target.read_bytes() == b"trusted=old\n"
