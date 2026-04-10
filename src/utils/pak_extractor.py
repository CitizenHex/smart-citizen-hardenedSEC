"""Extracts files from Star Citizen's Data.p4k using bundled unp4k.exe."""
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Path of global.ini inside the p4k archive (unp4k preserves directory structure)
_GLOBAL_INI_RELATIVE = Path("data/Localization/english/global.ini")


def _get_subprocess_kwargs() -> dict:
    """Return subprocess kwargs to suppress window on Windows."""
    kwargs = {
        "capture_output": True,
        "text": True,
    }
    # On Windows, suppress the subprocess window completely
    if sys.platform == "win32":
        # CREATE_NO_WINDOW = 0x08000000
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0x08000000
    return kwargs


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
            timeout=300,
            **_get_subprocess_kwargs()
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


# Subdirectories (relative to the Data/ dir created by unp4k) that we keep
# from the full DataForge extraction.  Everything else is discarded.
_DATAFORGE_KEEP = [
    "libs/foundry/records/entities/scitem/ships/shieldgenerator",
    "libs/foundry/records/entities/scitem/ships/cooler",
    "libs/foundry/records/entities/scitem/ships/powerplant",
    "libs/foundry/records/entities/scitem/ships/quantumdrive",
    "libs/foundry/records/entities/scitem/ships/weapons",
    "libs/foundry/records/entities/scitem/weapons/fps_weapons",
    "libs/foundry/records/ammoparams/vehicle",
    "libs/foundry/records/ammoparams/fps",
    "libs/foundry/records/entities/spaceships",
    "libs/foundry/records/entities/scitem/ships/controller",
    # Mission/contract/job terminal entities (for XP and reward extraction)
    "libs/foundry/records/entities/missions",
    "libs/foundry/records/entities/contracts",
    "libs/foundry/records/entities/jobterminal",
    # Crafting/recipe entities (for commodity crafting usage markers)
    "libs/foundry/records/entities/crafting",
    "libs/foundry/records/entities/recipes",
    "libs/foundry/records/entities/manufacturing",
    # Radar/sensor entities (for detection range and sensitivity stats)
    "libs/foundry/records/entities/scitem/radar",
    "libs/foundry/records/entities/scitem/sensors",
    "libs/foundry/records/entities/scitem/avionics/radar",
    # Missile/rocket entities (for tracking and velocity stats)
    "libs/foundry/records/entities/scitem/ammo/missiles",
    "libs/foundry/records/entities/scitem/ammo/rockets",
    "libs/foundry/records/entities/scitem/ammo/bombs",
]


def extract_dataforge(
    p4k_path: Path,
    unp4k_exe: Path,
    unforge_exe: Path,
    dataforge_cache_dir: Path,
    progress_callback=None,
) -> bool:
    """Extract DataForge entity XMLs from Data.p4k and cache relevant subdirectories.

    Pipeline:
      1. unp4k.exe extracts Game2.dcb from the p4k into a temp directory.
      2. unforge.exe converts Game2.dcb → individual XML entity files.
      3. Only the subdirectories needed for stats generation are copied to
         dataforge_cache_dir; everything else is discarded.

    This is slow the first time (~several minutes) but results are cached and
    only need to be re-run when the p4k file changes.

    Args:
        p4k_path: Path to Data.p4k.
        unp4k_exe: Path to bundled unp4k.exe.
        unforge_exe: Path to bundled unforge.exe.
        dataforge_cache_dir: Destination directory for the cached entity XMLs.
        progress_callback: Optional callable(str) for status messages.

    Returns:
        True on success.

    Raises:
        FileNotFoundError: If required executables or Data.p4k are missing.
        RuntimeError: If either subprocess fails.
    """
    for exe, name in [(unp4k_exe, "unp4k.exe"), (unforge_exe, "unforge.exe")]:
        if not exe.exists():
            raise FileNotFoundError(f"{name} not found at: {exe}")
    if not p4k_path.exists():
        raise FileNotFoundError(f"Data.p4k not found at: {p4k_path}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)

        # ── Step 1: Extract Game2.dcb ─────────────────────────────────────────
        if progress_callback:
            progress_callback("Extracting Game2.dcb from Data.p4k…")
        logger.info(f"Running unp4k to extract .dcb: {unp4k_exe} {p4k_path} .dcb")
        result = subprocess.run(
            [str(unp4k_exe), str(p4k_path), ".dcb"],
            cwd=tmp_dir,
            timeout=600,
            **_get_subprocess_kwargs()
        )
        if result.returncode != 0:
            raise RuntimeError(f"unp4k.exe failed (code {result.returncode}):\n{result.stderr or result.stdout}")

        # unp4k preserves archive structure: Data/Game2.dcb
        dcb_candidates = list(tmp.glob("Data/Game*.dcb"))
        if not dcb_candidates:
            raise FileNotFoundError("Game*.dcb not found in p4k output — check game install path.")
        dcb_path = dcb_candidates[0]
        logger.info(f"Found DCB: {dcb_path} ({dcb_path.stat().st_size / 1_048_576:.0f} MB)")

        # ── Step 2: Run unforge to produce entity XMLs ────────────────────────
        if progress_callback:
            progress_callback("Converting DataForge database — this takes several minutes…")
        logger.info(f"Running unforge: {unforge_exe} {dcb_path}")
        result = subprocess.run(
            [str(unforge_exe), str(dcb_path)],
            timeout=1800,   # 30 minutes max
            **_get_subprocess_kwargs()
        )
        if result.returncode != 0:
            raise RuntimeError(f"unforge.exe failed (code {result.returncode}):\n{result.stderr or result.stdout}")

        # unforge writes entity XMLs into a libs/ subdirectory next to the dcb file.
        # _DATAFORGE_KEEP paths already start with "libs/...", so use dcb_path.parent
        # as the base to avoid a doubled "libs/libs/..." path.
        libs_dir = dcb_path.parent
        if not (libs_dir / "libs").exists():
            raise FileNotFoundError("unforge ran but libs/ directory was not created — unexpected output structure.")

        # ── Step 3: Copy only the needed subdirectories to cache ──────────────
        if progress_callback:
            progress_callback("Caching entity files…")
        if dataforge_cache_dir.exists():
            shutil.rmtree(dataforge_cache_dir)
        dataforge_cache_dir.mkdir(parents=True, exist_ok=True)

        for rel in _DATAFORGE_KEEP:
            src = libs_dir / rel
            if not src.exists():
                logger.warning(f"Expected DataForge subdir not found (skipping): {src}")
                continue
            dst = dataforge_cache_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst)
            logger.info(f"Cached {rel} ({sum(f.stat().st_size for f in dst.rglob('*') if f.is_file()) // 1024} KB)")

        # Write a stamp so we know when this was extracted (p4k mtime)
        stamp = dataforge_cache_dir / ".p4k_mtime"
        stamp.write_text(str(p4k_path.stat().st_mtime))
        logger.info(f"DataForge cache written to {dataforge_cache_dir}")

    return True


def dataforge_cache_is_fresh(p4k_path: Path, dataforge_cache_dir: Path) -> bool:
    """Return True if the cached DataForge XMLs are up-to-date with the p4k.

    Requires both a matching mtime stamp AND actual XML content in the cache
    so a stamp-only remnant from a failed/partial extraction returns False.
    """
    stamp = dataforge_cache_dir / ".p4k_mtime"
    libs_dir = dataforge_cache_dir / "libs"
    if not stamp.exists() or not libs_dir.exists():
        return False
    # Verify there is at least one XML file — guards against empty extractions
    if not any(libs_dir.rglob("*.xml")):
        return False
    try:
        cached_mtime = float(stamp.read_text().strip())
        return cached_mtime >= p4k_path.stat().st_mtime
    except Exception:
        return False
