# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SC Localization Editor is a Windows-only PyQt6 GUI application for customizing Star Citizen localization strings. Users configure multiple data sources (Global, Contracts, Components, Ships, Commodities, Gear, User) with a drag-and-drop merge hierarchy, edit strings in a table, and apply changes to their game installation with automatic backup management.

**Current Version**: Read from `VERSION.TXT` (single source of truth).

## Quick Commands

```bash
# Setup
pip install -r requirements.txt

# Run
python src/main.py

# Run all tests
pytest tests/

# Run a single test file or test
pytest tests/test_core.py
pytest tests/test_core.py::TestIniParsing::test_parse_basic_ini

# Build exe
cd scripts/build && python build_exe.py

# Build exe + installer (requires Inno Setup)
cd scripts/build && build_all.bat

# Generate stats INI files from DataForge cache
python scripts/generate_stats_ini.py [base_ini_path [dataforge_cache_dir]]

# Extract component delta (base.ini vs stock vanilla)
python scripts/extract_components.py [--stock path] [--base path] [--output path] [--dry-run]
```

Tests cover core parsing, merging, category extraction, and P4K extraction logic. For GUI changes, also manual test: run app, load base file, edit a value, apply to game, restart to verify persistence.

## Architecture

Entry point: `src/main.py`. The app has two main layers:

**GUI layer** (`src/gui/`):
- `main_window.py` — Main window with table, toolbar, filters, backup/restore, threading workers, DataForge extraction. This is the largest file (~2000+ lines).
- `config_tab.py` — Config tab with source configuration widgets, drag-drop hierarchy.
- `enhancements_tab.py` — Optional features tab: stats overlays toggle, ship favorites prefix config, DataForge extraction trigger. Emits `merge_requested` and `stats_pipeline_requested` signals.
- `log_tab.py` — In-app log viewer. Bridges Python `logging` to a Qt text widget via `_LogEmitter` signal (thread-safe). Supports level filtering, auto-scroll, and log export.

**Data layer** (`src/models/`, `src/parser/`, `src/merger/`, `src/utils/`):
- `string_model.py` — `StringEntry` dataclass with category extraction from key prefixes.
- `ini_parser.py` — Line-by-line INI parsing (splits on first `=`), source loading, merging into StringEntry lists.
- `ini_merger.py` — Merge engine: `merge_sources_by_hierarchy(sources_dict, hierarchy, user_overrides)`. Sources merge sequentially; user overrides always win.
- `settings.py` — `AppSettings` class wrapping QSettings (Windows Registry). All user data stored in `Documents\SC Localization Editor\`.
- `updater.py` — GitHub API version checks + download workers for each source.
- `pak_extractor.py` — P4K extraction pipeline: `unp4k.exe` (extracts Game2.dcb) → `unforge.exe` (converts to entity XMLs).
- `overrides_manager.py` — Saves/loads user edits to `overrides.ini` (plain `key=value` format).
- `user_cfg.py` — Manages Star Citizen's `user.cfg` file; ensures `g_language = english` is set in the LIVE directory.

**Scripts** (`scripts/`):
- `generate_stats_ini.py` — Reads DataForge entity XMLs only (no external JSON) → outputs seven stats INI files to cache (ships, components, ship weapons, FPS weapons, mission rewards, commodity/crafting, missiles).
- `extract_components.py` — Diffs base.ini against stock vanilla to produce components.ini.

## Critical Design Decisions

### Sortable columns require indirect row lookup
Row index != entry index when columns are sorted. **All row→entry lookups must use `_entry_index_for_row(table_row)`**, which reads `Qt.ItemDataRole.UserRole` from column 0. Direct indexing into `self.entries` by row number will produce wrong results.

### File naming: base.ini vs global.ini
The cached global source is saved as `base.ini` (not `global.ini`) to avoid confusion with the game's `global.ini` at `LIVE/data/Localization/english/global.ini`.

### Threading model
All I/O-bound operations (file loads, network requests, P4K extraction) run in `QThread` workers. Workers emit `finished()` signals; cleanup requires `quit()` + `wait()`. Never block the main thread with file or network operations. Bulk table updates wrap in `setUpdatesEnabled(False)`.

### DataForge extraction is a three-step pipeline
The "Extract DataForge from P4K" button triggers: (1) unpack Data.p4k → entity XMLs via `pak_extractor.py`, (2) run `generate_stats_ini.py` to produce stats INI files from the XMLs, (3) reload all strings to refresh the table. All three steps run sequentially from a single button click.

### Merge hierarchy
Sources merge in user-defined order (default: global → contracts → components → ships → commodities → gear → user). Later sources overwrite earlier ones. User overrides are always applied last and never lost during source updates.

### Favorites use value prefix
Favorites prepend a configurable prefix (default `*`) to `custom_value`. The prefix is stored in Registry via `AppSettings.FAVORITE_PREFIX`.

## File Locations

| What | Where |
|------|-------|
| Settings | Windows Registry: `HKEY_CURRENT_USER\Software\Osiris DevWorks\SC Localization Editor` |
| User data root | `Documents\SC Localization Editor\` (resolved via registry for OneDrive support) |
| Overrides | `Documents\SC Localization Editor\overrides.ini` |
| Cached sources | `Documents\SC Localization Editor\cache\` (`base.ini`, `contracts.ini`, `ships.ini`, etc.) |
| DataForge cache | `Documents\SC Localization Editor\cache\dataforge\` (entity XMLs from Data.p4k) |
| Stats INIs | `Documents\SC Localization Editor\cache\` (`ships_desc_stats.ini`, `components_desc_stats.ini`, `ship_weapons_desc_stats.ini`, `fps_weapons_desc_stats.ini`, `mission_rewards_stats.ini`, `commodity_crafting_stats.ini`, `missile_stats.ini`) |
| Backups | `Documents\SC Localization Editor\backups\` (max 5, oldest auto-deleted) |
| Game file | `{game_install_path}\LIVE\data\Localization\english\global.ini` |
| P4K tools | `src/assets/unp4k/` (`unp4k.exe`, `unforge.exe`) |

## Common Modification Points

| Task | File | Key Function |
|------|------|-------------|
| Add/change table columns | `main_window.py` | `setup_string_table()` |
| Add/change filters | `main_window.py` | `apply_filters()`, `on_filter_changed()` |
| Change category extraction | `string_model.py` | `StringEntry.extract_category()` |
| Modify INI parsing | `ini_parser.py` | `parse_ini_file()` |
| Change merge logic | `ini_merger.py` | `merge_sources_by_hierarchy()` |
| Change overrides persistence | `overrides_manager.py` | `save_overrides()`, `load_overrides()` |
| Modify auto-update | `updater.py` | `check_for_updates()`, `download_base_file()` |
| Change backup behavior | `main_window.py` | `manage_backups()` |
| Modify P4K extraction | `pak_extractor.py` | `extract_dataforge()` |
| Change stats generation | `scripts/generate_stats_ini.py` | (standalone script) |
| Change user data paths | `settings.py` | `AppSettings.get_user_data_dir()` |
| Change DataForge freshness | `settings.py`, `main_window.py` | `dataforge_cache_is_fresh()` |
| Change stats/favorites UI | `enhancements_tab.py` | `setup_ui()` |
| Change in-app logging | `log_tab.py` | `LogTab`, `_QtLogHandler` |
| Change user.cfg behavior | `user_cfg.py` | `ensure_user_cfg_language()` |

## Version & Release

**Version update workflow:**
1. Edit `VERSION.TXT` to new version
2. Update `installer.iss` line ~5: `AppVersion` and output filename
3. Run `cd scripts/build && build_all.bat`
4. Test exe and installer
5. Commit, tag (`git tag -a v0.X.0 -m "Release v0.X.0"`), push
6. Create GitHub release with both `dist/SCLocalizationEditor-v{VERSION}.exe` and `SCLocalizationEditor-v{VERSION}-Setup.exe`

Discord notification is automatic via GitHub Actions (`scripts/discord_notify.py`) if `DISCORD_RELEASE_WEBHOOK_URL` secret is configured.

## Debugging

- **Registry**: `regedit` → `HKEY_CURRENT_USER\Software\Osiris DevWorks\SC Localization Editor`
- **Threading hangs**: Check `worker.quit()` + `worker.wait()` are called in finished slots
- **File encoding**: Parser expects UTF-8; BOM or other encodings fail silently
- **GitHub API rate limit**: Unauthenticated, 60 requests/hour per IP
- **Overrides not loading**: Verify `Documents\SC Localization Editor\overrides.ini` exists with `key=value` format

## Dependencies

- **PyQt6** (>=6.10.0) — GUI framework
- **pyinstaller** (>=6.3.0) — Executable builder
- **pyperclip** (>=1.8.2) — Clipboard access

Windows-only (uses Windows Registry via QSettings). Python 3.9+, recommended 3.10+.
