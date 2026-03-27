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
