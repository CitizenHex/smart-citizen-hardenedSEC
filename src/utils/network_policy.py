"""Application-wide outbound network policy for the hardened build."""
from __future__ import annotations

import logging
import socket
from typing import Any

logger = logging.getLogger(__name__)


class NetworkBlockedError(PermissionError):
    """Raised when Offline Security Mode blocks an outbound connection."""


def is_network_locked() -> bool:
    """Return the persisted policy; fail closed if settings cannot be read."""
    try:
        from src.utils.settings import AppSettings
        return AppSettings.get_network_lock_enabled()
    except Exception as exc:  # pragma: no cover - defensive startup guard
        logger.error("Could not read network policy; defaulting to locked: %s", exc)
        return True


def require_network_allowed(operation: str, destination: Any = "") -> None:
    """Log and reject a network operation while the lock is enabled."""
    if not is_network_locked():
        return
    target = str(destination or "unspecified destination")
    logger.warning(
        "OFFLINE SECURITY MODE blocked network operation=%s destination=%s",
        operation,
        target,
    )
    raise NetworkBlockedError(
        f"Offline Security Mode blocked {operation} to {target}"
    )


_guard_installed = False
_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex
_original_create_connection = socket.create_connection
_original_getaddrinfo = socket.getaddrinfo
_original_sendto = socket.socket.sendto


def install_network_guard() -> None:
    """Install a process-wide socket guard whose policy is checked per call."""
    global _guard_installed
    if _guard_installed:
        return

    def guarded_connect(sock, address):
        require_network_allowed("socket connect", address)
        return _original_connect(sock, address)

    def guarded_connect_ex(sock, address):
        require_network_allowed("socket connect_ex", address)
        return _original_connect_ex(sock, address)

    def guarded_create_connection(address, *args, **kwargs):
        require_network_allowed("socket create_connection", address)
        return _original_create_connection(address, *args, **kwargs)

    def guarded_getaddrinfo(host, port, *args, **kwargs):
        require_network_allowed("DNS lookup", f"{host}:{port}")
        return _original_getaddrinfo(host, port, *args, **kwargs)

    def guarded_sendto(sock, data, *args):
        destination = args[-1] if args else "unspecified destination"
        require_network_allowed("connectionless socket send", destination)
        return _original_sendto(sock, data, *args)

    socket.socket.connect = guarded_connect
    socket.socket.connect_ex = guarded_connect_ex
    socket.create_connection = guarded_create_connection
    socket.getaddrinfo = guarded_getaddrinfo
    socket.socket.sendto = guarded_sendto
    _guard_installed = True
    logger.info("Application-wide network guard installed")
