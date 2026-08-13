"""
Build script for creating Smart Citizen executable

Usage:
    python build_exe.py                    # Build without incrementing version
    python build_exe.py --increment patch  # Increment patch version (0.1.0 -> 0.1.1)
    python build_exe.py --increment minor  # Increment minor version (0.1.0 -> 0.2.0)
    python build_exe.py --increment major  # Increment major version (0.1.0 -> 1.0.0)
    python build_exe.py --portable         # Build standalone portable variant
                                           # (writes to <exe-dir>/data/, no registry)
    python build_exe.py --portable --local-test
                                           # Build only the runnable portable folder.
                                           # Skips ZIP, checksum, and release manifest.
    # Flags can combine, e.g. `--portable --increment patch`.
"""

import PyInstaller.__main__
import hashlib
import json
import os
import sys
import shutil
import zipfile

# Get the project directory
project_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(project_dir))

# Add src to path for imports
sys.path.insert(0, os.path.join(root_dir, 'src'))

# Handle CLI flags. Position-independent parsing — a list of args we
# slowly drain, recognising known flags. Anything left over is unused
# but we don't error on it (forward-compat with future flags).
_args = sys.argv[1:]
increment_version = None
portable_mode = False
local_test_mode = False
i = 0
while i < len(_args):
    arg = _args[i]
    if arg == '--increment' and i + 1 < len(_args):
        increment_type = _args[i + 1].lower()
        if increment_type in ['major', 'minor', 'patch']:
            increment_version = increment_type
        else:
            print(f"Error: Invalid increment type '{increment_type}'. Use 'major', 'minor', or 'patch'")
            sys.exit(1)
        i += 2
        continue
    if arg == '--portable':
        portable_mode = True
        i += 1
        continue
    if arg == '--local-test':
        local_test_mode = True
        portable_mode = True
        i += 1
        continue
    i += 1

# Get version from VERSION.TXT
version_file = os.path.join(root_dir, 'VERSION.TXT')
with open(version_file, 'r') as f:
    current_version = f.read().strip()

print(f"\n{'='*60}")
build_kind = " (LOCAL PORTABLE TEST)" if local_test_mode else (' (PORTABLE)' if portable_mode else '')
print(f"Building version: {current_version}{build_kind}")
print(f"{'='*60}\n")

# ── Portable-build flag plumbing ────────────────────────────────────────
# When --portable is set, write src/utils/_build_info.py with
# IS_PORTABLE = True before PyInstaller runs. build_mode.py imports
# IS_PORTABLE from _build_info if present; otherwise it defaults to
# False. After the PyInstaller run we delete _build_info.py so the
# repo stays in its default (registry-mode) state — protects against
# a developer running `python src/main.py` immediately after a
# portable build and getting silently switched to portable mode.
build_info_path = os.path.join(root_dir, 'src', 'utils', '_build_info.py')

def _write_build_info(is_portable: bool) -> None:
    """Generate src/utils/_build_info.py with the build-time flags.

    Module is git-ignored — never commit. Read by build_mode.py via
    a try/except ImportError fallback.
    """
    content = (
        '"""Build-time flags written by scripts/build/build_exe.py.\n'
        '\n'
        'DO NOT COMMIT. DO NOT EDIT BY HAND. Git-ignored — regenerated on every build.\n'
        '"""\n'
        f'IS_PORTABLE: bool = {is_portable!r}\n'
    )
    with open(build_info_path, 'w', encoding='utf-8') as f:
        f.write(content)

def _cleanup_build_info() -> None:
    """Remove the generated _build_info.py post-build.

    Idempotent — safe to call even if the file isn't there. We do this
    in a finally block so a PyInstaller failure mid-run doesn't leave
    the source tree in portable-mode state.
    """
    try:
        if os.path.exists(build_info_path):
            os.remove(build_info_path)
            print(f"  - Cleaned up {os.path.relpath(build_info_path, root_dir)}")
    except OSError as e:
        print(f"  WARNING: could not delete {build_info_path}: {e}")


def _write_package_integrity_manifest(package_dir: str) -> None:
    """Write hashes for every packaged runtime file after build cleanup."""
    entries = {}
    for walk_root, _dirs, files in os.walk(package_dir):
        for filename in sorted(files):
            if filename == "package-integrity.json":
                continue
            full_path = os.path.join(walk_root, filename)
            relative = os.path.relpath(full_path, package_dir).replace(os.sep, "/")
            digest = hashlib.sha256()
            with open(full_path, "rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            entries[relative] = {"size": os.path.getsize(full_path), "sha256": digest.hexdigest()}
    manifest = {"format": 1, "version": current_version, "files": entries}
    path = os.path.join(package_dir, "package-integrity.json")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
    print(f"  - Wrote package-integrity.json ({len(entries)} files)")

# Clean previous builds
print("Cleaning old builds...")
if local_test_mode:
    # Local iterations must never delete a release ZIP, signed manifest, or
    # upload directory. Keep their disposable output entirely separate.
    cleanup_paths = [
        os.path.join(root_dir, 'build', 'local-test'),
        os.path.join(root_dir, 'dist', 'local-test'),
    ]
else:
    cleanup_paths = [os.path.join(root_dir, 'build'), os.path.join(root_dir, 'dist')]
for path in cleanup_paths:
    if os.path.exists(path):
        # A prior portable test can contain a DataForge cache whose files
        # were removed concurrently by Defender, OneDrive, or a cleanup
        # utility.  Those already-missing generated files must not block a
        # fresh build; new output uses versioned ZIP names and is written
        # independently below.
        shutil.rmtree(path, ignore_errors=True)
        print(f"  - Removed {os.path.relpath(path, root_dir)}/")
# Also clean any stale _build_info.py from an interrupted prior build.
_cleanup_build_info()

print()

# Build executable with PyInstaller.
# The release ZIP remains versioned, while the executable is deliberately
# stable. A portable user can extract an approved update over the same folder
# and keep an existing shortcut working; the version is still visible in the
# app window, release ZIP name, and package-integrity manifest.
exe_name = "SmartCitizen-Hardened" if portable_mode else "SmartCitizen"
output_root = os.path.join(root_dir, 'dist', 'local-test') if local_test_mode else os.path.join(root_dir, 'dist')
work_root = os.path.join(root_dir, 'build', 'local-test') if local_test_mode else os.path.join(root_dir, 'build')

# Write PyInstaller's generated .spec into build/ (ephemeral, wiped each run)
# instead of the repo root, so the stable --name never clobbers the
# hand-maintained root SmartCitizen.spec or litters the root with per-version
# spec files.
spec_path = work_root
os.makedirs(spec_path, exist_ok=True)

assets_dir   = os.path.join(root_dir, 'assets')
icon_path    = os.path.join(assets_dir, 'logo.ico')
about_file   = os.path.join(root_dir, 'docs', 'ABOUT.md')
help_file    = os.path.join(root_dir, 'docs', 'HELP.md')
legal_file   = os.path.join(root_dir, 'docs', 'LEGAL.md')
faq_file     = os.path.join(root_dir, 'docs', 'FAQ.md')
patches_dir  = os.path.join(root_dir, 'patches')
languages_dir = os.path.join(root_dir, 'languages')
enhancements_script = os.path.join(root_dir, 'scripts', 'generate_enhancements_ini.py')

common_args = [
    os.path.join(root_dir, 'src', 'main.py'),
    '--name', exe_name,
    '--windowed',
    '--icon', icon_path,
    '--add-data', f'{version_file}{os.pathsep}.',
    '--add-data', f'{about_file}{os.pathsep}docs',
    '--add-data', f'{help_file}{os.pathsep}docs',
    '--add-data', f'{legal_file}{os.pathsep}docs',
    '--add-data', f'{faq_file}{os.pathsep}docs',
    '--add-data', f'{assets_dir}{os.pathsep}assets',
    '--add-data', f'{patches_dir}{os.pathsep}patches',
    # UI translation files. Without this the frozen app can't resolve any
    # tr() key (get_resource_path misses languages/<lang>/ui.json), so the
    # whole UI renders raw keys like 'branding.title'. Mirrors the
    # ('languages', 'languages') entry in SmartCitizen.spec.
    '--add-data', f'{languages_dir}{os.pathsep}languages',
    '--add-data', f'{enhancements_script}{os.pathsep}scripts',
    '--workpath', work_root,
    '--specpath', spec_path,
    '--hidden-import=PyQt6',
    '--hidden-import=src.gui',
    '--hidden-import=src.parser',
    '--hidden-import=src.merger',
    '--hidden-import=src.models',
    '--hidden-import=src.utils',
    # Modules that are only referenced from files PyInstaller loads as *data*
    # (not as code) need to be listed explicitly, or they silently miss the
    # bundle. scripts/generate_enhancements_ini.py is added via --add-data
    # and therefore never parsed for imports — its
    # `from src.utils.progress_sink import ProgressSink` then hits the
    # `except ImportError: _sink = None` branch in the frozen build, and
    # Generate Enhancements runs with an indeterminate progress bar the
    # whole time even though the determinate plumbing works in dev. We
    # pre-empted `--collect-submodules=src.utils` as a broader fix but it
    # didn't pick up progress_sink (pyinstaller's module-graph walk still
    # needs some in-graph reference to the package to expand it on our
    # src/ layout). Explicit hidden-import for the two script-only helpers
    # is the robust fix.
    '--hidden-import=src.utils.progress_sink',
    '--hidden-import=src.utils.dataforge_patcher',
    '--collect-all=lxml',
    # scripts/generate_enhancements_ini.py is loaded dynamically via
    # importlib at runtime (see EnhancementsGeneratorWorker), so
    # PyInstaller's static import graph can't see its dependencies.
    # --collect-all is stronger than --hidden-import: it forces every
    # submodule + data file into the bundle regardless of whether the
    # module graph finds a reference. Earlier hidden-import flags alone
    # silently no-op'd for concurrent.futures on PyInstaller 6 / Py 3.12.
    '--collect-all=concurrent',
]

# Build --onedir version only — feeds the Inno Setup installer. The portable
# --onefile build was retired because we release the installer as the sole
# distribution artifact.
print("Building --onedir version (for installer)...")
print(f"  Output: {os.path.relpath(os.path.join(output_root, exe_name), root_dir)}/")
print()

onedir_args = common_args + [
    '--onedir',
    # Only replaces the precise --distpath/--name directory. In local-test
    # mode that is dist/local-test/SmartCitizen-Hardened, never release ZIPs
    # or signed upload assets in dist/.
    '--noconfirm',
    '--distpath', output_root,
]

try:
    # Write the build-time flag module BEFORE PyInstaller scans imports
    # (PyInstaller bundles whatever's on disk at run-time, so the file
    # must exist before its module-graph walk starts).
    if portable_mode:
        _write_build_info(is_portable=True)
        print(f"  Wrote {os.path.relpath(build_info_path, root_dir)} with IS_PORTABLE = True")
        print()

    PyInstaller.__main__.run(onedir_args)
    if portable_mode:
        # The GUI cannot replace its own running executable on Windows. Build
        # a small console helper into the same verified package; at update
        # time the GUI copies it to staging and launches that copy.
        helper_args = [
            os.path.join(root_dir, 'src', 'update_helper.py'),
            '--name', 'SmartCitizen-UpdateHelper', '--onefile', '--console',
            '--paths', root_dir,
            '--distpath', os.path.join(output_root, exe_name),
            '--workpath', os.path.join(work_root, 'update-helper'),
            '--specpath', os.path.join(work_root, 'update-helper'),
            '--clean', '--noconfirm',
        ]
        PyInstaller.__main__.run(helper_args)
    print(f"\n{'='*60}")
    print("Build successful!")
    print(f"{'='*60}")
    print(f"Build dir: {os.path.relpath(os.path.join(output_root, exe_name), root_dir)}/")
    print()

    # --collect-all=lxml (needed so dynamically-imported lxml submodules
    # aren't missed) also drags in isoschematron's bundled reference-XSLT
    # resources — used only if code calls lxml.isoschematron.Schematron(),
    # which nothing here does. Those files add ~100+ chars of nested path
    # depth (_internal/lxml/isoschematron/resources/xsl/iso-schematron-xslt1/...)
    # for zero functional benefit, and combined with the patches/ tree's own
    # depth that's enough to push some paths past Windows' 260-char MAX_PATH
    # once extracted — which is what makes Explorer refuse to Recycle-Bin
    # them on delete. Safe to strip post-build: doesn't touch lxml's actual
    # etree/XPath parsing (compiled extension code, unaffected).
    isoschematron_resources = os.path.join(
        output_root, exe_name, '_internal', 'lxml', 'isoschematron', 'resources'
    )
    if os.path.exists(isoschematron_resources):
        shutil.rmtree(isoschematron_resources)
        print("  - Removed unused lxml isoschematron resources (dead weight, deep paths)")
        print()

    if portable_mode:
        _write_package_integrity_manifest(os.path.join(output_root, exe_name))
        print()

    # Portable distribution: zip up the onedir output for a no-install
    # USB-stick-friendly download. Recipients extract anywhere, run the
    # .exe inside; portable mode writes its data/ folder right there.
    # The standard build doesn't get a zip — Inno Setup is its
    # distribution artifact, attached separately by release.yml.
    if portable_mode and not local_test_mode:
        # The executable/folder name stays stable for shortcuts and in-place
        # updates. The downloadable release ZIP remains versioned so it is
        # unambiguous what a user is about to install.
        zip_name = f"SmartCitizen-Hardened-v{current_version}.zip"
        zip_path = os.path.join(root_dir, 'dist', zip_name)
        onedir_path = os.path.join(output_root, exe_name)
        print(f"Packaging portable zip: dist/{zip_name}")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for root, _dirs, files in os.walk(onedir_path):
                for fname in files:
                    full = os.path.join(root, fname)
                    # Inside the zip: files sit at the top level (no extra
                    # SmartCitizen-Portable-vX.Y.Z/ wrapper). Explorer's
                    # "Extract All" already creates an enclosing folder
                    # named after the zip, so wrapping here too used to
                    # double that prefix on the common extraction path —
                    # exactly the kind of redundant length that tips deep
                    # _internal/ paths over MAX_PATH. Recipients who
                    # manually unzip into an already-open folder instead
                    # of using Extract All will get the files loose there.
                    arcname = os.path.relpath(full, onedir_path)
                    zf.write(full, arcname=arcname)
        zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"  Portable zip ready: dist/{zip_name} ({zip_size_mb:.1f} MB)")
        zip_hash = hashlib.sha256()
        with open(zip_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                zip_hash.update(chunk)
        digest = zip_hash.hexdigest()
        hash_path = zip_path + ".sha256"
        with open(hash_path, "w", encoding="ascii", newline="\n") as handle:
            handle.write(f"{digest}  {zip_name}\n")
        # This deliberately remains unsigned in the build directory. Copy it
        # to the separate trusted signing machine, sign it there, then upload
        # the ZIP, this manifest, and its detached .sig together as release
        # assets. The app will not accept a ZIP unless this signature verifies.
        release_manifest = {
            "format": 1,
            "application": "Smart Citizen Hardened",
            "version": current_version,
            "zip_name": zip_name,
            "zip_size": os.path.getsize(zip_path),
            "zip_sha256": digest,
            "executable": "SmartCitizen-Hardened.exe",
            "package_manifest": "package-integrity.json",
        }
        manifest_path = os.path.join(root_dir, "dist", "release-manifest.json")
        with open(manifest_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(release_manifest, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
        print(f"  Release manifest ready for offline signing: dist/release-manifest.json")
        print()
    elif local_test_mode:
        print(f"  Local test build ready: dist/local-test/{exe_name}/{exe_name}.exe")
        print("  ZIP, checksum, and release manifest intentionally skipped.")
        print()
except Exception as e:
    print(f"\nError building --onedir executable: {e}")
    sys.exit(1)
finally:
    # Always remove the generated _build_info.py — keeps the source
    # tree in default (registry) mode for any subsequent dev runs.
    if portable_mode:
        _cleanup_build_info()
