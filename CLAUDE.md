# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SC Localization Editor is a PyQt6 GUI application for customizing Star Citizen localization strings. The app supports multiple configurable data sources with user-defined merge hierarchy. Users configure sources (Global, Contracts, Components, Ships), specify merge priority, make edits in the table, and apply changes directly to their game installation with automatic backup management.

**Current Version**: 0.3.0 (from VERSION.TXT)

**Key Features**:
- Multi-source data configuration (Global, Contracts, Components, Ships, User)
- User-configurable merge hierarchy (drag-and-drop priority)
- Auto-update from external sources (GitHub, local files)
- Persistent customizations via overrides.ini
- Backup and restore system
- Category-based filtering with Mission detection

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

## Data Flow & System Architecture

### Data Pipeline
```
Settings (QSettings)
  ├── Data sources (Global, Contracts, Components, Ships, User)
  ├── Merge hierarchy (user-configurable order)
  └── Auto-update flags
         ↓
Load Sources → Merge by Hierarchy → Parser → StringEntry objects → GUI Table
                                                                       ↓
                                                               Filters/Search
                                                                       ↓
                                                               User edits
                                                                       ↓
                                                          Store in overrides.ini
                                                                       ↓
                                                  Apply to Game (merge + write)
```

### Source Configuration System
The app supports five configurable data sources:
1. **Global** - Base localization file (pre-configured to MrKraken StarStrings repo)
2. **Contracts** - Mission strings (disabled by default, merged in Global)
3. **Components** - Ship component strings (empty by default)
4. **Ships** - Ship names (empty by default)
5. **User** - User customizations (auto-managed in AppData as overrides.ini)

### Merge Hierarchy
Users specify merge order via Config tab drag-drop interface. Sources are merged sequentially:
1. Start with Global as base
2. Apply Contracts (overwrites Global keys)
3. Apply Components (overwrites previous keys)
4. Apply Ships (overwrites previous keys)
5. Apply User edits (highest priority, always overwrites all sources)

Result: User customizations always win, ensuring edits are never lost during source updates.

### StringEntry Creation
When loading, the parser creates `StringEntry` objects:
- `original_value`: Final value after merging all sources (baseline for comparison)
- `custom_value`: User's edit (empty if not modified, populated when user edits)
- `status`: Calculated based on source origin:
  - **Unmodified**: From base source, not overridden
  - **Modified**: Overridden by higher-priority source or user edit
  - **New**: Exists only in overrides (user-added entry)

## Key Design Patterns

### 1. Data Model (StringEntry)
Located in `string_model.py`, each localization string is a dataclass with:
- `key`: The localization key
- `source_file`: "global" (vehicles.ini support removed)
- `category`: Auto-extracted from key prefix
- `original_value`: Value from loaded file (base + contracts merged)
- `custom_value`: User's edit (empty if unmodified)
- `status`: "Modified", "Unmodified", or "New"

**Status determination logic**:
- **Unmodified**: `custom_value` is empty AND no override exists in overrides.ini (original value from file is unchanged)
- **Modified**: `custom_value` differs from `original_value` (user has edited)
- **New**: Entry exists in overrides.ini but NOT in the base file (user added a new string, rare edge case)

**Category extraction rules** (from `string_model.py`):
- `vehicle_Name*` → "Ships"
- `item_Name(SHLD|POWR|COOL|QDRV|JUMP)_*` → "Ship Components"
- Mission-related keys → "Missions":
  - Starts with `shubin_` or `Shubin_` (Shubin mining)
  - Starts with `blackbox_` or `BlackBox_` (Black box recovery)
  - Starts with `hockrow_` or `Hockrow_` (Hockrow facility)
  - Starts with `contract_`, `Contract_`, `mission_`, `Mission_`, `jt_`, or `JT_` (generic mission types)
- Everything else → "Other"

### 2. Merge Engine (ini_merger.py)

**Core Function**: `merge_sources_by_hierarchy(sources_dict, hierarchy, user_overrides)`
- Takes dict of sources and merge hierarchy list
- Merges in order: early sources are base, later sources overwrite
- User overrides applied last (always highest priority)
- Returns final merged dict with all keys resolved

**Algorithm**:
```
1. Start with empty result
2. Load source at hierarchy[0]: result = sources[name].copy()
3. For each source in hierarchy[1:]:
   - For each key in source: result[key] = source[key]  (overwrite)
4. For each key in user_overrides: result[key] = user_overrides[key]  (highest priority)
5. Return merged result
```

**Key Feature**: User customizations are always preserved; they're never overwritten by source updates.

### 2b. File Parsing (ini_parser.py)
- Line-by-line parsing (efficient for 83k+ lines)
- Strips comments (`;` prefix) and empty lines
- Splits on first `=` only (preserves plural markers in keys)
- Returns `Dict[key, value]` for fast lookups
- **New**: `load_sources_from_settings()` loads all configured sources from QSettings
- **New**: `load_source_files(sources_dict, hierarchy, user_overrides)` merges and creates StringEntry list

### 3. GUI (main_window.py)
**Main Components**:
- **Toolbar**: 4 buttons (Load Base File, Restore Backup, Apply to Game, Help) + search/filter row
- **Tab 1 - Strings**: 6-column table (Category, Key, Default Value, Current Value, Custom Value, Status) + filters
  - **Default Value**: Shows baseline value from merged sources (for comparison)
  - **Current Value**: Shows original_value from loaded/merged sources
  - **Custom Value**: User's edits (populated when user modifies)
- **Tab 2 - Config**: Data source configuration with drag-drop hierarchy
  - Source configuration widgets: path/URL, enable/disable, auto-update flags
  - Status indicators per source (color-coded: green/red/yellow)
  - Save Configuration button (triggers merge)
  - Preview Merge button (shows merge order and statistics)
  - Game installation path setting
- **Tab 3 - About**: Project info, features, donation links
- **Footer**: Osiris DevWorks logo, GitHub attribution links (MrKraken, ExoAE, BeltaKoda), donation buttons
- **Status Bar**: Shows sync status for each configured source in merge order
  - Dynamic per-source display (e.g., `Global: 4.7.0-LIVE ✓  |  Contracts: 2026-03-28 ✓`)
  - Updates after source downloads or app startup
- **Window Icon**: Displays logo.ico in taskbar and window title bar

**Filters**: 
- Search text (searches key and value)
- Category dropdown (Ships, Ship Components, Missions, Other) - always shows all standard categories
- Status dropdown (Modified, Unmodified, New)
- Hide Unmodified checkbox
- Debounced search (300ms) to prevent excessive filtering

**Threading**: `FileLoaderWorker`, `UpdateCheckerWorker`, `DownloadWorker`, `ContractsCheckerWorker`, `ContractsDownloadWorker` all run in QThread with progress dialogs

### 4. Backup System
Located in `main_window.py:apply_to_game()`:
- On Apply, backs up existing `global.ini` to `global.ini.bak_YYYYMMDD_HHMMSS`
- Keeps max 5 backups; deletes oldest when limit reached
- Restore Backup dialog lets users select and restore from backups

### 5. Configuration System (settings.py & config_tab.py)

**Settings Storage** (`settings.py`):
Uses `QSettings` with Osiris DevWorks organization (Windows Registry) at `HKEY_CURRENT_USER\Software\Osiris DevWorks\SC Localization Editor`.

**Data Source Keys**:
- `data_sources/{source_name}/path` - Path or URL for each source (global, contracts, components, ships, user)
- `data_sources/{source_name}/enabled` - Enable/disable each source
- `merge_hierarchy` - Ordered list of source names for merge order
- `source_auto_update/{source_name}` - Auto-update flag per source
- `game_install_path` - Star Citizen installation root
- `window_geometry`, `window_state` - Window restoration

**Config Tab** (`config_tab.py`):
- **Source Configuration Widgets**: One per data source (Global, Contracts, Components, Ships, User)
  - Enable/disable checkbox
  - Path/URL input field
  - Browse button for local files
  - Auto-update checkbox (User source disabled)
  - Status indicator (●) with color coding: Green=available, Red=missing, Yellow=unconfigured
- **Hierarchy Management**: Sources listed for drag-drop reordering (drag to set merge priority)
- **Save Configuration Button**: Triggers merge of configured sources
- **Preview Merge Button**: Shows merge order, key counts, and status breakdown

**Migration** (`migrate_legacy_settings()`):
- On first run with new version, converts old settings to new format
- Pre-configures Global source to MrKraken StarStrings repo
- Leaves Contracts, Components, Ships empty by default (user configurable)
- Sets default hierarchy: [global, contracts, user]

### 6. Auto-Update System (updater.py)

**Multi-Source Downloads**:
The app can auto-download and update any configured source (Global, Contracts, Components, Ships) from GitHub or local URLs. Each source runs independently in background threads.

**Base File (Global Source)**:
- **Default URL**: Pre-configured to MrKraken StarStrings repo: `https://raw.githubusercontent.com/MrKraken/StarStrings/master/Data/Localization/english/global.ini`
- **Storage**: Downloaded and saved as `data/base.ini` (renamed to avoid confusion with game's global.ini)
- **Version tracking**: Stores current version in `data/base_version.txt`
- **Download**: User prompted before downloading ~2.2MB zip; only -LIVE releases accepted
- **Threading**: `UpdateCheckerWorker` + `DownloadWorker` run in background threads
- **Extraction**: Downloads zip, extracts `data/Localization/english/global.ini` from repo, saves locally as `data/base.ini`

**Other Sources**:
- User can configure any source to download from a URL or load from local file
- File naming: `components.ini`, `ships.ini`, `contracts.ini` (exact naming required)
- Graceful degradation: If source unavailable, app can skip it and merge remaining sources
- Error dialog on failure with options: Specify new location, Skip source, or Cancel merge

**File Naming Clarity**:
- `data/base.ini` - App's internal base file (reference/cache from external sources)
- `global.ini` - Game installation file only (`LIVE/data/Localization/english/global.ini`)
- This naming prevents confusion between the app's base file and the game's actual file

### 7. Overrides Persistence (overrides_manager.py)
- **Location**: `%APPDATA%\Osiris DevWorks\SC Localization Editor\overrides.ini`
- **Format**: Plain `key=value` per line (only modified entries)
- **Save triggers**: On "Apply to Game" and on app close via `closeEvent()`
- **Load**: Automatically applied when loading sources, merged as highest priority
- **Bootstrap on First Run**: App compares `data/base.ini` (reference from external source) vs existing game file (`LIVE/.../global.ini`). Any differences are assumed to be user customizations and extracted into overrides.ini. This allows the app to "remember" customizations from before it was installed, so users don't lose their edits when switching to this tool.

## Workflow

### Standard Usage
1. **First Run**: App migrates old settings (if any) and pre-configures Global source to MrKraken StarStrings repo
2. **Auto-Load on Startup**: App loads configured sources, merges them in hierarchy order, displays result in table
3. **Configure Sources** (optional): 
   - Click Config tab
   - Add/edit sources (Global, Contracts, Components, Ships)
   - Drag to reorder hierarchy (merge priority)
   - Click "Save Configuration & Merge" to apply new settings
4. **Edit Strings**:
   - Use search to find strings by key or value
   - Use Category filter (Ships, Ship Components, Missions, Other)
   - Double-click Custom Value column to edit
   - Changes highlighted with color (green=Modified, orange=New, gray=Unmodified)
5. **Apply Changes**:
   - Click "Apply to Game" → app merges all sources + user edits → writes to game
   - Backup created automatically
   - Edits saved to `overrides.ini` in AppData
6. **Restore from Backup** (if needed):
   - Click "Restore Backup" → select backup file → restores, overrides still active

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
  - Requires admin privileges to create Start Menu shortcuts
  - Configures version, paths, and permissions for Windows installation

### Data & Cached Files

**Application directory** (`./data/` - auto-created on first run):
- **Base file cache**: `data/base.ini` (app's internal base file, extracted from configured Global source)
- **Base file version**: `data/base_version.txt` (tracks current base file auto-update release version)
- **Source files**: Other sources can be cached here if needed (components.ini, ships.ini, contracts.ini)
- **Mission rewards**: `data/mission_blueprint_rewards.json` (placeholder for future features)

### User Settings (Windows)
- **Configuration**: Windows Registry at `HKEY_CURRENT_USER\Software\Osiris DevWorks\SC Localization Editor`
  - Stores: `base_global_path`, `game_install_path`, `window_geometry`, `window_state`
- **User overrides**: `%APPDATA%\Osiris DevWorks\SC Localization Editor\overrides.ini` (custom edits, persisted on Apply)

### Game Installation
- **Game files location**: Configurable via Config tab; typically `Roberts Space Industries/StarCitizen/LIVE/data/Localization/english/`
- **Game backups**: Same directory as applied file (`LIVE/data/Localization/english/global.ini.bak_YYYYMMDD_HHMMSS`)

## Development

### Quick Commands

**Setup and run:**
```bash
pip install -r requirements.txt
python src/main.py
```

**Build and release:**
```bash
cd scripts/build
python build_exe.py                    # Build exe only
build_all.bat                          # Build exe + installer
python build_exe.py --increment minor  # Build with version bump
```

### Requirements

- **Python 3.9+** (Windows 10/11)
- Requires Windows; uses Windows Registry for settings and Windows-only APIs

### Setup

```bash
pip install -r requirements.txt
```

This installs: PyQt6 (GUI), PyInstaller (builds), pyperclip (clipboard)

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

5. **Discord Notification** (optional)
   - On release, GitHub Actions automatically notifies Discord via `scripts/discord_notify.py`
   - **Setup**: Add `DISCORD_RELEASE_WEBHOOK_URL` secret to GitHub repository settings
   - Webhook posts version and release notes to configured Discord channel
   - Continues gracefully if webhook URL is not configured

## Key Implementation Details

### Threading & UI Responsiveness

The app uses `QThread` workers to keep the UI responsive during I/O-bound operations (file reads, network requests). Each worker is a separate class that inherits `QObject` and lives in its own thread.

**Worker threads used**:
- **FileLoaderWorker** (main_window.py): Loads base file from disk, parses, extracts categories. Takes ~1-2s for 83k+ lines.
- **UpdateCheckerWorker** (updater.py): Checks GitHub API for latest base file version on startup (non-blocking check).
- **DownloadWorker** (updater.py): Downloads ~2.2MB zip from GitHub, extracts, shows progress dialog.
- **ContractsCheckerWorker** (updater.py): Checks latest contracts.ini commit SHA in parallel with base file check.
- **ContractsDownloadWorker** (updater.py): Downloads ~49 KB mission strings file.

**Threading best practices used**:
- Workers emit `finished()` signal when done; slots handle the result
- `quit()` + `wait()` properly shut down threads (prevents orphaned threads and hangs)
- UI signals are blocked during bulk table updates with `setUpdatesEnabled(False)` to avoid lag
- Progress callbacks wrapped in try/except to prevent exceptions in worker threads from blocking

**When modifying**: Ensure new long-running operations use workers, don't block the main thread. Always call `quit()` + `wait()` to clean up.

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

## Common Modification Points

When making changes, look here for the relevant system:

| Task | File | Key Class/Function |
|------|------|-------------------|
| Add a new column to the table | `main_window.py` | `TableModel.setData()`, `setup_string_table()` |
| Add a new filter option | `main_window.py` | `apply_filters()`, `on_filter_changed()` |
| Change category extraction logic | `string_model.py` | `category` property |
| Modify INI parsing (e.g., handle new format) | `ini_parser.py` | `parse_ini_file()` |
| Change how overrides are saved/loaded | `overrides_manager.py` | `save_overrides()`, `load_overrides()` |
| Add a new status type | `string_model.py` | `status` property |
| Modify GitHub auto-update sources | `updater.py` | `check_for_updates()`, `download_base_file()`, `check_contracts()` |
| Change backup retention policy | `main_window.py` | `manage_backups()` |
| Modify file merge logic | `ini_merger.py` | `merge_and_write()` |

## Debugging Tips

- **Registry issues**: Check `HKEY_CURRENT_USER\Software\Osiris DevWorks\SC Localization Editor` for stored settings. Use `regedit` to inspect or clear values if settings corrupt.
- **Threading hangs**: Worker threads signal `finished()` when complete. If UI appears frozen, check that `worker.quit()` + `worker.wait()` are called in the slot.
- **File encoding**: Parser expects UTF-8. Files with BOM or other encodings will fail silently. Use Notepad++ or VS Code to check/convert.
- **Overrides not loading**: Check `%APPDATA%\Osiris DevWorks\SC Localization Editor\overrides.ini` exists and has correct format (`key=value` per line).
- **GitHub API rate limit**: Requests use unauthenticated API; limit is 60 requests/hour per IP. Errors caught and logged to console.

## Testing

**Current status**: No automated tests exist. Manual testing is performed on:
- File loading with various encodings and sizes (up to 83k+ lines)
- Editor and filter functionality
- Backup/restore workflows
- Auto-update checks and downloads
- Multi-threaded operations for UI responsiveness
- Windows Registry persistence

Test contributions welcome—use pytest framework if adding tests.

**Manual test checklist after code changes**:
1. Run `python src/main.py` and verify app starts
2. Load a base file and check table renders correctly
3. Edit a value and apply to game—verify file written and backup created
4. Restart app and verify edits persist
5. Use filters and search—verify they work as expected
6. Check Windows Registry under Osiris DevWorks for persistence

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
