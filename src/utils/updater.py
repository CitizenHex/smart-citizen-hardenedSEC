"""Hardened download utilities for optional community language files."""
import datetime
import email.utils
import logging
import os
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from src.utils.version import get_version
from src.utils.network_policy import require_network_allowed

logger = logging.getLogger(__name__)

ALLOWED_DOWNLOAD_URLS = frozenset({
    "https://raw.githubusercontent.com/Dymerz/StarCitizen-Localization/main/data/Localization/french_(france)/global.ini",
    "https://raw.githubusercontent.com/Thord82/Star_citizen_ES/propuestas_thord/global.ini",
    "https://raw.githubusercontent.com/Dymerz/StarCitizen-Localization/main/data/Localization/portuguese_(brazil)/global.ini",
    "https://raw.githubusercontent.com/stdblue/StarCitizenJapaneseResources/master/v4.x/release/japanese_(japan)/global.ini",
    "https://ini.42kit.com/full/global.ini",
    "https://raw.githubusercontent.com/Dymerz/StarCitizen-Localization/main/data/Localization/italian_(italy)/global.ini",
    "https://raw.githubusercontent.com/rjcncpt/StarCitizen-Deutsch-INI/main/live/global.ini",
})
MAX_DOWNLOAD_BYTES = 32 * 1024 * 1024
DOWNLOAD_CHUNK_BYTES = 64 * 1024


def _validate_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise ValueError("Only HTTPS language sources are allowed")
    if url not in ALLOWED_DOWNLOAD_URLS:
        raise ValueError("Language source URL is not allowlisted in this build")
    if parsed.username or parsed.password:
        raise ValueError("Credentials are not allowed in language source URLs")


def _read_limited_response(response) -> bytes:
    final_url = response.geturl()
    _validate_url(final_url)  # redirects may not leave the allowlist
    declared = int(response.headers.get("Content-Length") or 0)
    if declared > MAX_DOWNLOAD_BYTES:
        raise ValueError("Language file exceeds the 32 MiB size limit")
    chunks = []
    total = 0
    while True:
        chunk = response.read(DOWNLOAD_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_DOWNLOAD_BYTES:
            raise ValueError("Language file exceeds the 32 MiB size limit")
        chunks.append(chunk)
    return b"".join(chunks)


def _validate_ini_payload(data: bytes) -> None:
    if not data or b"\x00" in data:
        raise ValueError("Downloaded language file is empty or contains binary data")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Downloaded language file is not valid UTF-8 text") from exc
    meaningful = [line for line in text.splitlines() if line and not line.lstrip().startswith(("#", ";"))]
    if not meaningful or not any("=" in line for line in meaningful):
        raise ValueError("Downloaded content is not a localization INI file")


def _atomic_write(output_path: Path, data: bytes) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{output_path.name}.", suffix=".part", dir=output_path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        Path(temp_name).replace(output_path)
    except Exception:
        try:
            Path(temp_name).unlink(missing_ok=True)
        except OSError:
            pass
        raise


def download_file(url: str, output_path: str | Path) -> Path:
    """Download one validated language INI from an allowlisted HTTPS host."""
    output_path = Path(output_path)
    require_network_allowed("language download", url)
    _validate_url(url)
    req = Request(url, headers={"User-Agent": f"SmartCitizen/{get_version()}"})
    with urlopen(req, timeout=60) as response:
        data = _read_limited_response(response)
    _validate_ini_payload(data)
    _atomic_write(output_path, data)
    logger.info("Downloaded validated language file to %s (%d bytes)", output_path, len(data))
    return output_path


def download_file_if_changed(url: str, output_path: str | Path) -> bool:
    """Conditionally fetch and atomically replace a validated language INI."""
    output_path = Path(output_path)
    require_network_allowed("language freshness check", url)
    _validate_url(url)
    headers = {"User-Agent": f"SmartCitizen/{get_version()}"}
    if output_path.exists():
        mtime = output_path.stat().st_mtime
        dt = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc)
        headers["If-Modified-Since"] = email.utils.format_datetime(dt, usegmt=True)
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=60) as response:
            data = _read_limited_response(response)
        _validate_ini_payload(data)
        _atomic_write(output_path, data)
        logger.info("Downloaded validated %s (%d bytes)", output_path.name, len(data))
        return True
    except HTTPError as exc:
        if exc.code == 304:
            logger.info("%s is up to date", output_path.name)
            return False
        raise
