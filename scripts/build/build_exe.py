"""
Build script for creating SC Localization Editor executable

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
exe_name = f"SCLocalizationEditor-v{current_version}"

assets_dir = os.path.join(root_dir, 'assets')
icon_path  = os.path.join(assets_dir, 'logo.ico')

pyinstaller_args = [
    os.path.join(root_dir, 'src', 'main.py'),
    '--name', exe_name,
    '--onefile',
    '--windowed',
    '--icon', icon_path,
    '--add-data', f'{version_file}{os.pathsep}.',
    '--add-data', f'{assets_dir}{os.pathsep}assets',
    '--distpath', os.path.join(root_dir, 'dist'),
    '--workpath', os.path.join(root_dir, 'build'),
    '--specpath', root_dir,
    '--hidden-import=PyQt6',
    '--hidden-import=src.gui',
    '--hidden-import=src.parser',
    '--hidden-import=src.merger',
    '--hidden-import=src.models',
    '--hidden-import=src.utils',
]

print("Building executable with PyInstaller...")
print(f"  Output: {exe_name}.exe")
print()

try:
    PyInstaller.__main__.run(pyinstaller_args)
    print(f"\n{'='*60}")
    print("Build successful!")
    print(f"{'='*60}")
    print(f"Executable: dist/{exe_name}.exe")
    print()
except Exception as e:
    print(f"\nError building executable: {e}")
    sys.exit(1)
