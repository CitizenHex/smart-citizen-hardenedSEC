"""Auto-update utility for fetching latest base global.ini from GitHub."""
import json
import logging
import socket
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Callable
from urllib.request import urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com/repos/BeltaKoda/ScCompLangPackRemix/releases/latest"
GLOBAL_INI_PATH_IN_ZIP = "data/Localization/english/global.ini"

CONTRACTS_RAW_URL = "https://raw.githubusercontent.com/MrKraken/StarStrings/master/contracts.ini"
CONTRACTS_COMMITS_API_URL = (
    "https://api.github.com/repos/MrKraken/StarStrings/commits"
    "?path=contracts.ini&per_page=1"
)


def check_latest_release() -> tuple[str, str] | None:
    """Fetch latest LIVE release from GitHub.

    Returns:
        (tag_name, download_url) if successful, None if error or not LIVE
    """
    try:
        with urlopen(GITHUB_API_URL, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        tag_name = data.get("tag_name", "")

        # Only accept -LIVE releases
        if not tag_name.endswith("-LIVE"):
            logger.warning(f"Latest release is not -LIVE: {tag_name}")
            return None

        # Get download URL from first asset
        assets = data.get("assets", [])
        if not assets:
            logger.warning("No assets found in latest release")
            return None

        download_url = assets[0].get("browser_download_url")
        if not download_url:
            logger.warning("No download URL in asset")
            return None

        logger.info(f"Latest release: {tag_name}")
        return (tag_name, download_url)

    except (URLError, json.JSONDecodeError, Exception) as e:
        logger.warning(f"Failed to check latest release: {e}")
        return None


def get_current_base_version() -> str:
    """Read current base version from data/base_version.txt.

    Returns:
        Version string (e.g. "4.7.0-LIVE") or empty string if missing
    """
    version_file = Path(__file__).parent.parent.parent / "data" / "base_version.txt"

    if version_file.exists():
        try:
            return version_file.read_text(encoding='utf-8').strip()
        except Exception as e:
            logger.warning(f"Failed to read base version file: {e}")

    return ""


def save_base_version(version: str) -> None:
    """Write version to data/base_version.txt.

    Args:
        version: Version string (e.g. "4.7.0-LIVE")
    """
    version_file = Path(__file__).parent.parent.parent / "data" / "base_version.txt"

    try:
        version_file.parent.mkdir(parents=True, exist_ok=True)
        version_file.write_text(version, encoding='utf-8')
        logger.info(f"Saved base version: {version}")
    except Exception as e:
        logger.error(f"Failed to save base version: {e}")


def download_and_extract_base(download_url: str, progress_callback: Callable[[int, int], None]) -> Path:
    """Download zip file and extract global.ini to data/global.ini.

    Args:
        download_url: Direct URL to the zip file
        progress_callback: Called with (bytes_downloaded, total_bytes) during download

    Returns:
        Path to extracted global.ini file

    Raises:
        Exception if download or extraction fails
    """
    output_path = Path(__file__).parent.parent.parent / "data" / "global.ini"

    try:
        logger.info(f"Downloading from {download_url}")

        # Download with progress tracking
        with urlopen(download_url, timeout=60) as response:
            total_size = int(response.headers.get('content-length', 0))
            bytes_downloaded = 0
            chunks = []
            chunk_size = 65536  # 64KB chunks

            while True:
                try:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    bytes_downloaded += len(chunk)
                    # Update progress callback
                    try:
                        if total_size > 0:
                            progress_callback(bytes_downloaded, total_size)
                    except Exception:
                        pass  # Ignore callback errors
                except socket.timeout:
                    logger.warning("Download timeout, retrying...")
                    raise

            zip_data = b''.join(chunks)

        logger.info(f"Downloaded {len(zip_data)} bytes")

        # Extract global.ini from zip
        with zipfile.ZipFile(BytesIO(zip_data)) as zf:
            with zf.open(GLOBAL_INI_PATH_IN_ZIP) as f:
                global_ini_content = f.read()

        # Write to output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(global_ini_content)

        logger.info(f"Extracted global.ini to {output_path} ({len(global_ini_content)} bytes)")
        return output_path

    except Exception as e:
        logger.error(f"Failed to download/extract base: {e}")
        raise


def check_contracts_update() -> tuple[str, str] | None:
    """Fetch latest commit SHA and date for contracts.ini from MrKraken/StarStrings.

    Returns:
        (sha, date_str) if a newer commit exists, None if already up to date or on error.
        date_str is the ISO 8601 author date from the commit.
    """
    try:
        with urlopen(CONTRACTS_COMMITS_API_URL, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        if not data or len(data) == 0:
            logger.warning("No commits found for contracts.ini")
            return None

        commit = data[0]
        sha = commit.get("sha", "")
        date_str = commit.get("commit", {}).get("author", {}).get("date", "")

        if not sha:
            logger.warning("No SHA found in commit")
            return None

        # Check if this is newer than stored version
        current_sha, current_date = get_current_contracts_version()
        if sha == current_sha:
            logger.info(f"Contracts.ini already up to date: {sha[:8]}")
            return None

        logger.info(f"New contracts.ini available: {sha[:8]} ({date_str})")
        return (sha, date_str)

    except (URLError, json.JSONDecodeError, Exception) as e:
        logger.warning(f"Failed to check contracts update: {e}")
        return None


def get_current_contracts_version() -> tuple[str, str]:
    """Read current contracts version (SHA and date) from data/contracts_version.txt.

    Returns:
        (sha, date_str) tuple. Both empty strings if file missing or error.
        File format is 'sha\\ndate' (two lines).
    """
    version_file = Path(__file__).parent.parent.parent / "data" / "contracts_version.txt"

    if version_file.exists():
        try:
            content = version_file.read_text(encoding='utf-8').strip()
            lines = content.split('\n', 1)
            sha = lines[0] if lines else ""
            date_str = lines[1] if len(lines) > 1 else ""
            return (sha, date_str)
        except Exception as e:
            logger.warning(f"Failed to read contracts version file: {e}")

    return ("", "")


def save_contracts_version(sha: str, date_str: str) -> None:
    """Write contracts commit SHA and date to data/contracts_version.txt.

    Args:
        sha: Full commit SHA string.
        date_str: ISO 8601 date string from commit author.
    """
    version_file = Path(__file__).parent.parent.parent / "data" / "contracts_version.txt"

    try:
        version_file.parent.mkdir(parents=True, exist_ok=True)
        version_file.write_text(f"{sha}\n{date_str}", encoding='utf-8')
        logger.info(f"Saved contracts version: {sha[:8]} ({date_str})")
    except Exception as e:
        logger.error(f"Failed to save contracts version: {e}")


def download_contracts(progress_callback: Callable[[int, int], None]) -> Path:
    """Download contracts.ini from MrKraken/StarStrings and save to data/contracts.ini.

    Args:
        progress_callback: Called with (bytes_downloaded, total_bytes) during download.

    Returns:
        Path to saved data/contracts.ini.

    Raises:
        Exception if download fails.
    """
    output_path = Path(__file__).parent.parent.parent / "data" / "contracts.ini"

    try:
        logger.info(f"Downloading from {CONTRACTS_RAW_URL}")

        with urlopen(CONTRACTS_RAW_URL, timeout=60) as response:
            total_size = int(response.headers.get('content-length', 0))
            bytes_downloaded = 0
            chunks = []
            chunk_size = 65536  # 64KB chunks

            while True:
                try:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    bytes_downloaded += len(chunk)
                    try:
                        if total_size > 0:
                            progress_callback(bytes_downloaded, total_size)
                    except Exception:
                        pass  # Ignore callback errors
                except socket.timeout:
                    logger.warning("Download timeout, retrying...")
                    raise

            contracts_data = b''.join(chunks)

        # Write to output (contracts.ini uses UTF-8 with BOM, write raw bytes)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(contracts_data)

        logger.info(f"Downloaded contracts.ini to {output_path} ({len(contracts_data)} bytes)")
        return output_path

    except Exception as e:
        logger.error(f"Failed to download contracts: {e}")
        raise
