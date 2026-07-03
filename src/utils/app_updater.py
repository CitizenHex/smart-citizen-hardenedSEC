"""Check GitHub Releases for a newer Smart Citizen installer.

Hits the public ``/releases/latest`` endpoint (no auth), parses ``tag_name`` +
``html_url`` + ``body`` from the JSON payload, and compares the tag against
the locally-installed version from ``VERSION.TXT``. Runs on a ``QThread`` so
the UI never blocks on the network.

The GitHub unauthenticated rate limit is 60 req/hr per IP; the startup check
runs once per launch (#211) — one call, far under that cap — and gates the
rest of startup (source sync, extraction prompts) until it resolves.
"""
from __future__ import annotations

import json
import logging
import re
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from src.utils.version import get_version

logger = logging.getLogger(__name__)

GITHUB_API_URL = (
    "https://api.github.com/repos/Osiris-DevWorks/smart-citizen/releases/latest"
)
REQUEST_TIMEOUT_SECONDS = 10

# Release-asset name for the Windows installer, e.g. SmartCitizen-2.1.1-Setup.exe.
# Anchored full match so renamed or extra assets (portable zips, checksums)
# never get picked up as the installer.
_INSTALLER_ASSET_RE = re.compile(r"smartcitizen-.+-setup\.exe", re.IGNORECASE)

DOWNLOAD_CHUNK_BYTES = 256 * 1024


def parse_version(s: str) -> Optional[tuple[int, int, int]]:
    """Parse a ``major.minor.patch`` (optionally ``v``-prefixed) into a tuple.

    Returns ``None`` if the input can't be parsed — callers should treat that
    as "can't compare" rather than "equal" so we never silently pester on
    malformed tags.
    """
    if not s:
        return None
    s = s.strip().lstrip("vV")
    parts = s.split(".")
    if len(parts) < 2:
        return None
    try:
        nums = [int(p) for p in parts[:3]]
    except ValueError:
        return None
    while len(nums) < 3:
        nums.append(0)
    return (nums[0], nums[1], nums[2])


def pick_installer_asset(assets) -> Optional[tuple[str, int]]:
    """Return ``(download_url, size_bytes)`` for the installer asset, or None.

    *assets* is the ``assets`` array from a GitHub release payload. A release
    published without the Setup.exe attached (or with malformed asset entries)
    returns None — callers fall back to opening the release page.
    """
    if not assets:
        return None
    for asset in assets:
        try:
            name = (asset.get("name") or "").strip()
            url = (asset.get("browser_download_url") or "").strip()
            size = int(asset.get("size") or 0)
        except (AttributeError, TypeError, ValueError):
            continue
        if url and _INSTALLER_ASSET_RE.fullmatch(name):
            return (url, size)
    return None


def is_newer(latest: str, current: str) -> bool:
    """Return True iff *latest* is strictly newer than *current*.

    Unparseable input on either side returns False — fail safe so we don't
    prompt the user based on garbage.
    """
    lt = parse_version(latest)
    ct = parse_version(current)
    if lt is None or ct is None:
        return False
    return lt > ct


class AppUpdateCheckWorker(QThread):
    """Query GitHub Releases for the latest Smart Citizen version.

    Emits one of ``update_available`` / ``up_to_date`` / ``check_error`` and
    always emits ``finished`` so the owner can clean up. Mirrors the
    signal shape of ``StartupSyncWorker`` in ``main_window.py``.
    """

    # (latest_version, release_page_url, body, asset_url, asset_size_bytes)
    # asset_url is "" (and size 0) when the release has no installer asset —
    # receivers fall back to the release page.
    update_available = pyqtSignal(str, str, str, str, int)
    up_to_date = pyqtSignal(str)                   # (current_version)
    check_error = pyqtSignal(str)                  # (error_message)
    finished = pyqtSignal()

    def run(self) -> None:
        current = get_version()
        try:
            req = urllib.request.Request(
                GITHUB_API_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": f"SmartCitizen/{current}",
                },
            )
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
                payload = json.load(resp)
        except Exception as e:
            msg = f"{type(e).__name__}: {e}"
            logger.warning(f"App update check failed: {msg}")
            self.check_error.emit(msg)
            self.finished.emit()
            return

        tag = (payload.get("tag_name") or "").strip()
        url = (payload.get("html_url") or "").strip()
        body = (payload.get("body") or "").strip()
        latest = tag.lstrip("vV")

        if not tag:
            self.check_error.emit("Release payload missing tag_name")
            self.finished.emit()
            return

        if is_newer(tag, current):
            asset = pick_installer_asset(payload.get("assets"))
            asset_url, asset_size = asset if asset else ("", 0)
            logger.info(
                f"App update available: {latest} (current {current}, "
                f"installer asset: {'yes' if asset_url else 'no'})"
            )
            self.update_available.emit(latest, url, body, asset_url, asset_size)
        else:
            logger.info(f"App is up to date at {current}")
            self.up_to_date.emit(current)

        self.finished.emit()


def _download_progress_message(done: int, total: int) -> str:
    """Human-readable byte progress for the dialog label, e.g. '42.5 / 118.3 MB'."""
    mb = 1024 * 1024
    if total > 0:
        return f"{done / mb:.1f} / {total / mb:.1f} MB"
    return f"{done / mb:.1f} MB"


class AppUpdateDownloadWorker(QThread):
    """Download the release installer to a temp folder, with progress.

    Streams the Setup.exe to ``%TEMP%\\SmartCitizen-Update\\`` in chunks,
    writing to a ``.part`` file that is renamed only on completion — a
    half-download can never be mistaken for a runnable installer. Emits
    ``progress_pct`` in the shared ``(completed, total, message)`` shape so
    ``AnimatedProgressDialog.set_progress`` can consume it directly, then one
    of ``download_finished(path)`` / ``download_error(message)``, and always
    ``finished``. Cancellation goes through ``requestInterruption()``.
    """

    progress_pct = pyqtSignal(int, int, str)  # (completed, total, message)
    download_finished = pyqtSignal(str)       # (installer_path)
    download_error = pyqtSignal(str)          # (error_message)
    finished = pyqtSignal()

    def __init__(self, url: str, expected_size: int = 0, parent=None,
                 dest_dir: Optional[Path] = None):
        super().__init__(parent)
        self._url = url
        self._expected_size = expected_size
        self._dest_dir = dest_dir

    def run(self) -> None:
        part = None
        try:
            dest_dir = self._dest_dir or (
                Path(tempfile.gettempdir()) / "SmartCitizen-Update"
            )
            dest_dir.mkdir(parents=True, exist_ok=True)
            name = Path(urllib.parse.urlsplit(self._url).path).name
            if not name.lower().endswith(".exe"):
                name = "SmartCitizen-Setup.exe"
            target = dest_dir / name
            part = target.with_name(target.name + ".part")

            req = urllib.request.Request(
                self._url,
                headers={
                    "Accept": "application/octet-stream",
                    "User-Agent": f"SmartCitizen/{get_version()}",
                },
            )
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
                total = int(resp.headers.get("Content-Length") or 0)
                if total <= 0:
                    total = self._expected_size
                done = 0
                with open(part, "wb") as fh:
                    while True:
                        if self.isInterruptionRequested():
                            raise InterruptedError("Download cancelled")
                        chunk = resp.read(DOWNLOAD_CHUNK_BYTES)
                        if not chunk:
                            break
                        fh.write(chunk)
                        done += len(chunk)
                        self.progress_pct.emit(
                            done, total, _download_progress_message(done, total)
                        )
            part.replace(target)
            logger.info(f"Update installer downloaded to {target}")
            self.download_finished.emit(str(target))
        except Exception as e:
            if part is not None:
                try:
                    part.unlink(missing_ok=True)
                except OSError:
                    pass
            msg = f"{type(e).__name__}: {e}"
            logger.warning(f"Update installer download failed: {msg}")
            self.download_error.emit(msg)
        finally:
            self.finished.emit()
