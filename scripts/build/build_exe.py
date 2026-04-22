"""
Build script for creating Smart Citizen executable

Usage:
    python build_exe.py                    # Build without incrementing version
    python build_exe.py --increment patch  # Increment patch version (0.1.0 -> 0.1.1)
    python build_exe.py --increment minor  # Increment minor version (0.1.0 -> 0.2.0)
    python build_exe.py --increment major  # Increment major version (0.1.0 -> 1.0.0)
"""

import PyInstaller.__main__
import os
import sys
import shutil

# Get the project directory
project_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(project_dir))

# Add src to path for imports
sys.path.insert(0, os.path.join(root_dir, 'src'))

# Handle version increment argument
increment_version = None
if len(sys.argv) > 1:
    if sys.argv[1] == '--increment' and len(sys.argv) > 2:
        increment_type = sys.argv[2].lower()
        if increment_type in ['major', 'minor', 'patch']:
            increment_version = increment_type
        else:
            print(f"Error: Invalid increment type '{increment_type}'. Use 'major', 'minor', or 'patch'")
            sys.exit(1)

# Get version from VERSION.TXT
version_file = os.path.join(root_dir, 'VERSION.TXT')
with open(version_file, 'r') as f:
    current_version = f.read().strip()

print(f"\n{'='*60}")
print(f"Building version: {current_version}")
print(f"{'='*60}\n")

# Clean previous builds
print("Cleaning old builds...")
for folder in ['build', 'dist']:
    path = os.path.join(root_dir, folder)
    if os.path.exists(path):
        shutil.rmtree(path)
        print(f"  - Removed {folder}/")

print()

# Build executable with PyInstaller
exe_name = f"SmartCitizen-v{current_version}"

assets_dir   = os.path.join(root_dir, 'assets')
icon_path    = os.path.join(assets_dir, 'logo.ico')
about_file   = os.path.join(root_dir, 'ABOUT.md')
help_file    = os.path.join(root_dir, 'HELP.md')
patches_dir  = os.path.join(root_dir, 'patches')
enhancements_script = os.path.join(root_dir, 'scripts', 'generate_enhancements_ini.py')

common_args = [
    os.path.join(root_dir, 'src', 'main.py'),
    '--name', exe_name,
    '--windowed',
    '--icon', icon_path,
    '--add-data', f'{version_file}{os.pathsep}.',
    '--add-data', f'{about_file}{os.pathsep}.',
    '--add-data', f'{help_file}{os.pathsep}.',
    '--add-data', f'{assets_dir}{os.pathsep}assets',
    '--add-data', f'{patches_dir}{os.pathsep}patches',
    '--add-data', f'{enhancements_script}{os.pathsep}scripts',
    '--workpath', os.path.join(root_dir, 'build'),
    '--specpath', root_dir,
    '--hidden-import=PyQt6',
    '--hidden-import=src.gui',
    '--hidden-import=src.parser',
    '--hidden-import=src.merger',
    '--hidden-import=src.models',
    '--hidden-import=src.utils',
    '--hidden-import=xml',
    '--hidden-import=xml.etree',
    '--hidden-import=xml.etree.ElementTree',
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
print(f"  Output: dist/{exe_name}/")
print()

onedir_args = common_args + [
    '--onedir',
    '--distpath', os.path.join(root_dir, 'dist'),
]

try:
    PyInstaller.__main__.run(onedir_args)
    print(f"\n{'='*60}")
    print("Build successful!")
    print(f"{'='*60}")
    print(f"Installer dir: dist/{exe_name}/")
    print()
except Exception as e:
    print(f"\nError building --onedir executable: {e}")
    sys.exit(1)
