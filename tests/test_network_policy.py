"""Offline Security Mode fail-closed network policy."""
import logging
import socket

import pytest

from src.utils import network_policy

pytestmark = pytest.mark.unit


def test_locked_policy_blocks_and_logs(monkeypatch, caplog):
    monkeypatch.setattr(network_policy, "is_network_locked", lambda: True)
    with caplog.at_level(logging.WARNING), pytest.raises(
        network_policy.NetworkBlockedError, match="example.test"
    ):
        network_policy.require_network_allowed(
            "language download", "https://example.test/global.ini"
        )
    assert "OFFLINE SECURITY MODE blocked" in caplog.text


def test_unlocked_policy_allows(monkeypatch):
    monkeypatch.setattr(network_policy, "is_network_locked", lambda: False)
    network_policy.require_network_allowed(
        "language download", "https://example.test/global.ini"
    )


def test_downloader_is_blocked_before_urlopen(tmp_path, monkeypatch):
    from src.utils import updater

    monkeypatch.setattr(network_policy, "is_network_locked", lambda: True)
    monkeypatch.setattr(
        updater,
        "urlopen",
        lambda *args, **kwargs: pytest.fail("network should not be reached"),
    )
    with pytest.raises(network_policy.NetworkBlockedError):
        updater.download_file_if_changed(
            "https://ini.42kit.com/full/global.ini", tmp_path / "base.ini"
        )


def test_installed_guard_blocks_dns_and_udp(monkeypatch):
    monkeypatch.setattr(network_policy, "is_network_locked", lambda: True)
    network_policy.install_network_guard()
    try:
        with pytest.raises(network_policy.NetworkBlockedError):
            socket.getaddrinfo("example.test", 443)
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            with pytest.raises(network_policy.NetworkBlockedError):
                udp.sendto(b"test", ("127.0.0.1", 9))
        finally:
            udp.close()
    finally:
        socket.socket.connect = network_policy._original_connect
        socket.socket.connect_ex = network_policy._original_connect_ex
        socket.create_connection = network_policy._original_create_connection
        socket.getaddrinfo = network_policy._original_getaddrinfo
        socket.socket.sendto = network_policy._original_sendto
        network_policy._guard_installed = False
