"""Extracts files from Star Citizen's Data.p4k using bundled unp4k.exe."""
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Path of global.ini inside the p4k archive (unp4k preserves directory structure)
_GLOBAL_INI_RELATIVE = Path("data/Localization/english/global.ini")


def extract_global_ini(
    p4k_path: Path,
    output_path: Path,
    unp4k_exe: Path,
    progress_callback=None,
) -> bool:
    """Extract global.ini from Data.p4k and save it to output_path.

    Uses unp4k.exe with the filter "global.ini" to extract only the localization
    file, then copies it to output_path (overwriting any existing file).

    Args:
        p4k_path: Path to Star Citizen's Data.p4k file.
        output_path: Destination path (e.g. cache/base.ini).
        unp4k_exe: Path to the bundled unp4k.exe.
        progress_callback: Optional callable(str) for status messages.

    Returns:
        True on success.

    Raises:
        FileNotFoundError: If unp4k.exe or Data.p4k is missing, or the
            extracted file is not found after extraction.
        RuntimeError: If unp4k.exe exits with a non-zero return code.
    """
    if not unp4k_exe.exists():
        raise FileNotFoundError(f"unp4k.exe not found at: {unp4k_exe}")
    if not p4k_path.exists():
        raise FileNotFoundError(f"Data.p4k not found at: {p4k_path}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        if progress_callback:
            progress_callback("Launching unp4k — this may take a minute...")

        logger.info(f"Running unp4k: {unp4k_exe} {p4k_path} global.ini (cwd={tmp_dir})")
        result = subprocess.run(
            [str(unp4k_exe), str(p4k_path), "global.ini"],
            cwd=tmp_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            logger.error(f"unp4k stderr: {result.stderr}")
            raise RuntimeError(
                f"unp4k.exe exited with code {result.returncode}.\n\n{result.stderr or result.stdout}"
            )

        extracted = Path(tmp_dir) / _GLOBAL_INI_RELATIVE
        if not extracted.exists():
            raise FileNotFoundError(
                f"unp4k ran successfully but global.ini was not found at the expected path:\n"
                f"{extracted}\n\n"
                f"stdout: {result.stdout[:500]}"
            )

        if progress_callback:
            progress_callback("Copying extracted global.ini to cache...")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(extracted), str(output_path))
        logger.info(f"Extracted global.ini → {output_path}")

    return True
