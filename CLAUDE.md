# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SC Localization Editor is a PyQt6 GUI application for customizing Star Citizen localization strings. The app supports multiple configurable data sources with user-defined merge hierarchy. Users configure sources (Global, Contracts, Components, Ships), specify merge priority, make edits in the table, and apply changes directly to their game installation with automatic backup management.

**Current Version**: 0.5.3 (from VERSION.TXT)

**Key Features**:
- Multi-source data configuration (Global, Contracts, Components, Ships, Commodities, Gear, User)
- User-configurable merge hierarchy (drag-and-drop priority)
- Auto-update from external sources (GitHub, local files)
- Persistent customizations via overrides.ini
- Backup and restore system (stored in `Documents\SC Localization Editor\backups\`)
- Category-based filtering (Ships, Ship Components, Gear, Commodities, Missions, Other)
- Ship Favorites (★ prefix toggle, filterable)
- Stats enhancements (auto-generated ship/component/weapon descriptions via DataForge extraction)
- P4K extraction pipeline (extract Data.p4k and convert to DataForge entity XMLs)
- Sortable table columns
- Clear Localization (delete game's global.ini to revert to vanilla)

## Architecture

The application follows a modular, layered architecture:

```
src/
├── main.py                 # Entry point
├── gui/
│   ├── main_window.py      # Main UI, toolbar, table, filters, backup, auto-update, DataForge extraction
│   └── config_tab.py       # Configuration settings (paths, sources, hierarchy, DataForge extraction)
├── models/
│   └── string_model.py     # StringEntry dataclass, category extraction logic
├── parser/
│   └── ini_parser.py       # INI file parsing, source loading, merging
├── merger/
│   └── ini_merger.py       # File writing utilities
└── utils/
    ├── settings.py         # QSettings wrapper for Windows Registry, source paths
    ├── version.py          # Version reader from VERSION.TXT
    ├── updater.py          # GitHub API check + auto-update for all sources
    ├── pak_extractor.py    # P4K extraction + DataForge conversion pipeline
    ├── overrides_manager.py # Overrides persistence & bootstrap
    └── __init__.py

scripts/
├── generate_stats_ini.py   # DataForge XML → stats INI files (ships, components, weapons)
└── extract_components.py   # base.ini delta extraction vs stock vanilla

assets/
└── unp4k/
    ├── unp4k.exe          # P4K extractor (extracts Game2.dcb from Data.p4k)
    └── unforge.exe        # DataForge converter (converts DataForge.dcb → entity XMLs)
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
The app supports seven configurable data sources:
1. **Global** - Base localization file (pre-configured to MrKraken StarStrings repo)
2. **Contracts** - Mission strings (pre-configured to MrKraken StarStrings repo)
3. **Components** - Ship component strings (derived from MrKraken's modifications via `extract_components.py`)
4. **Ships** - Ship names and flight stats (pre-configured to Osiris-DevWorks repo)
5. **Commodities** - Commodity item names (pre-configured to Osiris-DevWorks repo)
6. **Gear** - FPS equipment and weapons (pre-configured to Osiris-DevWorks repo)
7. **User** - User customizations (auto-managed as overrides.ini)

### Merge Hierarchy
Users specify merge order via Config tab drag-drop interface. Sources are merged sequentially:
1. Start with Global as base
2. Apply Contracts (overwrites Global keys)
3. Apply Components (overwrites previous keys)
4. Apply Ships (overwrites previous keys)
5. Apply Commodities (overwrites previous keys)
6. Apply Gear (overwrites previous keys)
7. Apply User edits (highest priority, always overwrites all sources)

Result: User customizations always win, ensuring edits are never lost during source updates. Default hierarchy: [global, contracts, components, ships, commodities, gear, user]

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
- `vehicle_Name*` or `vehicle_Desc*` → "Ships"
- `item_Name(SHLD|POWR|COOL|QDRV|JUMP|MISL|GMISL|BOMB)_*` → "Ship Components" (shields, power plants, coolers, quantum drives, jump modules, ship weapons, bombs)
- Turrets with `item_Name_Turret*` or `item_Desc_Turret*` → "Ship Components"
- Ship weapons with size designator (e.g., `_S1`, `_S02`) → "Ship Components"
- `item_Name_*` or `item_Desc_*` (underscore directly after) → "Gear" (FPS weapons, armor, tools)
- FPS weapons without underscore (e.g., `item_NameGMNI_rifle_*`) → "Gear"
- `items_commodities_*` → "Commodities"
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
  - **Extract DataForge from P4K** button: Extracts entity XMLs from game's Data.p4k; runs in background thread with progress dialog
  - **DataForge cache freshness** indicator: Shows when cache was last extracted; prompts to re-extract if stale
  - Game installation path setting
  - Stats enabled toggle
- **Tab 3 - About**: Project info, features, donation links
- **Footer**: Osiris DevWorks logo, GitHub attribution links (MrKraken, ExoAE, BeltaKoda), donation buttons
- **Status Bar**: Shows sync status for each configured source in merge order
  - Dynamic per-source display (e.g., `Global: 4.7.0-LIVE ✓  |  Contracts: 2026-03-28 ✓`)
  - Updates after source downloads or app startup
- **Window Icon**: Displays logo.ico in taskbar and window title bar

**Filters**: 
- Search text (searches key and value)
- Category dropdown (Ships, Ship Components, Gear, Commodities, Missions, Other) - shows all auto-extracted categories
- Status dropdown (Modified, Unmodified, New)
- Hide Unmodified checkbox
- "★ Favorites Only" checkbox (shows only entries with the favorite prefix in custom_value)
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
- Pre-configures sources:
  - Global & Contracts: MrKraken StarStrings repo
  - Ships, Commodities, Gear: Osiris-DevWorks repos
  - Components: Empty by default (user configurable; see `extract_components.py`)
- Sets default hierarchy: [global, contracts, components, ships, commodities, gear, user]
- Enables auto-update for Global, Contracts, Ships, Commodities, Gear by default (User source excluded)

### 6. Auto-Update System (updater.py)

**Multi-Source Downloads**:
The app can auto-download and update any configured source (Global, Contracts, Components, Ships) from GitHub or local URLs. Each source runs independently in background threads.

**Base File (Global Source)**:
- **Default URL**: Pre-configured to MrKraken StarStrings repo: `https://raw.githubusercontent.com/MrKraken/StarStrings/master/Data/Localization/english/global.ini`
- **Storage**: Downloaded and cached as `base.ini` in `Documents\SC Localization Editor\cache\`
- **Naming**: Saved as `base.ini` (not `global.ini`) to avoid confusion with the game's global.ini file
- **Version tracking**: Stores current version in `base_version.txt` (same cache directory)
- **Download**: User prompted before downloading ~2.2MB zip; only -LIVE releases accepted
- **Threading**: `UpdateCheckerWorker` + `DownloadWorker` run in background threads
- **Extraction**: Downloads zip, extracts `data/Localization/english/global.ini` from repo, saves to cache as `base.ini`

**Contracts Source**:
- **Default URL**: Pre-configured to MrKraken StarStrings repo: `https://raw.githubusercontent.com/MrKraken/StarStrings/master/contracts.ini`
- **Storage**: Downloaded and cached as `contracts.ini` in `Documents\SC Localization Editor\cache\`
- **Purpose**: Mission contract strings; merged with Global source in hierarchy order
- **Note**: Global and Contracts are separate files and must both be loaded for complete localization
- **Download**: User prompted before downloading ~49 KB file
- **Threading**: `ContractsCheckerWorker` + `ContractsDownloadWorker` run in parallel to base file checks
- **Version tracking**: Stores commit SHA and date in `contracts_version.txt` (format: `sha\ndate`)

**Pre-configured Sources** (Ships, Commodities, Gear):
- Ships source: Osiris-DevWorks repo with vehicle names and flight stats
- Commodities source: Osiris-DevWorks repo with item commodity names
- Gear source: Osiris-DevWorks repo with FPS equipment and weapon names
- Each has auto-update flag (default: enabled) for automatic background downloads

**Other Sources**:
- User can configure any source to download from a URL or load from local file
- File naming: `components.ini`, `ships.ini`, `commodities.ini`, `gear.ini` (exact naming required)
- Graceful degradation: If source unavailable, app can skip it and merge remaining sources
- Error dialog on failure with options: Specify new location, Skip source, or Cancel merge

**File Naming Clarity**:
- `base.ini` - Cached global source file in Documents (reference from external sources)
- `global.ini` - Game installation file only (`LIVE/data/Localization/english/global.ini`)
- This naming prevents confusion between the app's cached base file and the game's actual file

### 6b. P4K Extraction & DataForge Pipeline

**Purpose**: Extract Star Citizen game data from Data.p4k and convert to DataForge entity XMLs for stats generation.

**Components**:
- **Assets**: `src/assets/unp4k/` contains `unp4k.exe` (P4K extractor) and `unforge.exe` (DataForge converter; v3.13.66+)
- **Main module**: `src/utils/pak_extractor.py` with `extract_dataforge()` function
- **Cache location**: `Documents\SC Localization Editor\cache\dataforge\` 
  - Contains subdirectories: `entity/`, `entities/`, `entityclasses/`, `ships/`, `weapons/`, etc.
- **Freshness check**: `dataforge_cache_is_fresh()` compares p4k mtime against cache creation time
- **Worker thread**: `DataForgeExtractWorker` in `main_window.py` runs extraction in background with progress dialog

**Workflow**:
1. On app startup (in Config tab), `_check_stats_freshness()` detects if DataForge cache is stale
2. If stale, user is prompted to "Extract DataForge from P4K" (button in Config tab)
3. Clicking button triggers `_run_dataforge_extraction()` which:
   - Locates game's `Data.p4k` from `game_install_path`
   - Launches worker to run `unp4k.exe` (extracts Game2.dcb) then `unforge.exe` (converts to XMLs)
   - Caches entity XMLs to `dataforge/` subdirectories
4. When complete, `generate_stats_ini.py` reads the entity XMLs directly (no JSON fallback)

**Key file**: `src/utils/pak_extractor.py` with `extract_dataforge()` orchestrating both tools.

### 7. Overrides Persistence (overrides_manager.py)
- **Location**: `Documents\SC Localization Editor\overrides.ini` (via `AppSettings.get_overrides_path()`)
- **Format**: Plain `key=value` per line (only modified entries)
- **Save triggers**: On "Apply to Game" and on app close via `closeEvent()`
- **Load**: Automatically applied when loading sources, merged as highest priority
- **Bootstrap on First Run**: App automatically downloads missing cache files from configured sources on startup. Creates Documents cache directory if needed. No fallback to game directory or legacy paths.

### 8. Favorites System (main_window.py, settings.py)
- **Mechanic**: Toggling a ship as a favorite prepends a configurable prefix (default `*`) to its `custom_value`
- **Prefix setting**: `AppSettings.FAVORITE_PREFIX` (stored in Registry; configurable in Config tab)
- **Filter**: "★ Favorites Only" checkbox in the filter row; `apply_filters()` checks `entry.custom_value.startswith(prefix)`
- **Context menu**: Right-click shows "★ Add/Remove from Favorites" depending on current state (`toggle_favorite()`)
- **Row lookup**: `_entry_index_for_row(table_row)` maps visible row → `self.entries` index via `UserRole` data on column 0 (required for sortable columns; all row→entry lookups must use this helper)

### 9. Stats Enhancements (settings.py, generate_stats_ini.py)
- **Purpose**: Adds auto-generated ship/component stat descriptions to the localization data
- **Enable/disable**: `AppSettings.STATS_ENABLED` (default True); toggle in Config tab
- **Data sources**:
  - **DataForge entity XMLs**: Parsed from `Documents\SC Localization Editor\cache\dataforge/` (extracted from Data.p4k via `pak_extractor.py`)
  - **Ship flight stats**: Still sourced from `ships.json` (StarCitizenWiki scunpacked-data) until full DataForge ship parser is implemented
- **Script**: `scripts/generate_stats_ini.py` — reads DataForge XMLs and outputs four INI files to cache directory
  - Takes optional arguments: `python scripts/generate_stats_ini.py [base_ini_path [dataforge_cache_dir]]`
- **Cache files** (`AppSettings.STATS_FILES`):
  - `ships_desc_stats.ini` — vehicle_Desc* entries with flight stats (speed, cargo, shields, QD range)
  - `components_desc_stats.ini` — item_Desc(SHLD|POWR|COOL|QDRV)_* with numerical stats
  - `ship_weapons_desc_stats.ini` — item_Desc_*_S* ship weapon stats
  - `fps_weapons_desc_stats.ini` — item_Desc_* FPS weapon stats
- **Loading**: Stats INI files are loaded and merged alongside configured sources when stats are enabled
- **Entity XML format**: Each entity XML contains its own localization key in the entity tag, enabling direct stat extraction without class-name matching

## Workflow

### Standard Usage
1. **First Run**: App:
   - Creates `Documents\SC Localization Editor\cache\` directory
   - Migrates old AppData files to Documents if present
   - Migrates old settings (if any) and pre-configures Global and Contracts sources to MrKraken StarStrings repo
   - Auto-downloads missing cache files from configured sources (Global, Contracts)
   - Then loads and displays merged strings in table
2. **Subsequent Startups**: App loads cached sources, merges in hierarchy order, displays result
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
   - Backup created automatically in `Documents\SC Localization Editor\backups\`
   - Edits saved to `overrides.ini` in Documents
6. **Restore from Backup** (if needed):
   - Click "Restore Backup" → select backup file → restores, overrides still active
7. **Clear Localization** (if needed):
   - Click "Clear Localization" → deletes game's `global.ini` → game reverts to vanilla text
   - Saved overrides are not affected and can be re-applied at any time

### Migration Scenario (after Star Citizen update)
1. Game receives major update (new Data.p4k)
2. User launches app; Config tab shows DataForge cache is stale
3. Click "Extract DataForge from P4K" to refresh entity XML cache (used for stats generation)
4. Load new base file from configured source (e.g., MrKraken StarStrings)
5. App automatically re-applies saved `overrides.ini` on top
6. All user customizations show as "Modified" (green)
7. New keys from the update are present with base values
8. Click Apply to Game → writes complete merged file with all keys
9. Game is now fully playable with all user customizations intact

## File Locations

### Project Files
- **Source code**: `src/` folder
- **Version**: `VERSION.TXT` in project root (single source of truth for all builds)
- **Build scripts**: `scripts/build/build_exe.py` (primary build tool), `scripts/build/build_all.bat` (build exe + installer)
- **Stats generator**: `scripts/generate_stats_ini.py` (generates ship/component description INI files from game data; outputs to cache dir)
- **Assets**: `src/assets/` folder (Osiris DevWorks logo, PayPal/Venmo buttons)
- **Build specs**: `SCLocalizationEditor.spec`, `SCLocalizationEditor-v0.1.0.spec`, `SCLocalizationEditor-v0.2.0.spec` (versioned backups; use current .spec)
- **Installer config**: `installer.iss` (Inno Setup script)
  - Requires admin privileges to create Start Menu shortcuts
  - Configures version, paths, and permissions for Windows installation

### Data & Cached Files

**Application directory** (`./` - no caching here):
- Application code and assets only. No cached files are stored in the app directory to avoid write permission issues on installed apps.

### User Settings (Windows)
- **Configuration**: Windows Registry at `HKEY_CURRENT_USER\Software\Osiris DevWorks\SC Localization Editor`
  - Stores: data source paths, merge hierarchy, auto-update flags, window geometry, window state, favorite prefix, stats enabled flag
- **User data root**: `Documents\SC Localization Editor\` (resolved via registry for OneDrive/folder-redirection support; `AppSettings.get_user_data_dir()`)
- **User overrides**: `Documents\SC Localization Editor\overrides.ini` (custom edits, persisted on Apply)
- **Cached sources**: `Documents\SC Localization Editor\cache\` (downloaded files and extracted data)
  - `base.ini` - Downloaded global source file
  - `contracts.ini` - Downloaded contracts source file
  - `components.ini`, `ships.ini`, `commodities.ini`, `gear.ini` - Other configured sources
  - `base_version.txt`, `contracts_version.txt` - Version tracking files
  - `ships_desc_stats.ini`, `components_desc_stats.ini`, `ship_weapons_desc_stats.ini`, `fps_weapons_desc_stats.ini` - Stats data (generated by `scripts/generate_stats_ini.py`)
  - `dataforge/` - DataForge entity XML cache (extracted from Data.p4k by `pak_extractor.py`)
    - Subdirectories: `entity/`, `entities/`, `entityclasses/`, `ships/`, `weapons/`, etc.
  - `stats_cache/` - JSON cache for ship stats (ships.json from StarCitizenWiki)
- **Backups**: `Documents\SC Localization Editor\backups\` (max 5, oldest deleted; `AppSettings.get_backups_dir()`)
- **Migration**: On startup, old AppData files are migrated to Documents automatically (`AppSettings.migrate_appdata_to_documents()`)

### Game Installation
- **Game files location**: Configurable via Config tab; typically `Roberts Space Industries/StarCitizen/LIVE/data/Localization/english/`
- **Applied file**: `LIVE/data/Localization/english/global.ini` (written on "Apply to Game")
- **Clear Localization**: Deletes the game's `global.ini`, reverting to vanilla text (overrides.ini is preserved)

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
```

### Requirements

- **Python 3.9+** (Windows 10/11)
  - **Recommended**: Python 3.10+ for better performance
  - **Windows-only**: Application uses Windows Registry (`QSettings`) and Windows-only APIs; will not run on macOS/Linux

### Virtual Environment

Create and activate a virtual environment before installing dependencies:

**Windows (PowerShell)**:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (cmd)**:
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### Setup

```bash
pip install -r requirements.txt
```

This installs: PyQt6 (GUI), PyInstaller (builds), pyperclip (clipboard)

### IDE Configuration (PyCharm)

If using PyCharm:
- **Python Interpreter**: Set to `.venv/Scripts/python.exe`
  - Project Settings → Python Interpreter → Add Interpreter → Existing Environment
- **Run Configuration**: Main module should be `src/main.py`
- **Registry debugging**: Use `regedit` to inspect settings at `HKEY_CURRENT_USER\Software\Osiris DevWorks\SC Localization Editor`

### Run Development Version
```bash
python src/main.py
```

### Build Executable

**Recommended: Use the build script** (handles PyInstaller cleanup and packaging):

```bash
cd scripts/build
python build_exe.py
```

This creates `dist/SCLocalizationEditor-v{VERSION}.exe` where VERSION comes from `VERSION.TXT`.

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
powershell -Command "& 'C:\Users\aabou\AppData\Local\Programs\Inno Setup 6\ISCC.exe' installer.iss"
```
Note: Inno Setup is installed per-user at `C:\Users\aabou\AppData\Local\Programs\Inno Setup 6\`. Use PowerShell `&` operator — `cmd /c` does not work for this path.

**Option C: GUI**:
1. Open Inno Setup Compiler
2. File → Open → Select `installer.iss`
3. Build → Compile

Output: `SCLocalizationEditor-v{VERSION}-Setup.exe` in project root

### Version Management

Version is stored in a single file: **`VERSION.TXT`** (e.g., `0.2.0`)

When building:
- `build_exe.py` reads `VERSION.TXT` and names output exe accordingly
- **Both `VERSION.TXT` and `installer.iss` must be manually updated before building** (line ~5 of installer.iss: `AppVersion` and output filename)

**Version update workflow:**
1. Edit `VERSION.TXT` to new version (e.g., `0.3.0`)
2. Update `installer.iss` line 5: `AppVersion=0.3.0`
3. Run `cd scripts/build && build_all.bat`
4. Test the installer and executable
5. Commit changes and tag: `git tag -a v0.3.0 -m "Release v0.3.0"`
6. Create GitHub release with both exe and installer

### Utility Scripts

**generate_stats_ini.py** - Generates stats-augmented INI files from DataForge entity XMLs and ship JSON data.

Usage:
```bash
# Generate stats using default paths (Documents cache)
python scripts/generate_stats_ini.py

# Specify custom paths
python scripts/generate_stats_ini.py path/to/base.ini path/to/dataforge/cache
```

Output files written to cache directory:
- `ships_desc_stats.ini` - Vehicle flight stats (speed, cargo, shields, quantum range)
- `components_desc_stats.ini` - Shield/power/cooler/quantum drive stats
- `ship_weapons_desc_stats.ini` - Ship weapon stats (missiles, bombs, turrets)
- `fps_weapons_desc_stats.ini` - FPS weapon stats (rifles, pistols, etc.)

**extract_components.py** - Extracts modified/new strings from base.ini compared to stock vanilla file.

Usage:
```bash
# Extract components using default paths (Documents cache)
python scripts/extract_components.py

# Use custom stock file
python scripts/extract_components.py --stock path/to/stock-global.ini

# Use custom base.ini and output path
python scripts/extract_components.py --base path/to/base.ini --output path/to/components.ini

# Dry run (print stats without writing)
python scripts/extract_components.py --dry-run
```

Output:
- Compares current base.ini against stock vanilla file (BeltaKoda's repo)
- Writes delta (new or modified keys) to `cache/components.ini`
- Can be configured as the Components source in the app for hierarchy: stock → components (mods) → contracts → user

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
- Filters: text (key or value), category, status, hide unmodified, favorites only

### Sortable Columns
- Columns are sortable; clicking a header sorts the visible rows
- **Critical**: Row index no longer equals entry index when sorted. All row→entry lookups must use `_entry_index_for_row(table_row)`, which reads `Qt.ItemDataRole.UserRole` from column 0 (set to the entry's index in `self.entries` during table population)

### Cell Editing
- `SelectAllDelegate` for in-place editing (auto-selects text)
- Double-click Custom Value column to edit
- Right-click context menu: Edit, Reset to Original, Copy Key, ★ Add/Remove from Favorites

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
| Change category extraction logic | `string_model.py` | `StringEntry.extract_category()` |
| Modify INI parsing (e.g., handle new format) | `ini_parser.py` | `parse_ini_file()` |
| Change how overrides are saved/loaded | `overrides_manager.py` | `save_overrides()`, `load_overrides()` |
| Add a new status type | `string_model.py` | `StringEntry.status` property |
| Modify GitHub auto-update sources | `updater.py` | `check_for_updates()`, `download_base_file()`, `check_contracts()` |
| Change backup retention policy | `main_window.py` | `manage_backups()` |
| Modify file merge logic | `ini_merger.py` | `merge_and_write()` |
| Change favorites prefix or logic | `settings.py`, `main_window.py` | `AppSettings.FAVORITE_PREFIX`, `toggle_favorite()` |
| Modify P4K extraction pipeline | `pak_extractor.py` | `extract_dataforge()` |
| Add/modify stats INI generation | `scripts/generate_stats_ini.py` | (standalone script, reads DataForge XMLs + ships.json) |
| Extract components delta from base | `scripts/extract_components.py` | (standalone script, diffs vs stock vanilla file) |
| Change DataForge cache freshness | `settings.py`, `main_window.py` | `dataforge_cache_is_fresh()`, `_check_stats_freshness()` |
| Change user data directory location | `settings.py` | `AppSettings.get_user_data_dir()` |

## Debugging Tips

- **Registry issues**: Check `HKEY_CURRENT_USER\Software\Osiris DevWorks\SC Localization Editor` for stored settings. Use `regedit` to inspect or clear values if settings corrupt.
- **Threading hangs**: Worker threads signal `finished()` when complete. If UI appears frozen, check that `worker.quit()` + `worker.wait()` are called in the slot.
- **File encoding**: Parser expects UTF-8. Files with BOM or other encodings will fail silently. Use Notepad++ or VS Code to check/convert.
- **Overrides not loading**: Check `Documents\SC Localization Editor\overrides.ini` exists and has correct format (`key=value` per line). Old AppData files are migrated on startup.
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

## Recent Changes (v0.5.3)
- **P4K extraction pipeline**: New `pak_extractor.py` orchestrates `unp4k.exe` → `unforge.exe` flow to extract DataForge entity XMLs from game's Data.p4k
- **DataForge stats generation**: `scripts/generate_stats_ini.py` now reads entity XMLs directly for shields, coolers, power plants, quantum drives, ship/FPS weapons; ships still use scunpacked JSON
- **Extract DataForge button**: Config tab button triggers background extraction with progress dialog; auto-prompts if cache stale
- **New data sources**: Commodities and Gear sources added; auto-configured with Osiris-DevWorks repos
- **New categories**: Gear (FPS equipment) and Commodities categories for better organization
- **Improved category logic**: Turrets now correctly route to Ship Components; ship weapons with size designators (_S1, etc.) properly classified
- **Utility script**: `scripts/extract_components.py` extracts modified/new strings from base.ini vs stock vanilla (enables modded Components source)
- **Gear source sync**: Gear source included in startup sync worker for auto-download

## Recent Changes (v0.5.2)
- **Ships source**: Pre-configured to Osiris-DevWorks repo with flight stats and ship names
- **Gear source (initial)**: New FPS equipment source (not yet fully integrated in v0.5.2)
- **Description fields**: `ships_desc_stats.ini` generates vehicle_Desc_* entries with flight stats
- **Category improvements**: Better distinction between ship components and FPS weapons

## Recent Changes (v0.5.1)
- **Stock vanilla source option**: Alternative to MrKraken's modified base
- **Components and Commodities sources**: Pre-configured sources from community repos
- **Startup sync**: Auto-download missing source files on app startup
- **Source validation**: Preview merge validates required sources before committing

## Recent Changes (v0.5.0)
- **Ship Favorites**: Toggle ★ from right-click menu; configurable prefix (default `*`); "★ Favorites Only" filter
- **Stats enhancements**: `scripts/generate_stats_ini.py` generates ship/component stat description INI files loaded alongside sources
- **Sortable columns**: All table columns are now sortable; `_entry_index_for_row()` helper maps sorted rows to entries
- **Clear Localization**: New toolbar button deletes game's `global.ini` to revert to vanilla (saved overrides unaffected)
- **User data moved to Documents**: All user data (overrides.ini, cache, backups) now stored in `Documents\SC Localization Editor\`; old AppData files migrated on startup
- **Backups moved**: Backups now go to `Documents\SC Localization Editor\backups\` (previously in game localization directory)
- **Status persistence fix**: `original_value` is now the true pre-edit baseline (user source excluded from base merge); `custom_value` populated from overrides.ini on load so Modified status correctly persists across restarts

## Recent Changes (v0.4.0)
- **Source type filtering**: Each source now only loads keys relevant to its type (e.g., Ships source only loads `vehicle_Name*` keys), preventing category pollution across sources
- **GitHub URL auto-conversion**: Config tab now auto-converts GitHub browser URLs to raw URLs for direct download
- **Improved preview merge**: Better feedback in preview dialog; skips user source from required-source checks
- **First-run overrides.ini creation**: App creates an empty overrides.ini on first run if missing

## Recent Changes (v0.3.0)
- **Multi-source configurable data system**: Replaced single base file with configurable Global, Contracts, Components, Ships, and User sources
- **Drag-drop merge hierarchy**: Users define source merge order via Config tab
- **Per-source auto-update flags**: Each source independently configured for auto-update
- **Automatic cache file download on startup**: App bootstraps missing cache files from configured remote URLs
- **Dynamic status bar**: Shows sync status per configured source in merge order
- **Preview Merge**: Shows merge statistics and key counts before committing configuration
- **Disabled automatic update checks**: Replaced with explicit save-and-merge flow via Config tab

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
