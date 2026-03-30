# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SC Localization Editor is a PyQt6 GUI application for customizing Star Citizen localization strings. Users load a base global.ini file, make edits in the table, and apply changes directly to their game installation with automatic backup management.

**Current Version**: 0.2.0 (from VERSION.TXT)

## Architecture

The application follows a modular, layered architecture:

```
src/
├── main.py                 # Entry point
├── gui/
│   ├── main_window.py      # Main UI, toolbar, table, filters, backup, auto-update
│   └── config_tab.py       # Configuration settings (paths)
├── models/
│   └── string_model.py     # StringEntry dataclass
├── parser/
│   └── ini_parser.py       # INI file parsing
├── merger/
│   └── ini_merger.py       # File writing utilities
└── utils/
    ├── settings.py         # QSettings wrapper for Windows Registry
    ├── version.py          # Version reader from VERSION.TXT
    ├── updater.py          # GitHub API check + auto-update
    ├── overrides_manager.py # Overrides persistence & bootstrap
    └── __init__.py
```

## Key Design Patterns

### 1. Data Model (StringEntry)
Located in `string_model.py`, each localization string is a dataclass with:
- `key`: The localization key
- `source_file`: "global" (vehicles.ini support removed)
- `category`: Auto-extracted from key prefix
- `original_value`: Value from loaded file
- `custom_value`: User's edit (empty if unmodified)
- `status`: "Modified", "Unmodified", or "New"

**Category extraction rules**:
- `vehicle_Name*` → "Ships"
- `item_Name(SHLD|POWR|COOL|QDRV|JUMP)_*` → "Ship Components"
- Entries from `contracts.ini` → "Missions" (assigned directly during parsing)
- Everything else → "Other"

### 2. File Parsing (ini_parser.py)
- Line-by-line parsing (efficient for 83k+ lines)
- Strips comments (`;` prefix) and empty lines
- Splits on first `=` only (preserves plural markers in keys)
- Returns `Dict[key, value]` for fast lookups

### 3. GUI (main_window.py)
**Main Components**:
- **Toolbar**: 4 buttons (Load Base File, Restore Backup, Apply to Game, Help) + search/filter row
- **Tab 1 - Strings**: 6-column table (Category, Key, Default Value, Current Value, Custom Value, Status) + filters
- **Tab 2 - Config**: Path inputs for base global.ini and game installation
- **Tab 3 - About**: Project info, features, donation links
- **Footer**: Osiris DevWorks logo, GitHub attribution links (MrKraken, ExoAE, BeltaKoda), donation buttons
- **Status Bar**: Shows base file version and contracts.ini version (e.g., `Base: 4.7.0-LIVE ✓  |  Contracts: 2026-03-28 ✓`)
- **Window Icon**: Displays logo.ico in taskbar and window title bar

**Filters**: Search text, Category dropdown (Ships, Ship Components, Missions, Other), Status dropdown, Hide Unmodified checkbox

**Threading**: `FileLoaderWorker`, `UpdateCheckerWorker`, `DownloadWorker`, `ContractsCheckerWorker`, `ContractsDownloadWorker` all run in QThread with progress dialogs

### 4. Backup System
Located in `main_window.py:apply_to_game()`:
- On Apply, backs up existing `global.ini` to `global.ini.bak_YYYYMMDD_HHMMSS`
- Keeps max 5 backups; deletes oldest when limit reached
- Restore Backup dialog lets users select and restore from backups

### 5. Settings (settings.py)
Uses `QSettings` with Osiris DevWorks organization (Windows Registry):
- `base_global_path` - Path to base global.ini file
- `game_install_path` - Star Citizen installation root
- `window_geometry`, `window_state` - Window restoration
- `get_overrides_path()` - Returns `%APPDATA%\Osiris DevWorks\SC Localization Editor\overrides.ini`

### 6. Auto-Update System - Global.ini (updater.py)
- **GitHub API**: Fetches latest release from `BeltaKoda/ScCompLangPackRemix` on startup
- **Version tracking**: Stores current version in `data/base_version.txt`
- **Download**: Only `-LIVE` releases; user prompted before downloading ~2.2MB zip
- **Threading**: `UpdateCheckerWorker` + `DownloadWorker` run in background threads
- **Extraction**: Downloads zip, extracts `data/Localization/english/global.ini` to `data/global.ini`

### 6b. Auto-Update System - Contracts.ini (updater.py)
- **GitHub API**: Checks latest commit for `contracts.ini` in `MrKraken/StarStrings` on startup (parallel to base file check)
- **Version tracking**: Stores commit SHA and date in `data/contracts_version.txt` (format: `sha\ndate`)
- **Download**: Downloads raw mission contract strings file (~49 KB); user prompted before download
- **Threading**: `ContractsCheckerWorker` + `ContractsDownloadWorker` run in background (independent of base file)
- **Merging**: Loaded via `load_source_files(base_path, overrides_path, contracts_path)` with category='Missions'
- **Precedence**: Contracts entries override global.ini entries for overlapping keys
- **Graceful Degradation**: If contracts unavailable, app continues with global.ini only (no errors)

### 7. Overrides Persistence (overrides_manager.py)
- **Location**: `%APPDATA%\Osiris DevWorks\SC Localization Editor\overrides.ini`
- **Format**: Plain `key=value` per line (only modified entries)
- **Save triggers**: On "Apply to Game" and on app close via `closeEvent()`
- **Load**: Automatically applied when loading any base file
- **Bootstrap**: On first run, diffs `data/global.ini` vs `LIVE/.../global.ini` to extract existing customizations

## Workflow

### Standard Usage
1. **Auto-Update** (on startup): App checks GitHub for latest base file version, prompts if newer available
2. **Load File**: Click "Load Base File" → select base global.ini → file loads in background with progress dialog
3. **Edit**: Use filters to find strings, double-click Custom Value column to edit
4. **Persist**: Edits saved to `overrides.ini` automatically on Apply or Close
5. **Apply**: Click "Apply to Game" → writes merged file (base + overrides) to game, creates backup
6. **Restore**: Click "Restore Backup" → file dialog → select backup to restore (overrides still active)

### Migration Scenario (after Star Citizen update)
1. Load new base file (newer P4K means loose file is stale and incomplete)
2. App automatically re-applies saved `overrides.ini` on top
3. All user customizations show as "Modified" (green)
4. New keys from the update are present with base values
5. Click Apply to Game → writes complete merged file with all keys
6. Game is now fully playable with all user customizations intact

## File Locations

### Project Files
- **Source code**: `src/` folder
- **Version**: `VERSION.TXT` in project root (single source of truth for all builds)
- **Build scripts**: `scripts/build/build_exe.py` (primary build tool), `scripts/build/build_all.bat` (build exe + installer)
- **Assets**: `src/assets/` folder (Osiris DevWorks logo, PayPal/Venmo buttons)
- **Build specs**: `SCLocalizationEditor.spec`, `SCLocalizationEditor-v0.1.0.spec`, `SCLocalizationEditor-v0.2.0.spec` (versioned backups; use current .spec)
- **Installer config**: `installer.iss` (Inno Setup script)

### Data & Cached Files
- **Base file cache**: `data/global.ini` (extracted from auto-update or manual load)
- **Base file version**: `data/base_version.txt` (tracks current global.ini auto-update release version)
- **Base file backup**: `data/global.ini.bak` (reference backup for migration detection)
- **Contracts file cache**: `data/contracts.ini` (mission strings downloaded from MrKraken/StarStrings)
- **Contracts version**: `data/contracts_version.txt` (tracks current contracts.ini commit SHA and date)
- **Mission rewards**: `data/mission_blueprint_rewards.json` (if applicable to future features)

### User Settings (Windows)
- **Configuration**: Windows Registry at `HKEY_CURRENT_USER\Software\Osiris DevWorks\SC Localization Editor`
  - Stores: `base_global_path`, `game_install_path`, `window_geometry`, `window_state`
- **User overrides**: `%APPDATA%\Osiris DevWorks\SC Localization Editor\overrides.ini` (custom edits, persisted on Apply)

### Game Installation
- **Game files location**: Configurable via Config tab; typically `Roberts Space Industries/StarCitizen/LIVE/data/Localization/english/`
- **Game backups**: Same directory as applied file (`LIVE/data/Localization/english/global.ini.bak_YYYYMMDD_HHMMSS`)

## Development

### Setup
```bash
pip install -r requirements.txt
```

### Run Development Version
```bash
python src/main.py
```

### Build Executable

**Recommended: Use the build script** (handles PyInstaller, versioning, and cleanup):

```bash
cd scripts/build
python build_exe.py
```

This creates `dist/SCLocalizationEditor-v{VERSION}.exe` where VERSION comes from `VERSION.TXT`.

**With automatic version increment:**
```bash
cd scripts/build
python build_exe.py --increment patch   # 0.2.0 → 0.2.1
python build_exe.py --increment minor   # 0.2.0 → 0.3.0
python build_exe.py --increment major   # 0.2.0 → 1.0.0
```

**Manual PyInstaller (not recommended):**
```bash
pyinstaller SCLocalizationEditor.spec
```

### Build Installer (Windows)

Requires [Inno Setup](https://jrsoftware.org/isdl.php) installed.

**Option A: Automated** (builds exe + installer):
```bash
cd scripts/build
build_all.bat
```

**Option B: Command line** (after building exe):
```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

**Option C: GUI**:
1. Open Inno Setup Compiler
2. File → Open → Select `installer.iss`
3. Build → Compile

Output: `SCLocalizationEditor-v{VERSION}-Setup.exe` in project root

### Version Management

Version is stored in a single file: **`VERSION.TXT`** (e.g., `0.2.0`)

When building:
- `build_exe.py` reads VERSION.TXT and names output exe accordingly
- `installer.iss` must be manually updated to match (line ~5: `AppVersion` and version in filename)

**Version update workflow:**
1. Edit `VERSION.TXT` to new version (e.g., `0.3.0`)
2. Update `installer.iss` line 5: `AppVersion=0.3.0`
3. Run `cd scripts/build && build_all.bat`
4. Test the installer and executable
5. Commit changes and tag: `git tag -a v0.3.0 -m "Release v0.3.0"`
6. Create GitHub release with both exe and installer

## Release Checklist

Follow this checklist when cutting a new release:

1. **Increment version**
   - Update `VERSION.TXT` (e.g., `0.2.0` → `0.3.0`)
   - Update `installer.iss` line ~5 with new `AppVersion` and version in output filename

2. **Build & Test**
   ```bash
   cd scripts/build
   build_all.bat
   ```
   - Test standalone exe: `dist/SCLocalizationEditor-v0.3.0.exe`
   - Test installer: `SCLocalizationEditor-v0.3.0-Setup.exe`

3. **Commit & Tag**
   ```bash
   git add VERSION.TXT installer.iss
   git commit -m "Bump version to 0.3.0"
   git tag -a v0.3.0 -m "Release v0.3.0"
   git push origin main
   git push origin v0.3.0
   ```

4. **Create GitHub Release**
   - Use the git tag to create a release
   - Attach both files: `dist/SCLocalizationEditor-v0.3.0.exe` and `SCLocalizationEditor-v0.3.0-Setup.exe`
   - Add release notes (changes from previous version)

5. **Optional: Discord Notification**
   - Script available at `scripts/discord_notify.py` (if webhook configured)

## Key Implementation Details

### Threading & UI Responsiveness
- File loading happens in `FileLoaderWorker` thread to prevent UI freeze
- Update checking happens in `UpdateCheckerWorker` thread on startup
- Base file download happens in `DownloadWorker` thread with progress dialog
- Worker threads properly cleaned up with `quit()` + `wait()` to prevent hangs
- UI signals blocked during bulk table updates to avoid lag
- Progress callbacks wrapped in try/except to prevent blocking on errors

### Table Filtering
- Uses `setRowHidden()` on each row (no proxy model for simplicity)
- 300ms debounce on search input to avoid excessive filtering
- Filters: text (key or value), category, status, hide unmodified

### Cell Editing
- `SelectAllDelegate` for in-place editing (auto-selects text)
- Double-click Custom Value column to edit
- Right-click context menu: Edit, Reset to Original, Copy Key

### Status Colors
- Modified: Green (#4CAF50)
- Unmodified: Gray (#999)
- New: Orange (#FF9800)

### Window State
- Geometry (position/size) persisted via QSettings
- Window state restored on startup

## Dependencies

- **PyQt6** (>=6.10.0) - GUI framework
- **pyinstaller** (>=6.3.0) - Executable builder
- **pyperclip** (>=1.8.2) - Clipboard access (for Copy Key context menu)

## Common Issues

### "Device or resource busy" when deleting backups or renaming directories
- Close IDE/file explorer with the directory open
- Run operation in a separate terminal
- Check that no Game Launcher instances are running

### QSettings not persisting
- QSettings uses Windows Registry
- Verify organization name is "Osiris DevWorks" and app name is "SC Localization Editor"
- Registry path: `HKEY_CURRENT_USER\Software\Osiris DevWorks\SC Localization Editor`

### File won't load or "Not a valid INI file"
- Ensure file is in UTF-8 encoding
- Verify file has `key=value` pairs (one per line)
- Check for duplicate keys (parser uses last value)

### Large file performance
- Parser uses line-by-line iteration (no full load into memory)
- Threading prevents UI freeze during load
- Should handle 83k+ lines smoothly

## Future Enhancements

From CLAUDE.md history:
- Diff view for before/after comparisons
- Batch find & replace
- Import/export to other formats (CSV, Excel)
- Profile/preset support for different customization sets
- Real-time preview of game file
- Undo/redo history
- Dark/light theme toggle

## Contact

Osiris DevWorks - https://github.com/OsirisDevworks/sc-localization-editor

## Recent Changes (v0.2.0)
- **Auto-update system**: Background GitHub API check for latest base file
- **Overrides persistence**: Custom edits saved to AppData, loaded automatically on next session
- **Migration support**: Load new base file → overrides auto-apply → seamless migration
- **Bootstrap on first run**: Diffs existing game file vs reference to extract customizations
- **Threading improvements**: Fixed "not responding" hangs during downloads
- **Status bar indicators**: Shows "Base: 4.7.0-LIVE ✓" and "N overrides active"

## Recent Changes (v0.1.1)
- Improved Config tab with clearer path descriptions and examples
- Enhanced UI design consistency
- Help dialog with usage instructions
- Directory selection in installer
- Backup system with up to 5 versions
- Automatic game directory detection
- Footer with branding and donation links
