# tests/CLAUDE.md

Test suite layout. See the root `CLAUDE.md` for project context.

## Unit tests

Split by domain:

- `test_core.py` — INI parsing/merging/category extraction. `TestStringEntry` is `@pytest.mark.skip`: its constructor calls predate `category` and `status` becoming required positional args (cleanup pending).
- `test_missions.py` — mission rewards pipeline.
- `test_mission_engagement.py` — FPS / Ship / FPS&Ship engagement classifier from CIG loc-key naming.
- `test_mission_turrets.py` — turret detection from `SpawnDescription_ShipGroup Name="Turrets"` plus the `OverrideTurretHosility_BP` mission-variable signal. Fabricated XML, so no populated cache needed.
- `test_blueprint_pools.py` — multi-source pool merge regression, component-style tag annotation, CIG-prefix strip, pool rank-tier label.
- `test_pak_extraction.py` — P4K/DataForge.
- `test_progress_sink.py` — thread-safe progress coalescing.
- `test_dataforge_patcher.py` — declarative XML patching.
- `test_app_updater.py` — GitHub Releases version-check worker.
- `test_channel_layout.py` — per-channel directory migration.
- `test_retired_url_sources_migration.py` — 1.0 cleanup of contracts/components/ships/commodities/gear sources retired in 0.7.0. Covers fresh-install defaults, upgrade-time prune, URL-vs-local guard, idempotence.
- `test_applied_file_validator.py` — post-apply `global.ini` vs stock `base.ini`.
- `test_entry_filter.py` — column-filter logic plus the `NUM_COLUMNS` getter-tuple drift guard.
- `test_markdown_renderer.py` — About/Help markdown→HTML.
- `test_resource_path.py` — PyInstaller `_MEIPASS`-aware paths.
- `test_status_classification.py` — post-1.3.0 `_determine_status_from_source` (Enhanced vs Modified).
- `test_user_cfg.py` — `g_language = english` in user.cfg.
- `test_user_ini_autosave_guard.py` — v1.3.0 regression guard: `should_autosave_user_ini` refuses a close-time autosave that would truncate a populated `user.ini` to 0 bytes after a load mismatch.
- `test_frontend_version_stamp.py` — `Frontend_PU_Version` watermark applied at apply-to-game time.
- `test_portable_mode.py` — portable flag flips `AppSettings._backend` to `JsonSettings` and routes `get_user_data_dir()` next to the exe.
- `test_build_info_fallback.py` — `build_mode.py` falls back to `IS_PORTABLE = False` when `_build_info.py` is absent.
- `test_json_settings.py` — file-backed `QSettings`-API shim for portable mode.
- `test_locpack_exporter.py` — Loc-Pack zip writer.
- `test_tag_builder.py` — TagConfig serialization + `render_tag` output shape.
- `test_tag_config_settings.py` — TagConfig persistence via `AppSettings`. Covers the 1.4.0 rename `Phys`/`Distort`/`Bio` → `Physical`/`Distortion`/`Biochemical`.
- `test_mining_salvage_stats.py` — 1.4.0 `enhancements_mining_laser` / `enhancements_salvage_tool` extractors. Per-mode beam stats for mining heads and handheld salvage tools, fabricated XML.
- `test_ship_weapon_tag.py` — 1.4.0 guard for `_ship_weapon_name_tag_factory`: EMP devices with size but no damage and tractor beams must NOT emit a damage tag; real combat weapons must.
- `test_user_ini_reset.py` — `reset_user_ini(path, *, backup=True)` contract for the Config tab's **Reset user.ini** button. Returns `None` when source absent, `backup=True` renames to a timestamped sibling, `backup=False` deletes outright, same-second double-call doesn't clobber the first backup.

QThread workers in `src/gui/workers.py` have no automated tests — they need `pytest-qt` (not a dev dep). Manual smoke testing is the only path.

## Pytest config

`pytest.ini` at the project root, not under `tests/` — placing it there makes rootdir resolve to `tests/` and breaks the `from src.X` imports CI uses. `pythonpath = . src` (project root for `from src.X`, `src/` for legacy `from utils.X`). Markers: `unit`, `integration`, `slow`, `critical`, `regression`.

## Test isolation

Tests should not depend on Registry state; mock `AppSettings` or use conftest fixtures.

## GUI testing

Manual. Run app, load base file, edit a value, apply to game, restart to verify persistence. Watch the Log Tab for load/merge/apply errors.
