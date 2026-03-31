# Build Instructions for SC Localization Editor

## Quick Start

**Build executable (recommended):**
```bash
cd scripts/build
.venv\Scripts\python.exe build_exe.py
```

**Build everything (executable + installer):**
```bash
cd scripts/build
build_all.bat
```

---

## Prerequisites

### Required Software

1. **Python 3.9+** - Already installed in your `.venv`
2. **PyInstaller** - Auto-installed by build scripts

### Download Inno Setup (Optional)

For creating the installer, download from: https://jrsoftware.org/isdl.php
- Install the Unicode version
- Default installation is fine

---

## Step 1: Build the Executable

Run the build script from the project root:

```bash
cd scripts/build
.venv\Scripts\python.exe build_exe.py
```

This will:
- Clean previous builds
- Package the application into a single `.exe` file
- Include all necessary data files (global.ini)
- Create `dist/SCLocalizationEditor-v0.1.0.exe`

**Testing the EXE:**
```bash
dist\SCLocalizationEditor-v0.1.0.exe
```

---

## Step 2: Create the Installer (Recommended)

### Option A: Using build_all.bat (Automated)

```bash
cd scripts/build
build_all.bat
```

This runs both build_exe.py and Inno Setup automatically.

### Option B: Using Inno Setup GUI

1. Open Inno Setup Compiler
2. File → Open → Select `installer.iss` (in project root)
3. Build → Compile
4. The installer will be created in project root

### Option C: Using Command Line

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

The installer will be created in the project root as:
```
SCLocalizationEditor-v0.1.0-Setup.exe
```

---

## Step 3: Test the Installer

1. Run the installer: `SCLocalizationEditor-v0.1.0-Setup.exe`
2. Follow the installation wizard
3. Test the installed application:
   - Launch the app
   - Load global.ini file
   - Edit some strings
   - Apply to game
   - Check that files are in the right location

---

## Distribution Package Contents

The installer includes:
- ✅ Main executable (`SCLocalizationEditor.exe`)
- ✅ Data files (default global.ini)
- ✅ Start menu shortcuts
- ✅ User config setup

---

## File Sizes (Approximate)

- **Executable**: ~60-100 MB (includes Python runtime, PyQt6, and all dependencies)
- **Installer**: ~30-50 MB (compressed)

---

## Version Update Checklist

For future versions:

1. Update version in:
   - `VERSION.TXT` (e.g., `0.2.0`)
   - `installer.iss` (line ~5)

2. Rebuild:
   ```bash
   cd scripts/build
   build_all.bat
   ```

3. Test installer and executable

4. Create release notes

5. Tag in git:
   ```bash
   git tag -a v0.2.0 -m "Release v0.2.0"
   git push origin v0.2.0
   ```

6. Create GitHub release with:
   - Release notes
   - Installer executable
   - Standalone executable

---

## Troubleshooting

### "PyInstaller not found"
```bash
.venv\Scripts\pip install pyinstaller
```

### "Module not found" errors
Make sure all dependencies are installed:
```bash
.venv\Scripts\pip install -r requirements.txt
```

### Executable is too large
This is normal for PyQt6 applications. PyInstaller bundles the entire Python runtime and all libraries (60-100MB is standard).

### Inno Setup not found
Install from: https://jrsoftware.org/isdl.php

Or compile the installer manually by:
1. Opening `installer.iss` in Inno Setup Compiler
2. Clicking Build → Compile

---

**Ready to build!** Run `build_all.bat` or follow the steps above.
