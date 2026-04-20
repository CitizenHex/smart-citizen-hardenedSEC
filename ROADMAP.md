# 0.1.x Initial Beta
## 0.1.0
* [x] load and edit global.ini strings
* [x] filter and search functionality
* [x] apply changes to game with automatic backups
* [x] basic help and configuration dialogs

## 0.1.1 Professional UI & Threaded Loading
* [x] threaded file loading so 83k+ line global.ini doesn't freeze the UI
* [x] progress dialog during file loading
* [x] remove deprecated target_strings.ini prompt
* [x] styled About tab with theme-aware markdown rendering
* [x] redesigned Help dialog
* [x] Osiris DevWorks footer branding with PayPal/Venmo donation buttons
* [x] clearer config placeholder text and path examples

# 0.2.x Auto-Update, Persistence & Migration
## 0.2.0
* [x] GitHub auto-update check for base localization file (BeltaKoda/ScCompLangPackRemix)
* [x] persistent customizations saved to `overrides.ini` and reloaded on startup
* [x] seamless migration: saved edits automatically re-applied to new base file after SC updates
* [x] first-run bootstrap diffs existing game file against reference and extracts prior edits
* [x] improved threading with worker thread cleanup and 60s socket timeout
* [x] installer supports upgrade from 0.1.x (uninstalls old version)

# 0.3.x Contracts Auto-Update & Missions Filter
## 0.3.0
* [x] contracts.ini auto-update from MrKraken/StarStrings (tracks by commit SHA and date)
* [x] parallel update checks for base file and contracts
* [x] Missions category in filter dropdown
* [x] contracts merge overrides global.ini automatically
* [x] tooltips on hover for all table cells (shows full truncated text)
* [x] fix window/taskbar icon
* [x] fix BOM handling (utf-8-sig) for contracts.ini
* [x] fix duplicate closeEvent() that broke overrides auto-save
* [x] fix installer permissions for Start Menu shortcuts

# 0.4.x Multi-Source Configurable System
## 0.4.0
* [x] multi-source configurable system (Global, Contracts, Components, Ships, User) with customizable merge hierarchy
* [x] AppData-based cache location (proper permissions, out of app dir)
* [x] auto-download missing cache files from configured sources on first run
* [x] intelligent source filtering by file type
* [x] preview merge improvements with auto-conversion of GitHub URLs
* [x] create empty overrides.ini on first run if missing
* [x] fix stack overflow from synchronous loading
* [x] build scripts and PyInstaller specs added to version control

# 0.5.x Favorites, Stats, and Source Independence
## 0.5.0
* [x] ship favorites: star column + configurable prefix character prepended to favorited ship names (sorts them to top in-game)
* [x] apply-button migration when changing favorite prefix
* [x] scunpacked-data stats enhancements: `generate_stats_ini.py` appends numerical stats (SCM, DPS, shield HP, cargo, turrets, etc.) to ship/component/ship weapon/FPS weapon descriptions
* [x] stats toggle in Config tab
* [x] sortable columns (click header to sort, click again to reverse)
* [x] Clear Localization button reverts game to vanilla without losing overrides
* [x] backups moved to `Documents\SC Localization Editor\backups\` (with automatic migration from old location)
* [x] fix Modified status not showing on reload for rows edited in a previous session
* [x] fix ship category detection for lowercase `vehicle_name` prefix (Starlancer variants)
* [x] filter out `_short,P` plural variants and `_Desc` entries from Ships list
* [x] remove `TheCollector_*` from Ships category
* [x] rename FPS weapon "Effective Range" → "Range"

## 0.5.1 Stock Baseline & Startup Sync
* [x] global source switched to BeltaKoda stock-global.ini (clean unmodified baseline)
* [x] components.ini extracted from MrKraken's component strings, reformatted as `Name (GRADE-Sn-T)`, hosted in this repo
* [x] dedicated commodities.ini (illegal/specialty commodity names)
* [x] startup sync of all remote sources via conditional GET (only downloads if changed)
* [x] per-source sync status in status bar (`Syncing global...` → `Global: ✓` / `updated ↑`)
* [x] Apply to Game key-set validation: rolls back and restores backup if the written file doesn't match stock keys
* [x] default merge hierarchy: `stock global → components → contracts → commodities → user overrides`
* [x] auto-migrate existing users from MrKraken global URL to BeltaKoda stock URL

## 0.5.2 Ships & Gear Sources
* [x] Ships source (ships.ini) — all stock ship names + `vehicle_Desc*` with Ironchad corrections
* [x] Gear source (gear.ini) — FPS weapons (rifles, pistols, SMGs, shotguns, snipers, LMGs) and armor/personal equipment (Geist, ADP, helmets, undersuits, backpacks) with descriptions
* [x] components.ini expanded with paired `item_Desc*` descriptions
* [x] commodities.ini expanded with full `items_commodities_*_desc` descriptions
* [x] `vehicle_Desc*` routed to Ships category
* [x] `item_Desc*` components routed to Ship Components category
* [x] new Gear category for FPS weapons and armor
* [x] remove `<EM4>` tags from `== Stats ==` header (rendered as raw text in-game)
* [x] Clear Localization dialog reminds user to click Apply to Game afterward

## 0.5.3 P4K Extraction & In-App Stats Generator
* [x] extract global.ini directly from installed Data.p4k using bundled unp4k (no more external repo dependency for base strings)
* [x] auto-prompt on startup when Data.p4k is newer than cached base.ini
* [x] Extract from Data.p4k button in Config tab
* [x] Generate Stats button in Config tab wires up the stats generator
* [x] auto-prompt on startup when stats files are missing
* [x] all default sources hosted on OsirisDevWorks (no external dependencies)
* [x] contracts.ini served from OsirisDevWorks default URL
* [x] Clear Cache auto-re-syncs all remote sources afterward
* [x] Apply to Game warns when enabled sources are missing (instead of silent skip)
* [x] Open Localization Dir button
* [x] remove MrKraken/ExoAE/BeltaKoda attribution links from footer (retained in Acknowledgements)
* [x] existing users auto-migrated from remote global URL to local P4K cache path

# 0.6.x Dependency Internalization
## 0.6.0 P4K Extraction & DataForge Stats
* [x] removed dependencies on external ini sources
* [x] started adding item stat enhancements
* [x] new `pak_extractor.py` orchestrates `unp4k.exe` → `unforge.exe` pipeline
* [x] DataForge entity XML extraction cached to `dataforge/` subdirectory
* [x] freshness check detects stale cache vs. game's Data.p4k
* [x] `generate_stats_ini.py` reads entity XMLs directly (supports shields, coolers, power plants, quantum drives, ship/FPS weapons)
* [x] ship flight stats from scunpacked ships.json
* [x] new Gear source (FPS equipment) — Osiris-DevWorks repo
* [x] new Commodities source (item names) — Osiris-DevWorks repo
* [x] 7 sources total with configurable hierarchy
* [x] category improvements: turrets → Ship Components, sized ship weapons → Ship Components, FPS weapons → Gear
* [x] Config redesign: Extract DataForge button with progress dialog, cache freshness indicator
* [x] new Enhancements and Log tabs
* [x] hotfix for missing `xml.etree.ElementTree` PyInstaller bundling

# 0.7.x Final Ship, Gear, Item & Journal Detail Enhancements & App Rearchitecture
## 0.7.0
* [x] remove data folder dependency so all enhancements are dynamically generated
* [x] rename overrides.ini to user.ini
* [x] user INI import: any external ini can be imported to update user.ini (with conflict resolution dialog)
* [x] complete enhancements for ships, gear, components, and journal items
* [x] configurable enhancements
* [x] useful info added to journal (crafting/mining information)
* [x] blueprint data in missions — `[BP]` tags in titles + full blueprint lists in descriptions
* [x] commodity crafting cross-references — `[CF]` tags + which blueprints use each commodity
* [x] journal mining guide expanded with mineral locations and crafting cross-references
* [x] instant table loading — replaced QTableWidget with QAbstractTableModel (on-demand row rendering, no startup freeze on 87k+ entries)
* [x] 15s → 0.036s sorting by moving sort to Python's `sorted()` instead of Qt's per-comparison `lessThan()`
* [x] background precomputation of default values and sort keys on worker thread
* [x] O(1) entry lookups via reverse-lookup dict
* [x] updated About tab and Help dialog with all current categories and tabs
* [x] installer preserves registry settings, backups, and user.ini across upgrades
* [x] installer fix: game path now saved correctly from directory page
* [x] end-to-end testing & version release

### 0.7.0 Hotfixes
* [x] fix crash when install dir not found

## 0.7.1 Fixes
* [x] remember install locations from previous installs when installing/upgrading a new version
* [x] grouped sort not working with commodities
* [x] Hemera is not getting its labels (fixed component stats for quantum drive + 3 others with legacy key variants)
* [x] fix missing blueprints — scan both Career and List contract handlers (closed 36 of 37 gaps vs community truth set)
* [x] Group Sort changed from persistent checkbox to one-shot button
* [x] missions with blueprint rewards but no extractable XP now included (previously silently dropped)

# 0.8.x Final Mission, Crafting, & Commodity Detail Enhancements
## 0.8.0
* [x] complete enhancements & fixes for missions
* [x] complete enhancements & fixes for crafting
* [x] complete enhancements & fixes for commodity details
* [x] mission enhancements: spawn counts (waves/enemies/non-hostiles), difficulty rating, flags (Chain, Starter, Unique), contract template lookups
* [x] stats separator changed from `== Stats ==` to `<EM3>STATS</EM3>` / `<EM3>MISSION DETAILS</EM3>` for cleaner in-game rendering
* [x] filter out components with placeholder overheat temp (450,000K)
* [x] 16 mission enhancement tests added with CSV fixture (1,288 missions) for cross-validation
* [x] stability & bugfixes
* [x] end-to-end testing & version release

## 0.8.1 Mission Annotation Fixes & Performance
* [x] Stanton Bounty Hunter missions (VLRT/LRT/MRT/HRT/ERT) show descriptions — contracts sharing a title but different desc keys each get their own stats block
* [x] blueprint list restored for `[BP]`/`[BP*]` missions (215 missions now show POTENTIAL BLUEPRINTS)
* [x] templated cargo-haul titles (Junior/Master Rank Direct Bulk Cargo Haul) show XP ranges via `ContractResult_CalculatedReward` fallback to pu_missions aggregation
* [x] CleanAir bulk hauls pick up XP via `ContractResult_ScenarioProgress PointsToAward` fallback
* [x] remove aUEC reward line from descriptions (game shows it natively)
* [x] annotation styling: `<EM3>`/`<EM4>` for missions/commodities/journal; plain text + `--- STATS ---` for ship/component/weapon items (EM tags don't render there); title XP tags now `<EM4>`-wrapped
* [x] performance: merged magazine and entity-name walks over `entities/scitem/` into one pass (~20k XMLs scanned once, saves ~30s per run)
* [x] performance: disk-cached derived lookups under `cache\dataforge\.lookups\` keyed on P4K mtime; warm stats-gen runs 100s+ → ~9.5s
* [x] installer: uninstall preserves `Documents\SC Localization Editor\backups\`
* [x] portable onefile exe retired — installer-only going forward

## 0.8.2 Bug Fixes
* [x] when a user provides a different Star Citizen installation path during setup, it isn't being propagated to the game settings — `get_game_install_path()` now mirrors the installer-written `sc_directory` into QSettings on first read, so the app survives registry cleanup or clean reinstall
* [x] what is with the BP* annotations? — intentional marker for "only some mission variants reward BP" (14 of 233 BP-annotated missions, ~6%). Descriptions already list the specific variants; added a footer line `* = only some mission variants reward bp` to `[BP*]` mission descriptions so the asterisk is self-explanatory.

# 0.9.0 Pre-Release Polish
* [x] UI themes: dark, light, SCLE and ODW themes
* [x] Rebranding as "Smart Citizen: Smarter Strings for Star Citizen"
* [x] Fix sorting of favorites column
* [x] ship armor enhancements — `entities/scitem/ships/armor/` (~197 XMLs, ~100 loc keys in base.ini). Damage multipliers (physical/energy/distortion/thermal), deflection, health pools. Reuses the weapon-damage parsing pattern; output as `ship_armor_desc_enhancements.ini` merged as a new source.

## 0.9.1
* [x] default theme progress bar is all solid and doesn't animate — retuned SCLE `Highlight` from near-max #00D4FF to #0099CC so Fusion's chunk gradient has room to animate
* [x] progress bars for other themes the two colors are too similar — shifted each theme's `Highlight` to mid-luminance (Light #1565C0, Dark #3B82F6, ODW #D4A017) so the chunk gradient's lighter/darker tones read distinctly
* [x] use better contrast on text for light and dark themes — palette disabled/placeholder tuned; secondary-text role retargeted per-theme (Light #2A2A2A, Dark/SCLE #D5D5D5, ODW #D4B876) via an app-level QSS rule
* [x] when first starting and generation says files are missing, it says 8 but lists only 6 — dialog now counts the category checkboxes it actually renders, not the underlying files
* [x] when generating stats, the footer at one point says "Ready" which is confusing because its actually still working — status bar no longer falls back to "Ready" while any extract/generate/load worker is running
* [x] Jorrit Dossier P2M1/P2M4 share blueprint awards — game-side data bug (P2M4's contract references `P2M1_Repeat_desc`); first-writer-wins guard keeps P2M1's intended pool (Pool A, 11 items). Also extended contract-template fallback so `desc_key` resolves independently of `title_key`.

## 0.9.2
* [x] parallelize enhancements generation + switch to determinate progress bars — ran independent lookup builds (ammo × 2, scitem, controller, armor, reputation) concurrently via a 6-way `ThreadPoolExecutor`, dropping the lookup phase to the time of its longest builder (scitem). Then wrapped the 7 output generators (components, missiles, ship weapons, FPS weapons, ships, mission chain, commodity/journal) as closures and fanned them across a second pool wave; the mission chain (scan → bp pools → contractgen → title/desc augmentation → coverage report) stays serial inside its one closure because its sub-phases share in-memory state. Added `src/utils/progress_sink.py` (thread-safe `(completed, total, message)` sink), extended `AnimatedProgressDialog` with `set_progress()` for determinate mode with a two-tone chunk gradient, and plumbed per-phase ticks through the enhancements worker, file loader (3 phases), P4K extract (2 phases), and DataForge extract (3 phases: unp4k → unforge → cache).
* [ ] Bounty missions from the bounty hunter guild showing the mission details but not blueprints
* [ ] Issue with P2M1/P2M4 blueprints not resolved
* [ ] Regional blueprint awards are not showing properly for their region
* [ ] Add Battlestations to other apps in about section
* [ ] Add/Update acknowledgements section to include everyone who tested and gave feedback on the application: Boogie Man, Perseuscz, Tichro, Flat Earth, Lord Valium
* [ ] finalize in-app documentation

## 0.9.3
* [ ] performance optimization
* [ ] cache streamlining
* [ ] stability & bugfixes
* [ ] end-to-end testing & version release
