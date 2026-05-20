# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Smart Citizen (formerly SC Localization Editor) is a Windows-only PyQt6 GUI application for customizing Star Citizen localization strings. Tagline: *Smarter Strings for Star Citizen*. Users edit strings in a table backed by a `global` source (locally cached `base.ini` from Data.p4k extraction) merged with their per-channel `user.ini` overrides, then apply the result to their game installation with automatic backup management.

**Branding**: User-facing strings, registry path (`Osiris DevWorks\Smart Citizen`), and the default user data root (`Documents\Smart Citizen\`) all use the new name. `AppSettings` still contains one-shot migrators for the legacy `Osiris DevWorks\SC Localization Editor` registry tree and `Documents\SC Localization Editor\` directory (rebrand happened in 0.9.0); do not remove them while users on pre-0.9 builds may still upgrade.

**Build modes**: The standard PyInstaller build is *registry mode* — settings go to `HKEY_CURRENT_USER`, data goes to `Documents\Smart Citizen\`. A *portable mode* build (`build_exe.py --portable`) overwrites `src/utils/build_mode.py` so `IS_PORTABLE=True`, swapping the backend to `JsonSettings` (config.json next to the exe) and rooting user data at `<exe-dir>/data/`. The repo on disk should always have `IS_PORTABLE=False` — the flag lives in a git-ignored `_build_info.py` written by the build script. See `src/utils/build_mode.py` for the contract and `src/utils/json_settings.py` for the QSettings-compatible JSON shim.

**Current Version**: Read from `VERSION.TXT` (single source of truth). Currently 1.4.1.

## Quick Commands

```bash
# Setup (production deps only)
pip install -r requirements.txt

# Setup (with dev/test tools: pytest, flake8, black, mypy, etc.)
pip install -r requirements-dev.txt

# Run
python src/main.py

# Testing
pytest tests/                                    # Run all tests
pytest tests/test_core.py                       # Run single file
pytest tests/test_core.py::TestIniParsing       # Run single class
pytest tests/test_core.py::TestIniParsing::test_parse_basic_ini  # Run single test
pytest tests/ -v                                # Verbose output
pytest tests/ --cov=src --cov-report=html      # Coverage report (HTML)
pytest tests/ -n auto                           # Parallel execution (pytest-xdist)

# Code Quality
black src/ tests/ scripts/                      # Format code
flake8 src/ tests/ scripts/                     # Lint (use flake8 config if present)
isort src/ tests/ scripts/                      # Sort imports
mypy src/                                       # Type checking

# Building
cd scripts/build && python build_exe.py             # Build exe (PyInstaller, registry-backed)
cd scripts/build && python build_exe.py --portable  # Build portable variant (JSON settings + next-to-exe data/)
cd scripts/build && build_all.bat                   # Build exe + installer (requires Inno Setup)

# Data Generation
python scripts/generate_enhancements_ini.py [base_ini_path [dataforge_cache_dir]]
python scripts/extract_components.py [--stock path] [--base path] [--output path] [--dry-run]
```

## Testing Strategy

**Unit Tests** (`tests/`): Split by domain — `test_core.py` (INI parsing/merging/category extraction; `TestStringEntry` is currently `@pytest.mark.skip` because its constructor calls predate `category` and `status` becoming required positional args — fix is a separate cleanup), `test_missions.py` (mission rewards pipeline), `test_mission_engagement.py` (FPS / Ship / FPS & Ship engagement classifier driven by CIG loc-key naming conventions), `test_mission_turrets.py` (turret detection from `SpawnDescription_ShipGroup Name="Turrets"` + the `OverrideTurretHosility_BP` mission-variable signal, fabricated XML so tests don't need a populated cache), `test_blueprint_pools.py` (multi-source pool merge regression + component-style tag annotation + CIG-prefix strip + pool rank-tier label derivation), `test_pak_extraction.py` (P4K/DataForge), `test_progress_sink.py` (thread-safe progress coalescing), `test_dataforge_patcher.py` (declarative XML patching), `test_app_updater.py` (GitHub Releases version-check worker), `test_channel_layout.py` (per-channel directory migration), `test_retired_url_sources_migration.py` (1.0 cleanup of the contracts/components/ships/commodities/gear sources retired in 0.7.0 — covers fresh-install defaults, upgrade-time pruning, URL-vs-local guard, and idempotence), `test_applied_file_validator.py` (post-apply `global.ini` vs stock `base.ini` validation), `test_entry_filter.py` (column-filter logic + the `NUM_COLUMNS` getter-tuple drift guard), `test_markdown_renderer.py` (About/Help markdown→HTML conversion), `test_resource_path.py` (PyInstaller `_MEIPASS`-aware resource resolution), `test_status_classification.py` (the post-1.3.0 `_determine_status_from_source` classifier that distinguishes "Enhanced" from "Modified"), `test_user_cfg.py` (`g_language = english` user.cfg management), `test_user_ini_autosave_guard.py` (v1.3.0 regression guard: `should_autosave_user_ini` refuses a close-time autosave that would truncate a populated `user.ini` to zero bytes after a load mismatch), `test_frontend_version_stamp.py` (the `Frontend_PU_Version` watermark appended at apply-to-game time), `test_portable_mode.py` (portable build flag flips `AppSettings._backend` to `JsonSettings` and routes `get_user_data_dir()` next-to-exe), `test_build_info_fallback.py` (verifies `build_mode.py` falls back to `IS_PORTABLE = False` when the build-script-generated `_build_info.py` is absent), `test_json_settings.py` (file-backed `QSettings`-API shim used in portable mode), `test_locpack_exporter.py` (Export Loc-Pack zip writer), `test_tag_builder.py` (TagConfig serialization + render_tag output shape), `test_tag_config_settings.py` (TagConfig persistence via `AppSettings`, including the 1.4.0 `Phys`/`Distort`/`Bio` → `Physical`/`Distortion`/`Biochemical` ship-weapon mapping-key rename), `test_mining_salvage_stats.py` (1.4.0 `enhancements_mining_laser` / `enhancements_salvage_tool` extractors — per-mode beam stats for mining heads + handheld salvage tools, driven by fabricated XML so the suite doesn't need a populated DataForge cache), `test_ship_weapon_tag.py` (1.4.0 regression guard for `_ship_weapon_name_tag_factory` in `generate_enhancements_ini.py`: EMP devices that have a size but no damage and tractor beams must NOT emit a damage tag, while real combat weapons still must), `test_user_ini_reset.py` (locks the `reset_user_ini(path, *, backup=True)` contract used by the Config tab's **Reset user.ini** button — returns `None` when source absent, `backup=True` renames to a timestamped sibling, `backup=False` deletes outright, and a same-second double-call doesn't clobber the first backup). Worker classes themselves have no automated tests — they need `pytest-qt` (not currently a dev dependency); manual smoke testing is still the only verification path for the QThread workers in `workers.py`. Pytest config lives in `pytest.ini` at the project root (not under `tests/` — placing it there would make rootdir resolve to `tests/` and break the `from src.X` imports CI uses) — `pythonpath = . src` (project root for `from src.X` imports + `src/` for legacy `from utils.X` imports used by older tests), registers markers: `unit`, `integration`, `slow`, `critical`, `regression`.

**GUI Testing**: Manual. Run app (`python src/main.py`), load base file, edit a value, apply to game, restart to verify persistence. Use the Log Tab to watch for errors during load/merge/apply cycles.

## Architecture

Entry point: `src/main.py`. The app has two main layers:

**GUI layer** (`src/gui/`):
- `main_window.py` — Main window with table, toolbar, filters, backup/restore, DataForge extraction trigger, and worker-thread orchestration. Largest file in the repo; manages the primary workflow: load, merge, edit, apply. Worker classes live in `workers.py`; pure-Python helpers (`validate_applied_file`, `filter_entry_indices`, `markdown_to_html`) live in their own modules and are wrapped by thin `MainWindow` methods. Owns `_stamp_frontend_version(merged)` plus `_FRONTEND_VERSION_KEY` / `_FRONTEND_VERSION_STAMP_RE`: at apply-to-game time, the launcher's `Frontend_PU_Version` loc-key gets `" | Localizations Enhanced with Smart Citizen v{VERSION}"` appended so users can see in-game that the loc-pack is active; the regex strips any prior stamp before re-applying so the suffix doesn't pile up across runs.
- `workers.py` — All `QThread` background workers + the shared `AnimatedProgressDialog` and `SelectAllDelegate`. Workers: `FileLoaderWorker` (load sources → build `StringEntry` list + sort keys), `StartupSyncWorker` (refresh URL-backed sources at startup), `EnhancementsGeneratorWorker` (run `scripts/generate_enhancements_ini.py` in-process via `importlib.util`), `P4kExtractWorker` (unp4k extraction of `global.ini`), `DataForgeExtractWorker` (unp4k + unforge + post-extract patches). Each worker emits `progress` (str) + `progress_pct` (completed, total, message) signals; `AnimatedProgressDialog.set_progress` consumes the latter. `AppUpdateCheckWorker` is the exception — it lives in `src/utils/app_updater.py` because the worker, the version-comparison logic, and the registry timestamp-cap belong together as one unit.
- `markdown_renderer.py` — `markdown_to_html(text, text_color, base_color, link_color)` for the About / Help panels. Pure-Python; the Qt caller passes in palette colours so the converter has no Qt dependency. Stash-and-restore code-span handling means `**` and `_` inside backticks stay literal (important: loc keys like `vehicle_Name*` shouldn't sprout `<em>` tags).
- `config_tab.py` — **Config Tab**: Data source management (add/edit/remove sources), drag-drop merge hierarchy, Star Citizen install path, and DataForge extraction trigger.
- `enhancements_tab.py` — **Enhancements Tab**: Toggle stats overlays, configure ship favorites prefix, trigger DataForge extraction. Emits `merge_requested` and `stats_pipeline_requested` signals.
- `log_tab.py` — **Log Tab**: In-app real-time log viewer. Bridges Python `logging` to Qt text widget via `_LogEmitter` signal (thread-safe). Supports level filtering, auto-scroll, and log export.
- `filter_header.py` — `FilterHeaderView` QHeaderView subclass adding per-column QLineEdit filter row below header labels, with debounced filtering.
- `string_table_model.py` — `QAbstractTableModel` backing the strings `QTableView`. Replaces the old `QTableWidget.populate_table()` approach; renders visible rows on demand and sorts in Python (via `sort()` override) rather than per-comparison `lessThan()`. Column index constants (`COL_CATEGORY`, `COL_KEY`, `COL_DEFAULT`, `COL_CURRENT`, `COL_STAR`, `COL_CUSTOM`, `COL_STATUS`) live here.
- `import_dialog.py` — `ImportConflictDialog` for resolving conflicts when importing INI files into user overrides. Allows per-key resolution strategies (keep current, use imported, append, prepend, or custom).
- `tag_mapping_dialog.py` — `TagMappingDialog`: modal editor for the Tag Builder's per-category variant mapping (Short / Medium / Long columns × class/ordinance/damage rows). Hides the Medium column for kinds that only expose Short/Long (currently missiles' ordinance) via the `medium_column_visible` flag so the user never sees a column they can't actually select. Pure presentation; the underlying `TagConfig` lives in `src/utils/tag_builder.py`.
- `theme.py` — Palette swap on `QApplication` + branded font loading (`load_application_fonts()` registers the Hyperspace Race OTF from `assets/fonts/`). Theme-aware widgets rely on palette `WindowText`/`Text` roles; dim/secondary labels mark themselves with `setProperty("role", "secondary")` and the app-level QSS rule installed by `apply_theme()` recolors them on live theme swap. Progress-bar contrast is controlled via the palette's `Highlight` role (Fusion's native chunk color) — do not add `QProgressBar::chunk` QSS, it switches Qt to a styled path that stops animating in indeterminate mode.
- `coach_mark.py` — `CoachMarkOverlay` + `TutorialTour` for the in-app guided tour. Self-contained: the main window builds a list of `CoachMarkStep` records (target widget, title, description, optional pre-action) and calls `tour.start()`. Overlay dims the window, spotlights the target, and floats a callout with Back / Next / Skip; emits `finished(completed: bool)` when done.

**Data layer** (`src/models/`, `src/parser/`, `src/merger/`, `src/utils/`):
- `string_model.py` — `StringEntry` dataclass with category extraction from key prefixes.
- `ini_parser.py` — Line-by-line INI parsing (splits on first `=`), source loading via `load_sources_from_settings()`, and `load_overrides(target_path)` for reading `user.ini` back as a `dict[str, str]`. `_determine_status_from_source(...)` classifies each entry as `Modified` (user explicitly set `custom_value`), `Enhanced` (value came from the enhancements pipeline), `Unmodified` (stock `base.ini` text), or `New` (key only exists in user / enhancements, not base). Pre-1.3.0 the "Enhanced" bucket didn't exist — those entries showed as "Modified" and were indistinguishable from real user edits.
- `ini_merger.py` — Merge engine: `merge_sources_by_hierarchy(sources_dict, hierarchy, user_overrides)`. Sources merge sequentially; user overrides always win.
- `settings.py` — `AppSettings` class wrapping a backend that is either `QSettings` (registry mode, the default) or `JsonSettings` (portable mode — see `build_mode.py`/`json_settings.py` below). User data lives under the configured data root (default `Documents\Smart Citizen\`, or `<exe-dir>/data/` in portable mode) plus `{active_channel}\`. Critical: the backend is the single source of truth for all paths and preferences. Also owns canonical paths (`get_user_data_dir()`, `get_cache_dir()`, `get_user_ini_path()`, `get_backups_dir()`, `get_dataforge_cache_dir()`) and a chain of one-shot migrators run on every launch (all idempotent, all no-op in portable mode since there's no registry to migrate from): `migrate_legacy_settings()` (seeds `[global, user]` defaults for fresh installs), `migrate_remove_retired_url_sources()` (1.0 prune of contracts/components/ships/commodities/gear from upgrader registries — only when the stored path is a URL; local-path overrides are preserved), `migrate_global_to_p4k_local()` (rewrites `global` from a URL to the local cached `base.ini`), `migrate_registry_appname()` (`SC Localization Editor` → `Smart Citizen` registry tree), `migrate_docs_folder_rename()` (`Documents\SC Localization Editor\` → `Documents\Smart Citizen\`), `migrate_data_to_documents()` (`AppData\Roaming\...` → the configured data root), `migrate_game_path_to_channel_layout()` (0.9.3+ flat layout → per-channel layout), `migrate_dataforge_cache_to_local()` (1.x move of the DataForge XML cache out of `Documents\...\cache\dataforge\` into `AppData\Local\...` to escape OneDrive / Defender / Search Indexer per-file hooks on the ~28k extracted XMLs).
- `json_settings.py` — `JsonSettings`, a file-backed key-value store mirroring the four `QSettings` methods `AppSettings` actually uses (`value` / `setValue` / `remove` / `sync`). Writes immediately on every set, thread-safe via `RLock`. Used only when `build_mode.IS_PORTABLE` is true. We do **not** use `QSettings(IniFormat)` because it mangles slash-prefixed keys (e.g. `enhancements/categories/foo/enabled`) into nested groups and can't round-trip them — `test_json_settings.py` locks this contract.
- `build_mode.py` — Single `IS_PORTABLE` flag. Default `False`; `scripts/build/build_exe.py --portable` writes a tiny generated `src/utils/_build_info.py` (git-ignored) with `IS_PORTABLE = True` and `build_mode.py` picks it up via `try: from src.utils._build_info import IS_PORTABLE`. The build script deletes the generated file post-build so the source tree never gets committed in portable-mode state. Tests flip the flag via `monkeypatch.setattr` to exercise both branches; production code only ever reads it.
- `locpack_exporter.py` — Pure-Python writer for the **Export Loc-Pack** toolbar action: zips the already-applied `global.ini` from the game's localization directory into `SmartCitizen-LocPack-{channel}-{YYYYMMDD}.zip` (compression level 9; the bare `global.ini` sits at the zip root so recipients drop it straight into their `StarCitizen\<channel>\data\Localization\english\`). The Qt button lives on `MainWindow.export_locpack`; this module owns the I/O so the logic is testable without Qt.
- `tag_builder.py` — Pure-Python (Qt-free) **Tag Builder** engine new in 1.4.0. Drives the `[CLASS-Sx-grade]`-style annotations that prefix component / missile / ship-weapon names in the generated enhancement INIs. A `TagConfig` per category captures element order, per-element style (e.g. `Short`/`Medium`/`Long`), separator, enclosing brackets, placement, and the class/ordinance/damage variant mapping; `render_tag(category, values, cfg)` produces the final bracketed string. `DEFAULT_TAG_CONFIGS` is calibrated so an unconfigured user sees the pre-1.4.0 format byte-for-byte (locked by `tests/test_tag_builder.py::TestDefaultBackwardsCompat`). Consumed by both the generator (`scripts/generate_enhancements_ini.py`, which has a `sys.path` shim so it still runs as a standalone CLI from `scripts/`) and the Enhancements tab's live preview. Persisted by `AppSettings.get_tag_config()` / `set_tag_config()` / `get_all_tag_configs()` as one JSON blob per category under `tag_builder/{category}/config` — flat slash-key so `JsonSettings` round-trips it.
- `dataforge_diff.py` — Manifest-based diff cache for the ~28k-file DataForge XML cache. `update_manifest(cache_dir)` snapshots SHA-256 + mtime of every XML; `dirty_categories(cache_dir)` returns the set of enhancement categories whose source subtree changed since the last snapshot (or `None` if no prior manifest → run everything, or empty set → skip everything). `CATEGORY_SUBTREES` maps each enhancement category to the DataForge paths it reads from and **must stay in sync with `DATAFORGE_KEEP_SUBPATHS` in `pak_extractor.py`**. The hash sweep runs in a `ThreadPoolExecutor` because the work is I/O-bound (Defender / Search Indexer / OneDrive intercept every file-open on Windows).
- `updater.py` — Per-source GitHub downloads. Drives the auto-update workers that refresh cached source INIs from their configured GitHub URL. Post-1.0 the only URL-backed source is `global` (`base.ini`); the four legacy URL sources have been retired in favor of local Data.p4k extraction.
- `app_updater.py` — *Separate* from `updater.py`. Polls `GET /repos/Osiris-DevWorks/smart-citizen/releases/latest` and compares `tag_name` to the local `VERSION.TXT` to surface a "new installer available" prompt. Runs on a `QThread`; `MainWindow` caps auto-checks to once per 6 hours via a registry timestamp to stay under GitHub's 60-req/hr unauthenticated limit.
- `pak_extractor.py` — P4K extraction pipeline: `unp4k.exe` (extracts Game2.dcb) → `unforge.exe` (converts to entity XMLs). After unforge writes the full DataForge tree to a temp dir, `_copy_filtered_records()` copies only the subtrees in `DATAFORGE_KEEP_SUBPATHS` (the ones the generator actually reads) to the persistent cache — halves cache file count and cuts copy/rmtree wall time. Adding a new read path in the generator requires adding it to `DATAFORGE_KEEP_SUBPATHS`; `tests/test_pak_extraction.py::TestDataForgeKeepList` locks the contract.
- `user_ini_manager.py` — Saves user-modified entries to `user.ini` (plain `key=value`, no sections) via `save_user_ini(entries, path)`; coordinates with `ImportConflictDialog` when importing external INIs. Also exports `should_autosave_user_ini(entries, path)`: a v1.3.0 regression guard called from `MainWindow.closeEvent`. v1.3.0 unconditionally re-wrote `user.ini` from the in-memory entry list on close, which on a load mismatch (channel drift after migration, transient I/O) silently truncated a populated `user.ini` to 0 bytes. The guard refuses the write when nothing is actually modified but the on-disk file is non-empty. Also exports `reset_user_ini(path, *, backup=True)` — the Config tab's **Reset user.ini** button: by default renames the existing `user.ini` to a timestamped sibling (`user.ini.YYYYMMDD-HHMMSS.bak`) before removing it so an accidental wipe is recoverable; `backup=False` deletes outright. Returns the backup `Path` or `None` when the source was absent.
- `user_cfg.py` — Manages Star Citizen's `user.cfg` file; ensures `g_language = english` is set in the LIVE directory.
- `version.py` — Reads version string from `VERSION.TXT`, handling both normal and PyInstaller-frozen execution.
- `perf.py` — `@timed` decorator for debug-level performance profiling. No-op when DEBUG logging disabled.
- `progress_sink.py` — `ProgressSink` coalesces `advance()` calls from many worker threads into throttled `(completed, total, message)` callbacks. Used by the parallelized lookup builders and enhancement generators to drive determinate progress bars without flooding the Qt event loop.
- `dataforge_patcher.py` — Applies declarative JSON patches from `patches/` to the DataForge XML cache immediately after extraction. Fixes upstream CIG data bugs (e.g. mission records pointing at wrong loc-keys) so downstream consumers see corrected data. Patches mirror the DataForge layout under `patches/<category>/.../<name>.patch.json`.
- `applied_file_validator.py` — `validate_applied_file(written_path, cache_dir, stock_keys=None)`: independently re-parses the just-written `global.ini` against the cached `base.ini` and returns a human-readable diff (missing / unexpected keys) or `""` when valid. `MainWindow._validate_applied_file` is a thin wrapper that supplies the cache dir from `AppSettings`. Lets `apply_to_game` auto-rollback on a merger bug.
- `entry_filter.py` — `filter_entry_indices(...)`: pure-Python row filter for the strings table (column filters + category / status / hide-unmodified / favorites-only). Imports `NUM_COLUMNS` from `string_table_model` so the OOB-bounds guard stays in sync if a column is added; bad indices are dropped + logged once instead of raising `IndexError` deep in the per-entry loop. Per-call getter tuple lets the hot path call only the getters for active filters.
- `resource_path.py` — `get_resource_path(rel)` (PyInstaller `_MEIPASS`-aware) and `resolve_patches_dir()` (`Path` to bundled `patches/`). Lives in `src/utils/` rather than `src/gui/` because both `main_window.py` and `workers.py` depend on it — keeping it leaf-level avoids a `gui` ↔ `gui` import cycle.

**Scripts** (`scripts/`):
- `generate_enhancements_ini.py` — Reads DataForge entity XMLs only (no external JSON) → outputs enhancement INI files to cache (ships, components, ship weapons, FPS weapons descriptions).
- `extract_components.py` — Diffs base.ini against stock vanilla to produce components.ini.
- `gen_commodity_crafting.py` — Generates `commodity_crafting_enhancements.ini` with crafting blueprint usage data from DataForge XMLs.
- `compare_kraken_fixture.py` — Research/reporting tool: diffs the `kraken_4.7.ini` ground-truth fixture against our generated `mission_rewards_enhancements.ini` to validate blueprint list output. Read-only.
- `diff_bp_kraken.py`, `diff_bp_annotations.py`, `diff_bp_csv_fixture.py` — Read-only diagnostic scripts validating `[BP]` / `[BP?]` blueprint annotations on mission rewards. Each compares our `mission_rewards_enhancements.ini` output against a different ground-truth source (kraken fixture, an applied LIVE `global.ini`, and the `missions_4.7.177.csv` per-variant fixture, respectively). Use these when blueprint tags regress.
- `diff_base_ini_channels.py` — Read-only: diffs cached `base.ini` between two SC channels (e.g. `LIVE` vs `PTU`) and reports added / removed / changed loc keys as a category-bucket summary plus optional full machine-readable list. Defaults to `%USERPROFILE%\Documents\Smart Citizen` and supports `--user-data` for OneDrive-redirected installs.
- `diff_mission_rewards_channels.py` — Companion to `diff_base_ini_channels.py` for the generated `mission_rewards_enhancements.ini`: diffs mission entries between two channels and reports adds / removes / changes. Useful when verifying that a CIG balance pass or new mission archetype propagated correctly through the enhancements pipeline across `LIVE` / `PTU`.
- `discord_notify.py` — GitHub Actions release webhook notifier.
- `build/build_exe.py`, `build/build_all.bat`, `build/clean_cache_for_distribution.py` — Build pipeline; see `scripts/build/BUILD_INSTRUCTIONS.md`.

**PyInstaller specs**: `SmartCitizen.spec` at the repo root is the live spec used by the current build. The `SCLocalizationEditor-v*.spec` and `SmartCitizen-v0.9.*.spec` files are archival snapshots from prior releases — do not edit them for new builds.

## Critical Design Decisions

### Sortable columns require indirect row lookup
The table is a `QTableView` backed by `StringTableModel` (`src/gui/string_table_model.py`), which maintains a filtered/sorted list of indices into `self.entries`. Row index != entry index when columns are sorted or filtered. **All row→entry lookups must use `_entry_index_for_row(row)`** on `MainWindow` (which delegates to `self._model.entry_index_for_row(row)`). Direct indexing into `self.entries` by row number will produce wrong results. When adding code that reads from the table, use the `COL_*` constants from `string_table_model.py` rather than hard-coded column numbers.

### File naming: base.ini vs global.ini
The cached global source is saved as `base.ini` (not `global.ini`) to avoid confusion with the game's `global.ini` at `LIVE/data/Localization/english/global.ini`.

### Threading model
All I/O-bound operations (file loads, network requests, P4K extraction) run in `QThread` workers — they live in `src/gui/workers.py` (with `AppUpdateCheckWorker` as the lone exception, which lives next to its companion logic in `src/utils/app_updater.py`). Workers emit `finished()` signals; cleanup requires `quit()` + `wait()`. Never block the main thread with file or network operations. Bulk table updates wrap in `setUpdatesEnabled(False)`. Registry access (via `AppSettings`) is thread-safe; use it freely from main or worker threads. Worker logger names are `src.gui.workers` post-extraction (was `src.gui.main_window` pre-extraction) — relevant if you grep logs.

### Startup initialization
On first run, the app initializes user data directories, validates Star Citizen install path, and may show a startup dialog to guide configuration. Subsequent runs check source freshness and auto-apply any pending DataForge cache updates.

### DataForge extraction is a four-step pipeline
The "Extract DataForge from P4K" button triggers: (1) unpack Data.p4k → entity XMLs via `pak_extractor.py` (the bundled unp4k is a parallelised fork — `odw-fast-unp4k` — that uses ThreadPoolExecutor for extraction and `lxml` for unforge), (2) apply declarative patches from `patches/` via `dataforge_patcher.py` to fix upstream CIG data bugs, (3) run `generate_enhancements_ini.py` to produce enhancement INI files from the XMLs (only for categories the diff cache flags as dirty — see below), (4) reload all strings to refresh the table. All steps run sequentially from a single button click. The patch step is idempotent and always runs on the extracted cache, even when extraction is skipped as fresh. The progress dialog stays continuous across steps 1–3 so users see one bar from start to finish.

### DataForge diff cache skips unchanged enhancement generators
`src/utils/dataforge_diff.py` snapshots every XML in the DataForge cache and, on the next extraction, reports which enhancement categories actually need to re-run. `CATEGORY_SUBTREES` maps each category (`ships`, `components`, `ship_weapons`, `fps_weapons`, `missions`, `commodities`, `journal`) to the DataForge paths it reads from. **If you add a new enhancement category or change which DataForge subtrees an existing one reads, you must update both `CATEGORY_SUBTREES` here AND `DATAFORGE_KEEP_SUBPATHS` in `pak_extractor.py` — the former drives "what to re-run", the latter drives "what to copy to the cache". They are not the same list (subtree filters can be finer-grained than keep filters), but they must agree on coverage.**

### Apply-to-game stamps a watermark on Frontend_PU_Version
On every apply, `MainWindow` appends a Smart Citizen watermark to the `Frontend_PU_Version` loc value (the string the SC main menu renders verbatim) so users can confirm the loc-pack is active in-game without opening a file. The stamping logic + key constants live near the top of `main_window.py` (search `_FRONTEND_VERSION_KEY`); the no-double-stamp guarantee is locked by `tests/test_frontend_version_stamp.py`.

### Portable build mode
A second build target produces a registry-free, fully relocatable distribution. Trigger: `python scripts/build/build_exe.py --portable`. The build script writes `src/utils/_build_info.py` (git-ignored) with `IS_PORTABLE = True`, PyInstaller bundles it, and at runtime `AppSettings` (a) swaps its backend from `QSettings` to `JsonSettings(<exe-dir>/data/config.json)` and (b) overrides `get_user_data_dir()` to `<exe-dir>/data/`. Legacy-registry migrators are no-ops in this mode. When editing settings-touching code, prefer `AppSettings` helpers over reaching for `QSettings` directly — calling `QSettings` straight breaks portable mode silently.

### Parallel pipelines report progress via ProgressSink
Lookup builders and enhancement output generators run in parallel worker threads (see `scripts/generate_enhancements_ini.py`). They share a single `ProgressSink` (`src/utils/progress_sink.py`) so the UI shows one determinate progress bar. Never call `QProgressBar.setValue()` directly from workers — go through the sink so updates are coalesced and throttled on the main thread.

### Tag-config hand-off to the enhancements worker
`EnhancementsGeneratorWorker.__init__(categories, tag_configs)` (in `src/gui/workers.py`) takes the tag-builder configs as a plain dict parameter rather than reading them inside the worker thread. `MainWindow.run_enhancements_pipeline` calls `AppSettings.get_all_tag_configs()` on the **main thread** and hands the result to the worker so the generator code path never touches a live `QSettings` / `JsonSettings` handle from a background thread. Don't shortcut this — `QSettings` is thread-safe but the JSON shim's file write is point-in-time, and we want the generator's input frozen at pipeline-launch time anyway so a mid-run tab edit doesn't half-rewrite an enhancement INI.

### Mining-laser and handheld-salvage stat enhancements
`generate_enhancements_ini.py` exposes `enhancements_mining_laser` and `enhancements_salvage_tool` (new in 1.4.0) alongside the existing ship-weapon / FPS-weapon / component generators. The mining-laser generator reads ship-mounted mining heads under `ships/weapons/mining_laser_*.xml` and emits per-mode (Fracture / Extraction) beam stats plus `SEntityComponentMiningLaserParams` modifier overlays. The salvage generator reads `weapons/fps_weapons/grin_*salvage_repair*.xml` and emits per-mode (Repair / Salvage) rate / efficiency / ramp / energy / heat / wear. Both deliberately exclude things that would require resolving a `globalParams` UUID into a base entity (base mining-laser power/range, ship-mounted salvage equipment); the scope cut is documented at the function level and locked by `tests/test_mining_salvage_stats.py`.

### Merge hierarchy
Sources merge in user-defined order. Later sources overwrite earlier ones; user overrides are always applied last and never lost during source updates. As of 1.0 the seeded default is just `[global, user]` — the four URL-based sources (contracts/components/ships/commodities) and `gear` were retired in 0.7.0 when extraction moved to local Data.p4k, and `migrate_remove_retired_url_sources()` cleans them out of upgrader registries. `load_sources_from_settings()` additionally injects a synthetic `enhancements` source at runtime when any enhancement category is enabled on the Enhancements tab — it is *not* a registry entry and shouldn't be added to the hierarchy by hand.

### Favorites use value prefix
Favorites prepend a configurable prefix (default `*`) to `custom_value`. The prefix is stored in Registry via `AppSettings.FAVORITE_PREFIX`.

### Portable vs registry build mode
The same source tree builds two variants: the default registry-backed installer (`python build_exe.py`) and a portable variant (`python build_exe.py --portable`) that ships everything next to the `.exe`. The flag flips exactly two things at runtime, decided at build time and surfaced via `src/utils/build_mode.py::IS_PORTABLE`:
1. `AppSettings._backend` — `QSettings` (Windows Registry) in the default build, `JsonSettings` rooted at `<user_data_dir>/config.json` in portable. The `QSettings` API surface AppSettings touches is tiny (`value` / `setValue` / `remove` / `sync`), so the shim in `src/utils/json_settings.py` is a focused mirror, not a full reimplementation.
2. `AppSettings.get_user_data_dir()` — `Documents\Smart Citizen\` (or whatever the user has configured) in the default build; `<exe-dir>/data/` in portable when frozen, or `<repo-root>/portable_data/` when running unfrozen for testing.

All registry-tree migrators no-op in portable mode — there's nothing to migrate from. The build-script-generated `src/utils/_build_info.py` (`IS_PORTABLE = True`) is written before PyInstaller runs and deleted afterward so the source tree is never committed in portable-mode state.

### Frontend version stamp on apply
At apply-to-game time, `main_window._stamp_frontend_version(merged)` appends ` | Localizations Enhanced with Smart Citizen v{VERSION}` to the launcher's `Frontend_PU_Version` loc-key, so users can confirm in-game that the loc-pack is active. `_FRONTEND_VERSION_STAMP_RE` strips any previous stamp first, so the suffix never piles up across repeated applies or version upgrades. If the key is absent from the merge (older patches, custom configs), the stamp is silently skipped — never inserted.

## File Locations

| What | Where |
|------|-------|
| Settings (registry build) | Windows Registry: `HKEY_CURRENT_USER\Software\Osiris DevWorks\Smart Citizen` |
| Settings (portable build) | `<user_data_dir>/config.json` (via `JsonSettings`) |
| User data root (registry build) | Configurable via `user_data_dir` (alias `UserDataDir` is also read); defaults to `Documents\Smart Citizen\` |
| User data root (portable build) | `<exe-dir>/data/` when frozen, `<repo-root>/portable_data/` when running unfrozen |
| **Per-channel data** | `{user_data_root}\{LIVE|PTU|EPTU|HOTFIX|TECH-PREVIEW}\` — 0.9.3+ nests user.ini / cache / backups / dataforge under the active channel so each SC channel is isolated. Migrator: `AppSettings.migrate_game_path_to_channel_layout()`. |
| User overrides | `{user_data_root}\{active_channel}\user.ini` (legacy `overrides.ini`, auto-migrated) |
| Cached sources | `{user_data_root}\{active_channel}\cache\` — only `base.ini` post-1.0 (the four legacy URL-based source INIs were retired in 0.7.0); enhancement INIs live alongside it, see below |
| DataForge cache | `%LOCALAPPDATA%\Osiris DevWorks\Smart Citizen\{active_channel}\dataforge\` (entity XMLs from Data.p4k). Moved out of `Documents\` in 1.x — `migrate_dataforge_cache_to_local()` relocates the legacy `…\cache\dataforge\` tree on first launch. Resolved via `AppSettings.get_dataforge_cache_dir()`. |
| Enhancement INIs | `{user_data_root}\{active_channel}\cache\` (`ships_desc_enhancements.ini`, `components_desc_enhancements.ini`, `ship_weapons_desc_enhancements.ini`, `fps_weapons_desc_enhancements.ini`, `mission_rewards_enhancements.ini`, `commodity_crafting_enhancements.ini`) |
| Backups | `{user_data_root}\{active_channel}\backups\` (max 5, oldest auto-deleted) |
| Game file | `{sc_install_root}\{active_channel}\data\Localization\english\global.ini` — resolved via `AppSettings.get_global_ini_path()` |
| P4K tools | `assets/unp4k/` (`unp4k.exe`, `unforge.exe`) |
| DataForge patches | `patches/` (JSON files mirroring DataForge layout; applied post-extraction) |
| Help/About content | `HELP.md`, `ABOUT.md` at repo root — rendered inside the in-app help panel |
| Legal tab content | `LEGAL.md` at repo root — CIG community-content compliance, license summaries, privacy/data-handling disclosure, AI-use statement; bundled via `SmartCitizen.spec` and rendered through the same markdown→HTML pipeline as About |
| Linux/Wine guide | `LINUX.md` at repo root — user-facing Wine-prefix walkthrough; not loaded by the app |

## Common Modification Points

| Task | File | Key Function |
|------|------|-------------|
| Add/change table columns | `main_window.py`, `string_table_model.py` | `setup_string_table()`, `NUM_COLUMNS` + `COL_*` constants (also referenced by `entry_filter.py`'s getter tuple) |
| Add/change filters (UI wiring) | `main_window.py` | `apply_filters()`, `on_filter_changed()` |
| Change row-filter logic | `entry_filter.py` | `filter_entry_indices()` (delegated to from `MainWindow._filtered_entry_indices`) |
| Change per-column filter widgets | `filter_header.py` | `FilterHeaderView` |
| Change category extraction | `string_model.py` | `StringEntry.extract_category()` |
| Modify INI parsing | `ini_parser.py` | `parse_ini_file()` |
| Change merge logic | `ini_merger.py` | `merge_sources_by_hierarchy()` |
| Change overrides persistence | `user_ini_manager.py` (save) / `ini_parser.py` (load) | `save_user_ini()`, `load_overrides()` |
| Change user INI import behavior | `import_dialog.py`, `user_ini_manager.py` | `ImportConflictDialog` |
| Change table columns / model | `string_table_model.py`, `main_window.py` | `StringTableModel`, `COL_*` constants, `setup_string_table()` |
| Modify auto-update | `updater.py` | `check_for_updates()`, `download_base_file()` |
| Change backup behavior | `main_window.py` | `manage_backups()` |
| Modify P4K extraction | `pak_extractor.py` | `extract_dataforge()` |
| Change enhancements generation | `scripts/generate_enhancements_ini.py` | (standalone script) |
| Add performance profiling | `perf.py` | `@timed` decorator |
| Change user data paths | `settings.py` | `AppSettings.get_user_data_dir()` |
| Change DataForge freshness | `settings.py`, `main_window.py` | `dataforge_cache_is_fresh()` |
| Change stats/favorites UI | `enhancements_tab.py` | `setup_ui()` |
| Manage Config tab UI | `config_tab.py` | `setup_ui()`, drag-drop hierarchy setup |
| Manage Enhancements tab UI | `enhancements_tab.py` | `setup_ui()`, stats toggle, favorites config |
| Change in-app logging | `log_tab.py` | `LogTab`, `_QtLogHandler` |
| Change user.cfg behavior | `user_cfg.py` | `ensure_user_cfg_language()` |
| Fix an upstream DataForge data bug | `patches/<category>/.../<name>.patch.json`, `dataforge_patcher.py` | `apply_patches()` |
| Change parallel progress reporting | `progress_sink.py` | `ProgressSink.advance()` |
| Change post-apply validation | `applied_file_validator.py` | `validate_applied_file()` (wrapped by `MainWindow._validate_applied_file`) |
| Change About / Help markdown rendering | `markdown_renderer.py` | `markdown_to_html()` (wrapped by `MainWindow.markdown_to_html`, which supplies palette colours) |
| Add or modify a background worker | `workers.py` | The relevant `*Worker` class (subclass of `QThread`) |
| Change resource-path resolution (PyInstaller bundle vs dev) | `resource_path.py` | `get_resource_path()`, `resolve_patches_dir()` |
| Toggle portable vs registry build mode | `scripts/build/build_exe.py`, `src/utils/build_mode.py` | `--portable` flag, `IS_PORTABLE` |
| Change portable-mode settings backend | `src/utils/json_settings.py`, `src/utils/settings.py` | `JsonSettings`, `AppSettings._backend` |
| Skip clean enhancement categories on re-extract | `src/utils/dataforge_diff.py`, `pak_extractor.py` | `update_manifest()`, `dirty_categories()`, `CATEGORY_SUBTREES` (mirrors `DATAFORGE_KEEP_SUBPATHS`) |
| Change Export Loc-Pack zip behavior | `src/utils/locpack_exporter.py` | `default_locpack_filename()`, `write_locpack_zip()` |
| Change apply-time launcher watermark | `src/gui/main_window.py` | `_stamp_frontend_version()`, `_FRONTEND_VERSION_KEY`, `_FRONTEND_VERSION_STAMP_RE` |
| Change Modified/Enhanced/Unmodified/New status logic | `src/parser/ini_parser.py` | `_determine_status_from_source()` |
| Adjust close-time user.ini autosave guard | `src/utils/user_ini_manager.py` | `should_autosave_user_ini()` |
| Change "Reset user.ini" tool behavior | `src/utils/user_ini_manager.py`, `src/gui/config_tab.py` | `reset_user_ini()` (+ Config-tab button wiring) |
| Move DataForge XML cache out of Documents | `src/utils/settings.py` | `migrate_dataforge_cache_to_local()`, `get_dataforge_cache_dir()` |
| Add a tag-builder element/style/category | `src/utils/tag_builder.py` | `CATEGORY_ELEMENT_KINDS`, `STYLES_BY_KIND`, `DEFAULT_TAG_CONFIGS`, `render_tag()` |
| Change Tag Builder UI / live preview | `src/gui/enhancements_tab.py`, `src/gui/tag_mapping_dialog.py` | `_PREVIEW_VALUES`, `TagMappingDialog` |
| Persist/load tag configs | `src/utils/settings.py` | `AppSettings.get_tag_config()`, `set_tag_config()`, `get_all_tag_configs()` |
| Add a new stats-enhancement generator (e.g. mining/salvage analogue) | `scripts/generate_enhancements_ini.py` | `enhancements_mining_laser`, `enhancements_salvage_tool` (reference pattern); register in `CATEGORY_SUBTREES` + `DATAFORGE_KEEP_SUBPATHS` |

## Version & Release

### Branching model

Smart Citizen uses **long-lived release branches as integration targets**, not feature-branch-into-main.

- **Immediately after a release ships**, the next `release/X.Y.Z` branch is opened off `main` and `VERSION.TXT` is bumped on it. That branch becomes the integration target for all subsequent work until it ships.
- **The version in the branch name signals the scope of work that belongs there.** A patch bump (e.g. `release/1.4.1`) is reserved for **bug fixes and minor polish** — anything bigger waits for the next minor or major. Treat the branch version as a scope filter when reviewing or proposing changes: don't land a new feature on a patch branch without flagging the scope mismatch.
- **All PRs target the active `release/X.Y.Z` branch, not `main`.** `main` only ever receives a release-branch merge.
- When the integration branch is feature-complete and stable, **the user adds the `build-installer` label to a PR** to produce a tester installer artifact (see *Tester pre-release installers* below). Testing happens against those artifacts before any merge to `main`.
- **Merging `release/X.Y.Z` → `main` is the release trigger.** That merge is when the per-release checklist below runs (tag, GitHub release, Discord webhook). Until that merge, no commit on the release branch is "released."

So: don't propose tagging, drafting release notes, or merging to `main` mid-integration — the user drives that handoff explicitly. During integration, normal work is just landing PRs on the release branch.

### Release checklist (when `release/X.Y.Z` is ready to merge to `main`)
1. `VERSION.TXT` should already match the branch name from when the branch was opened — confirm it (sole source of truth; `installer.iss` reads it via ISPP at compile time).
2. Build the PyInstaller onedir: `.venv/Scripts/python.exe scripts/build/build_exe.py`
3. Compile the installer (Inno Setup is a per-user install, invoke via PowerShell): `powershell -NoProfile -Command "& 'C:\Users\<you>\AppData\Local\Programs\Inno Setup 6\ISCC.exe' installer.iss"`
4. Test installer from `dist/SmartCitizen-{VERSION}-Setup.exe`
5. Merge `release/X.Y.Z` into `main`, then tag on `main` (`git tag -a vX.Y.Z -m "Release vX.Y.Z"`), push branch + tag.
6. Create GitHub release and attach `dist/SmartCitizen-{VERSION}-Setup.exe` (installer only; portable onefile exe has been retired).
7. Open the next `release/X.Y.(Z+1)` branch off `main` and bump `VERSION.TXT` on it — this is the new integration target.

Discord notification is automatic via GitHub Actions (`scripts/discord_notify.py`) if `DISCORD_RELEASE_WEBHOOK_URL` secret is configured.

**Tester pre-release installers**: `.github/workflows/installer-preview.yml` builds a downloadable `SmartCitizen-{VERSION}-Setup.exe` artifact outside the standard release flow. Two triggers: (1) `workflow_dispatch` from the Actions tab against any branch, and (2) adding the `build-installer` label to a PR (subsequent pushes to the labeled PR rebuild via the `synchronize` event; remove the label to stop the rebuilds). In the integration-branch model this is the *primary* signal that a release is approaching test sign-off — when the user adds the label, treat the active release branch as approaching ship. Artifact name is `smartcitizen-installer-{SHA}`, retention 30 days (testers need lead time vs. CI's 7), and `installer-preview-cleanup.yml` deletes the artifacts on PR merge so the Actions storage doesn't accumulate stale builds. The `concurrency` group cancels in-flight builds when a newer commit lands on the same PR / branch.

## Debugging

- **Registry**: `regedit` → `HKEY_CURRENT_USER\Software\Osiris DevWorks\Smart Citizen` (live tree). Pre-0.9 installs leave a parallel `Osiris DevWorks\SC Localization Editor` tree that the in-app migrator drains on next launch.
- **User data path**: If `Documents` is redirected (OneDrive), Registry stores the override under `user_data_dir` (legacy/manual alias `UserDataDir` is also honored); delete that value to reset and auto-detect on next run.
- **Threading hangs**: Check `worker.quit()` + `worker.wait()` are called in finished slots. Use Log Tab to watch for blockages.
- **File encoding**: Parser expects UTF-8; BOM or other encodings fail silently. Ensure cache files are UTF-8 no-BOM.
- **GitHub API rate limit**: Unauthenticated, 60 requests/hour per IP. Check updater logs if auto-update stalls.
- **Overrides not loading**: Verify `{user_data_root}\{active_channel}\user.ini` exists with `key=value` format (no sections). If you find a legacy `Documents\SC Localization Editor\overrides.ini`, both the rename (`overrides.ini` → `user.ini`) and the channel-nesting migration are handled lazily by `AppSettings` — launching the app once should drain them.
- **Performance**: Use `@timed` decorator on slow functions and check elapsed times in DEBUG logs.
- **Test isolation**: Each test should not depend on Registry state; mock `AppSettings` or use conftest fixtures.

## Dependencies

- **PyQt6** (>=6.10.0) — GUI framework
- **pyinstaller** (>=6.3.0) — Executable builder
- **pyperclip** (>=1.8.2) — Clipboard access
- **lxml** (>=5.0) — XML parsing for DataForge entity XMLs (`dataforge_patcher.py`, mission classifiers in `generate_enhancements_ini.py`)

Windows-only by default (uses Windows Registry via QSettings in the standard build; portable builds skip the registry and write to a JSON file next to the `.exe`). Python 3.9+, recommended 3.10+.
