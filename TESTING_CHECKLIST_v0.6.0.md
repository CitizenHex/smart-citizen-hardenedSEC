# SC Localization Editor v0.6.0 - Testing Checklist

**Test Date**: ___________  
**Tester**: ___________  
**Environment**: Windows 10/11, Python 3.9+, PyQt6

---

## Quick Setup

```bash
pip install -r requirements.txt
python src/main.py
```

---

## 1. Application Startup & Initialization

- [ ] **App launches without crashing**
  - Run `python src/main.py` and wait 2-3 seconds for initial load
  - Verify main window appears with three tabs (Strings, Config, About)

- [ ] **Settings migrate/persist correctly**
  - Check Registry at `HKEY_CURRENT_USER\Software\Osiris DevWorks\SC Localization Editor`
  - Verify window geometry, source paths, and hierarchy are preserved

- [ ] **First-run bootstrap (if new user)**
  - Delete existing `Documents\SC Localization Editor\` directory
  - Run app and monitor initial download/cache setup
  - Verify app doesn't hang during "Auto-downloading missing sources" phase
  - Check that `Documents\SC Localization Editor\cache\` contains `base.ini` and `contracts.ini`

- [ ] **Status bar displays correctly**
  - Verify status bar shows per-source sync status (e.g., "Global: 4.7.0-LIVE ✓  |  Contracts: 2026-03-28 ✓")
  - Status should update after auto-update checks complete

---

## 2. Core Data Loading & Merging

- [ ] **Base file loads without errors**
  - Strings tab appears with populated table
  - Row count shown (should be 80,000+)
  - All six columns visible: Category, Key, Default Value, Current Value, Custom Value, Status

- [ ] **Multi-source merge works correctly**
  - Switch to Config tab
  - Click "Preview Merge" button
  - Dialog shows merge order, key counts per source, and final merged total
  - No errors or exceptions logged to console

- [ ] **Category extraction is accurate**
  - Check for Ships category entries (e.g., `vehicle_Name*`)
  - Check for Ship Components (e.g., `item_NameSHLD_*` for shields)
  - Check for Gear category (e.g., `item_Name_*` for FPS weapons)
  - Check for Commodities category (e.g., `items_commodities_*`)
  - Check for Missions category (e.g., `contract_*`, `shubin_*`)

- [ ] **Merge hierarchy is respected**
  - Go to Config tab and note current hierarchy order
  - Enable a lower-priority source and edit a key in it
  - Reload (Save Configuration) and verify higher-priority sources override it
  - This confirms last-wins merge algorithm works

---

## 3. Stats Generation & P4K Extraction (Critical for v0.6.0)

### Initial Setup
- [ ] **DataForge cache freshness is detected**
  - Config tab shows "DataForge cache last updated: [date]" or "Cache is stale"
  - Freshness check compares p4k mtime against cache creation time

- [ ] **Extract DataForge button is clickable (only if game path is set)**
  - Set game install path in Config tab to valid Star Citizen installation
  - Verify "Extract DataForge from P4K" button is enabled (greyed out if no game path)

### Extraction Workflow
- [ ] **P4K extraction starts without hanging**
  - Click "Extract DataForge from P4K" button
  - Progress dialog appears and updates regularly
  - No "Not Responding" UI freeze

- [ ] **Extract completes successfully**
  - Progress dialog closes when extraction finishes
  - Check `Documents\SC Localization Editor\cache\dataforge\` contains subdirectories: `entity/`, `entities/`, `entityclasses/`, `ships/`, `weapons/`
  - At least some XML files exist in those directories

- [ ] **Extract handles missing/invalid p4k gracefully**
  - Set game path to invalid location
  - Click "Extract DataForge from P4K"
  - Error dialog appears with helpful message (e.g., "Data.p4k not found")
  - App doesn't crash; can still interact with other tabs

- [ ] **Stats INI files generate correctly**
  - After successful DataForge extraction, verify these files exist in cache:
    - `ships_desc_stats.ini`
    - `components_desc_stats.ini`
    - `ship_weapons_desc_stats.ini`
    - `fps_weapons_desc_stats.ini`
  - Each file should contain `key=value` entries (not empty)

### Stats Integration
- [ ] **Stats are loaded and merged**
  - Config tab has "Stats enabled" toggle (should be ON by default)
  - Click "Save Configuration & Merge"
  - Switch to Strings tab and search for vehicle_Desc entries
  - Verify some entries show detailed stats (e.g., "Max Speed: 210 m/s, Cargo: 180 SCU")
  - Stats come from `ships_desc_stats.ini` merge

- [ ] **Stats disabled works**
  - Config tab: toggle "Stats enabled" OFF
  - Click "Save Configuration & Merge"
  - Search for same vehicle_Desc entries
  - Stats should be gone (only base descriptions from sources remain)

- [ ] **Stale cache prompts re-extraction**
  - Touch `Data.p4k` to update its mtime (or artificially set old cache time)
  - Restart app
  - Config tab should show "Cache is stale" and prompt to re-extract
  - Option to extract or ignore

---

## 4. Table Functionality

- [ ] **Search/filter works**
  - Type in search box (e.g., "shield")
  - Table filters to matching entries
  - Debounce prevents lag (300ms delay)

- [ ] **Category filter works**
  - Select "Ships" from category dropdown
  - Only vehicle_Name/Desc entries visible
  - Select "Ship Components" → only shields, coolers, power plants visible
  - Select "Gear" → only item_Name_* FPS weapons visible

- [ ] **Status filter works**
  - Select "Modified" from status dropdown → shows green entries (user edits)
  - Select "Unmodified" → shows gray entries
  - Select "New" → shows orange entries (user-added only)

- [ ] **Hide Unmodified toggle works**
  - Check "Hide Unmodified" → table shows only Modified + New
  - Uncheck → shows all entries

- [ ] **Favorites filter works**
  - Right-click a Ship entry → "★ Add to Favorites"
  - Check "★ Favorites Only" checkbox
  - Table shows only favorited entries (those with `*` prefix in custom_value)
  - Uncheck → all entries visible again

- [ ] **Columns are sortable**
  - Click "Category" header → table sorts by category
  - Click "Key" → sorts by key name
  - Click again → reverse sort
  - Verify row data stays in sync after sort (use `_entry_index_for_row()` correctly)

---

## 5. Editing & Persistence

- [ ] **Double-click to edit Custom Value**
  - Find an entry
  - Double-click Custom Value column
  - Edit text and press Enter
  - Row highlights as green (Modified) if value differs from original

- [ ] **Right-click context menu**
  - Right-click a row
  - Menu shows: Edit, Reset to Original, Copy Key, ★ Add to Favorites
  - Each option works as expected

- [ ] **Reset to Original**
  - Edit a value, then right-click → "Reset to Original"
  - Custom Value becomes empty
  - Row changes to gray (Unmodified)

- [ ] **Edits persist after restart**
  - Edit 2-3 entries
  - Click "Apply to Game"
  - Close and restart app
  - Verify those entries still show as Modified with same custom values

- [ ] **Overrides.ini is written correctly**
  - Make edits and click "Apply to Game"
  - Check `Documents\SC Localization Editor\overrides.ini`
  - File contains only Modified + New entries (not unmodified ones)
  - Format is correct: `key=value` per line

---

## 6. Apply & Backup System

- [ ] **Apply to Game creates backup**
  - Make a test edit
  - Click "Apply to Game"
  - Dialog shows: "Backup created: global.ini.bak_YYYYMMDD_HHMMSS"
  - Check `Documents\SC Localization Editor\backups\` → backup file exists

- [ ] **Backup file contains correct data**
  - Open backed-up file in text editor
  - Verify it's a valid INI file with many keys
  - Not empty or corrupted

- [ ] **Game file is written correctly**
  - Check game's `LIVE/data/Localization/english/global.ini` (read-only to verify)
  - Modified entries should be present in the file
  - File size increased from base due to merges

- [ ] **Backup rotation (max 5 backups)**
  - Apply to Game 6+ times (creating 6+ backups)
  - Check `Documents\SC Localization Editor\backups\`
  - Only latest 5 backups remain (oldest deleted)

- [ ] **Restore Backup works**
  - Click "Restore Backup" button
  - Dialog shows list of available backups
  - Select one and confirm
  - Game file is restored to that backup's state
  - App reloads and shows entries from restored file

---

## 7. Auto-Update System

- [ ] **Auto-update checks on startup**
  - Monitor console output on app launch
  - Should see GitHub API check messages (not required to show in UI)
  - Status bar updates with latest version info (if available)

- [ ] **Manual update check**
  - Config tab: "Check for Updates" button (if present)
  - Click and wait ~2-3 seconds
  - Dialog shows latest version or "You're up to date"

- [ ] **Downloads work without hanging**
  - If update available, click "Download & Install"
  - Progress dialog shows download progress (% or MB/s)
  - No UI freezes during download
  - When complete, dialog shows success message

- [ ] **Per-source auto-update flags**
  - Config tab shows auto-update checkboxes for each source
  - Toggle one OFF, save configuration
  - Verify that source doesn't auto-update on next app restart
  - Toggle back ON, save, verify it re-enables

---

## 8. Clear Localization

- [ ] **Clear Localization button works**
  - Click "Clear Localization" toolbar button
  - Confirmation dialog appears
  - Click "Yes"
  - Game's `global.ini` is deleted
  - Overrides.ini is preserved (not deleted)

- [ ] **Game reverts to vanilla after clear**
  - Launch game after clearing localization
  - Verify game shows default English text (not localized)

- [ ] **Edits can be re-applied after clear**
  - Clear localization (deletes game file)
  - Click "Apply to Game" again
  - Overrides re-apply on top of new merge
  - Game file recreated with customizations

---

## 9. Config Tab & Source Management

- [ ] **Config tab displays all sources**
  - Each source shows: enable checkbox, path/URL input, browse button, auto-update checkbox
  - User source doesn't show auto-update (disabled)

- [ ] **Source paths resolve correctly**
  - Set a source to a local file path
  - Click browse, select file
  - Path is saved and file loads on merge

- [ ] **URL conversion works**
  - Paste a GitHub browser URL (e.g., `https://github.com/repo/blob/master/file.ini`)
  - Config tab auto-converts to raw URL (e.g., `https://raw.githubusercontent.com/...`)
  - When merged, file downloads correctly

- [ ] **Drag-drop hierarchy reordering**
  - Drag "Contracts" above "Global" in hierarchy list
  - Click "Save Configuration & Merge"
  - Click "Preview Merge" to confirm new order
  - Merge respects new order (later sources override earlier ones)

- [ ] **Game path setting**
  - Config tab game path field
  - Click browse, select valid Star Citizen installation
  - Path is saved and used for P4K extraction
  - App can find `Data.p4k` when extracting DataForge

---

## 10. Threading & UI Responsiveness

- [ ] **App doesn't freeze during large file load**
  - Load a 83k+ line file
  - App should remain responsive (can interact with UI while loading)
  - Loading completes in 1-2 seconds

- [ ] **Extraction doesn't freeze UI**
  - During P4K extraction, UI remains responsive
  - Can cancel extract operation
  - Can switch tabs or interact with other controls

- [ ] **Downloads don't freeze UI**
  - Download a large file (2+ MB)
  - Progress dialog shows updates
  - UI remains interactive (can cancel)

- [ ] **Table updates don't lag**
  - Apply filters to large table (10k+ visible rows)
  - No noticeable lag or stutter
  - Sorting large table is snappy

---

## 11. Error Handling & Edge Cases

- [ ] **Invalid INI files handled gracefully**
  - Set a source to a corrupted/invalid INI file
  - Click "Save Configuration & Merge"
  - Error dialog appears with helpful message
  - App doesn't crash

- [ ] **Missing source file**
  - Set a source URL to non-existent GitHub path
  - Click "Save Configuration & Merge"
  - Error dialog: "Failed to download [source]"
  - Options: Retry, Skip, or Cancel
  - Selecting Skip allows merge to continue with remaining sources

- [ ] **No game path set**
  - Clear game install path in Config tab
  - "Extract DataForge" button is disabled (greyed out)
  - Stats generation still works (if cache exists)
  - No crash when trying to extract

- [ ] **Duplicate keys in sources**
  - If a source has duplicate keys, last value wins (no error)
  - Entry shows value from last-occurring key

- [ ] **Empty custom value**
  - Edit an entry, then clear custom value completely
  - Status should revert to "Unmodified"
  - Overrides.ini doesn't include empty entries

---

## 12. About Tab

- [ ] **About tab displays correctly**
  - Shows project title, version (0.6.0), features list
  - Links to GitHub, MrKraken, ExoAE, BeltaKoda are clickable
  - Donation links (PayPal, Venmo) are clickable

- [ ] **Version is correct**
  - About tab shows "v0.6.0"
  - Matches VERSION.TXT file

---

## 13. Crash & Stability Tests

- [ ] **No console errors on startup**
  - Run `python src/main.py` 2>&1 in terminal
  - Monitor for any exceptions or tracebacks
  - App should start cleanly (may have info/debug logs, but no errors)

- [ ] **No memory leaks over extended use**
  - Keep app open for 10+ minutes
  - Perform several operations (load, filter, edit, merge)
  - Monitor memory usage (Task Manager)
  - Should not continuously increase

- [ ] **No orphaned threads**
  - After extraction or download completes, close app
  - Verify no Python processes remain running
  - (Run `tasklist | findstr python` in terminal)

- [ ] **Registry doesn't get corrupted**
  - Make multiple config changes and restarts
  - Check Registry at `HKEY_CURRENT_USER\Software\Osiris DevWorks\SC Localization Editor`
  - All values are readable and correctly formatted

---

## 14. Installer & Build (if building release)

- [ ] **Executable builds without errors**
  - Run `cd scripts/build && python build_exe.py`
  - No errors during build
  - Output: `dist/SCLocalizationEditor-v0.6.0.exe`

- [ ] **Standalone exe runs**
  - Double-click the built exe
  - App launches without any Python errors
  - All features work as expected

- [ ] **Installer creates Start Menu shortcut**
  - Run `SCLocalizationEditor-v0.6.0-Setup.exe`
  - Follow installer prompts
  - Installer completes successfully
  - Start Menu contains "SC Localization Editor" shortcut

- [ ] **Uninstaller removes files**
  - Windows Add/Remove Programs → uninstall
  - Verifies all app files removed (except Documents user data, which is preserved)

---

## Test Results Summary

**Test Date**: ___________  
**Tester**: ___________  
**Total Tests**: 120+  
**Passed**: ___  
**Failed**: ___  

### Failed Tests
(List any failed tests and reproduction steps)

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

### Notes & Observations
_____________________________________________
_____________________________________________
_____________________________________________

---

## Sign-off

- [ ] **All critical tests passed** (Startup, Data Loading, Apply to Game, Backup/Restore)
- [ ] **All stats generation tests passed** (Extraction, INI generation, loading, merging)
- [ ] **No critical bugs found**
- [ ] **Ready for release**

**Tester Signature**: _______________  
**Date**: _______________
