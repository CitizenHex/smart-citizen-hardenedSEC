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
- Everything else → "Other"

### 2. File Parsing (ini_parser.py)
- Line-by-line parsing (efficient for 83k+ lines)
- Strips comments (`;` prefix) and empty lines
- Splits on first `=` only (preserves plural markers in keys)
- Returns `Dict[key, value]` for fast lookups

### 3. GUI (main_window.py)
**Main Components**:
- **Toolbar**: 4 buttons (Load Base File, Restore Backup, Apply to Game, Help) + search/filter row
- **Tab 1 - Strings**: 4-column table (Category, Key, Original Value, Custom Value) + filters
- **Tab 2 - Config**: Path inputs for base global.ini and game installation
- **Tab 3 - About**: Help and branding
- **Footer**: Osiris DevWorks branding, donation links
- **Status Bar**: Shows loaded file count and operation status

**Filters**: Search text, Category dropdown, Status dropdown, Hide Unmodified checkbox

**Threading**: `FileLoaderWorker` (QThread) loads files without blocking UI, shows progress dialog

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

### 6. Auto-Update System (updater.py)
- **GitHub API**: Fetches latest release from `BeltaKoda/ScCompLangPackRemix` on startup
- **Version tracking**: Stores current version in `data/base_version.txt`
- **Download**: Only `-LIVE` releases; user prompted before downloading ~2.2MB zip
- **Threading**: `UpdateCheckerWorker` + `DownloadWorker` run in background threads
- **Extraction**: Downloads zip, extracts `data/Localization/english/global.ini` to `data/global.ini`

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

- **Source code**: `src/` folder
- **Configuration**: Windows Registry (HKEY_CURRENT_USER\Software\Osiris DevWorks\SC Localization Editor)
- **Version**: `VERSION.TXT` in project root
- **Base file version**: `data/base_version.txt` (tracks current auto-update version)
- **User overrides**: `%APPDATA%\Osiris DevWorks\SC Localization Editor\overrides.ini`
- **Assets**: `assets/` folder (Osiris DevWorks logo, PayPal/Venmo buttons)
- **Game files**: Configurable via Config tab; typically `Roberts Space Industries/StarCitizen/LIVE/data/Localization/english/`
- **Backups**: Same directory as applied file (`LIVE/data/Localization/english/global.ini.bak_*`)

## Development

### Setup
```bash
pip install -r requirements.txt
```

### Run
```bash
python src/main.py
```

### Build Executable
```bash
pyinstaller SCLocalizationEditor.spec
```

### Create Installer
```bash
# Requires Inno Setup installed
# Compile installer.iss file in Inno Setup IDE
```

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
