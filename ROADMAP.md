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
* [x] Bounty missions from the BHG in Stanton system that do not give BPs are getting BP tag in titles — title tag now skips `[BP?]` when any desc_key bucket under that title has no BP-having variant (so `bhg_bounty_title_gen_001`, shared by 7 no-BP Stanton bounties and the 1 BP-having PAF contract, no longer advertises BPs it can't guarantee).
* [x] Issue with P2M1/P2M4 blueprints not resolved — declarative DataForge patch (`patches/contracts/contractgenerator/mercenary_guild/hockrowagency/hockrowagency_facilitydelve.patch.json`) rewrites P2M4_Repeat's Description param from the bugged `@Hockrow_FacilityDelve_P2M1_Repeat_desc` to `@Hockrow_FacilityDelve_P2M4_Repeat_desc`, so P2M4 now shows its own Power-Usage flavor text and the ASD2D pool (including the Fresnel "Icebox" Energy LMG). Patches re-apply idempotently on every DataForge extract and every regen.
* [x] Regional blueprint awards are not showing properly for their region — `mission_blueprints` now tracks per-system pools (`dict[title_key, dict[system, items]]`) populated from each contract's own debugName (not the handler's, since Shubin Rank0 hosts Stanton & Pyro siblings). The desc renderer groups pools shared by multiple systems, collapses identical pools to one section, and emits `<EM4>[Stanton]</EM4>` / `<EM4>[Nyx/Stanton]</EM4>` / `<EM4>[Pyro RegionA, Pyro RegionB]</EM4>` sub-headers for the Shubin mining, dual-system mining, and Headhunters intra-system cases respectively. Kraken-fixture flat-vs-regional gap dropped from 18 → 1.
* [x] Add Battlestations (https://battlestations.osiris-devworks.com/) to other apps in about section — added to `ABOUT.md` "Other Tools by Osiris DevWorks" list, renders in the app's About tab.
* [x] Add/Update acknowledgements section to include everyone who tested and gave feedback on the application: Boogie Man, Perseuscz, Tichro, Flat Earth, Lord Valium — added a dedicated Acknowledgements section in `ABOUT.md`.
* [x] finalize in-app documentation — refreshed `ABOUT.md` for 0.9.x: themes list now leads with SCLE (the actual default), Data Management points at the renamed `Documents\Smart Citizen\` path, acknowledgements + Battlestations added.
* [x] missiles missing type tag [CM/EM/IF] — added `_missile_name_tag` helper that reads `trackingSignalType` from the missile `<targetingParams>` (falls back to parsing "Tracking Signal: …" from the description) and appends `[S{size}-CS/EM/IR]` to `item_Name*` entries; bombs fall through to `[S{size}]`. `scan_entity_dir` gained a `name_tag_fn` hook so `_gen_missiles` can opt in.
* [x] all Wikelo ships should be classified as ships — `StringEntry.extract_category` now returns "Ships" for keys ending in `_VehicleName`, `_VehicleDesc`, or `_VehicleNameShort`, checked before the mission-prefix fallthrough that was catching `TheCollector_ShipMod_…` and routing them to "Missions".
* [x] Aluminum not getting [CF] tag when viewed in FE inventory — `commodity_loc` switched to `list[(name_key, desc_key)]` so aluminum maps to both `items_commodities_aluminum` and `items_commodities_aluminum_ore`; both the refined and ore loc-keys now get `[CF]` and the BLUEPRINT DATA block.
* [x] Hex Shield Generator not getting its annotations (but does get stats) — HEX's XML references the underscored loc keys (`item_Name_SHLD_…`) while base.ini also carries orphaned no-underscore legacy siblings (`item_NameSHLD_…`). Added an inverse-propagation pass in the component generator that mirrors the augmented underscore value onto the legacy no-underscore key (name tag + stats), keeping both in sync.
* [x] Hockrow mission with icebox fresnel reward not showing that reward on it — resolved by the P2M4 desc-key patch above (Icebox pool now renders under Hockrow P2M4_Repeat).
* [x] Extreme Risk Target Mission showing [BP?] - same with other XXX-Risk Target missions — resolved alongside the BHG Stanton title fix; the ?-Risk Target / ?-Risk Target (…) labels are variants of `bhg_bounty_title_gen_001` via `~mission(Danger)`, and the new desc-bucket rule drops `[BP?]` from that title.
* [x] Move in-app help out of an inline Python string into a standalone `HELP.md`, rendered via `get_resource_path()` like `ABOUT.md`. Also bundled `ABOUT.md`, `HELP.md`, and `patches/` in `SmartCitizen.spec` and corrected the stale `scripts/generate_stats_ini.py` entry to `generate_enhancements_ini.py` so built exes can actually regen enhancements. Fallback stub renders if either MD file can't be read.
* [x] Convert the Help dialog into a dockable side-panel (`QDockWidget` "Help", right-edge default, left/right allowed, close/move/float enabled). Built eagerly in `setup_ui` with a stable `objectName="helpDock"` so Qt's native `saveState`/`restoreState` (already wired through `AppSettings`) persists its open/closed width and dock side across sessions. Toolbar **Help** button is now `setCheckable(True)` and toggles the panel; its checked state stays in sync with the dock's `visibilityChanged` signal. Help panel's `QTextBrowser` re-renders on theme swaps via `_render_help_html`, mirroring `_render_about_html`.
* [x] Restyle the **Help** button to match the toolbar: moved to sit between Clear Cache and the trailing stretch (no longer floating to the far right), uses the `open` color role (shares the blue/cyan/gold info-action palette with Open Localization Dir), picks up live theme swaps via `refresh_action_buttons`.
* [x] Drop outdated "downloads from GitHub" / "auto-update from remote" wording from `ABOUT.md` and `HELP.md`. Base localization and DataForge data now come exclusively from `Data.p4k` extraction. Quick Start reordered so "Extract from Data.p4k" is an explicit required step; Config Tab section in HELP.md rewritten to match the current layout (Appearance / Star Citizen Installation / P4K Extraction / Import INI — no more "remote URLs" or "drag-drop merge hierarchy"); theme picker correctly pointed at Config → Appearance (was "View menu"); theme combo item labeled "Default" to match the actual UI label.
* [x] Add a `USER_DATA_DIR` registry override (`AppSettings.get_user_data_dir` / `set_user_data_dir`) so users whose Windows Documents folder is redirected to OneDrive can point the app at a local path. Cache extraction and rmtree under OneDrive are slow and race-prone (OneDrive sync hooks, Windows Search Indexer, and Defender each intercept every file create/close — 50k+ files during a DataForge extract). When the override is set, `get_user_data_dir` returns it directly; when unset, behavior is unchanged (Documents\Smart Citizen\ via the `Personal` shell-folder key). Also fixed the `shutil.rmtree` failure that prompted the investigation — new `_robust_rmtree` helper retries with 0.2–3.0s exponential backoff across 6 attempts and clears read-only bits via `onexc`, surviving the transient handles OneDrive/Defender/Indexer hold immediately after `unforge.exe` exits. Used at both `extract_dataforge` and the Clear-Cache flow.
* [x] Rename the QSettings registry node from the legacy `HKCU\Software\Osiris DevWorks\SC Localization Editor` to `Smart Citizen` so it matches the 0.9.0 product rebrand. One-shot `migrate_registry_appname` recursively copies every value and subkey (preserving REG_SZ/DWORD/BINARY types) to the new node, writes a `_migrated_from_legacy_appname` marker so subsequent launches no-op via a fast short-circuit, then depth-first deletes the old subtree. Runs as the very first step in `main()`, before any other `AppSettings` call — otherwise QSettings under the new APP_NAME would read an empty node and users would silently lose their saved theme, paths, favorites, window geometry, and the `USER_DATA_DIR` override. Partial-failure-safe: leaves marker unset on error so the next launch retries.
* [x] Installer detects a OneDrive-redirected Documents folder and offers to store Smart Citizen's data on a local path instead. New `IsDocsOnOneDrive` + `HasDataDirOverride` helpers in `installer.iss` skip the prompt when the current Documents path doesn't contain `\OneDrive\` *or* when a `user_data_dir` override is already present in either registry node. When shown, the page pre-fills `%USERPROFILE%\Documents\Smart Citizen` and writes the chosen path to `HKCU\Software\Osiris DevWorks\Smart Citizen\user_data_dir`; clearing the field keeps the OneDrive default. Page is `DataDirPromptShown`-gated so skipping it never emits a stale registry write.
* [x] Guard against CIG system-sentinel loc-keys (`LOC_UNINITIALIZED`, `LOC_PLACEHOLDER`, `LOC_BADSTRING`, `LOC_BADTOKEN`, `LOC_DEBUG`, `LOC_EMPTY`, `LOC_INVALID`, `LOC_NOINNERTHOUGHT`) — previously, contracts or entities whose `Title`/`Description`/`vehicleDescription` attribute pointed at one of these (e.g. `citizensforprosperity_destroyitems` and `thecollector` both have contracts with `@LOC_UNINITIALIZED` set) caused our generator to write the full MISSION DETAILS / POTENTIAL BLUEPRINTS / ITEM REWARDS block *into the sentinel itself*. The game then rendered that content anywhere a reference failed to bind — most visibly, the Primary Objectives panel for hauling contracts whose item entity class lacked a loc-name ("Deliver 0/15 `<= UNINITIALIZED =>`" followed by a random unrelated mission's reward block). Added `_is_sentinel_loc_ref` + `_SENTINEL_LOC_KEYS`, routed every loc-key extractor (`_loc_key`, `_loc_name_key`, `_mission_loc_key`, `scan_spaceships`, the contract-generator Title/Description path, and the `pu_missions` XP-augmentation second pass) through it. Also moved `generate_enhancements_ini.py`'s `OUTPUT_DIR` from a module-level `Personal`-shell-folder constant to `base_ini_path.parent` so the CLI invocation writes output next to its input — it previously hard-coded the output at the Windows Documents path even when the user had moved their data off OneDrive via the new `USER_DATA_DIR` override.

## 0.9.3 
* [x] Investigated "Illegal mission 'need a death at asteroid base' has [BP] in title but no BP list in description" (headhunters `EliminateSpecific_Asteroid_Generic_M` contract, Pyro RegionA–D). Could not reproduce in current output: all four M-variant contracts in `headhunters_mercenary_fps.xml` correctly point their `Description` param at `@headhunters_EliminateSpecific_Asteroid_Generic_M_desc_001`, and that key emits a full `POTENTIAL BLUEPRINTS` block with the correct pool (`b81b328f…` → Deadrig Shotgun mag, Dust Devil set, Manticore Helmet, Ravager-212 twin, Ripper Sunblock). Audited all 231 `[BP]`-tagged titles against all 2,377 contract records: zero cases where a BP-tagged title's effective paired desc lacked the `POTENTIAL BLUEPRINTS` block. The prior report was likely resolved indirectly by 0.9.2's regional-pool split + `LOC_*` sentinel guards, or is a CIG-side contract-reference bug we haven't located; flagged for re-testing with a specific in-game screenshot if it recurs.
* [x] Declarative loc-string workarounds for CIG contract-reference bugs — our XML patches fix the DataForge cache the enhancement generator reads, but the game resolves Title/Description pointers directly from `Data.p4k` at runtime, so an XML edit alone doesn't change what the game displays when CIG's contract points at the wrong loc key. Extended the `patches/*.patch.json` schema with an optional `locstring_workarounds` list: each entry appends one loc key's value onto another (via `target` / `append_from` / `separator`), applied post-generation by the enhancement script. New `load_locstring_workarounds` + `apply_locstring_workarounds` + `LocstringWorkaround` in `src/utils/dataforge_patcher.py`; `generate_enhancements_ini.py` calls them against every output dict before `write_ini`; `main_window.py`'s enhancement worker passes `patches_dir` through. Idempotent (safe to re-run on already-merged content). Applied to Jorrit Dossier STARC-176797: `hockrowagency_facilitydelve.patch.json` now both rewrites the bugged P2M4 Description pointer *and* appends `Hockrow_FacilityDelve_P2M4_Repeat_desc` (flavor + P2M4 pool: Corbel Smolder, Geist Rogue/Whiteout) onto `Hockrow_FacilityDelve_P2M1_Repeat_desc` with a labeled divider — so in-game P2M4 players see the correct content despite the bugged lookup. P2M1 players see the P2M4 block as a labeled appendix. 7 new tests cover load/apply/idempotence/missing-key cases.
* [x] Known Issues section in `HELP.md` documenting CIG-side bugs that Smart Citizen works around, with links to the CIG Issue Council tickets and pointers to the patch files. Inaugural entry covers STARC-176797 (Jorrit Dossier).
* [x] Better formatting for Help section — Markdown bold (`**text**`) in the in-app help viewer wasn't rendering because `markdown_to_html()` did `line.replace("**", "<strong>")`, which emitted an opening tag at both ends (no closing), and because the bold transform only ran in the paragraph branch so list items and headers were skipped entirely. Extracted a shared `_convert_markdown_inline()` helper that stashes inline `` `code` `` spans behind placeholders (so ``**`` or ``_`` inside a backtick span stay literal), runs the existing link converter, then does bold (`**…**` / `__…__`) → `<strong>`, italic (`*…*`) → `<em>` with a `(?<!\*)…(?!\*)` guard so it can't steal halves of a `**` pair, and finally restores the code spans as `<code>` (HTML-escaped). Wired into the paragraph, unordered-list, ordered-list, and h1/h2/h3 branches of the line loop. Verified against a harness covering the six shapes HELP.md uses: bold alone, bold in a list item, bold wrapping an inline code span, `*` inside backticks staying un-italicized, real italic, and Markdown links.
* [x] Tooltips for buttons and other UI elements — ran a script that matches every `self.foo = Q{PushButton,ToolButton,CheckBox,ComboBox,Action,LineEdit,RadioButton,Spin,DoubleSpin,Slider}(...)` against an adjacent `self.foo.setToolTip(...)` call, identified 13 uncovered widgets across `main_window.py`, `config_tab.py`, `enhancements_tab.py`, and `log_tab.py`, and added concise action-oriented tooltips matching the existing style (Load Base File, Apply to Game, Restore Backup on the main toolbar; Category/Status/Hide Unmodified/Favorites Only/Clear Filters on the filter row; theme picker and game install path on the Config tab; favorite-prefix combo on the Enhancements tab; min-level combo and auto-scroll checkbox on the Log tab). Each tooltip explains *what the control does* and *what data it affects*, not just restating the label. Re-ran the audit script — 21/21 widgets now covered, 0 bare. Also bumped the app-wide tooltip wake-up delay from Qt's default 700ms to 800ms via a new `_SmartCitizenProxyStyle(QProxyStyle)` that wraps Fusion and overrides `SH_ToolTip_WakeUpDelay` — tooltips no longer pop while the cursor is just passing over a densely-labeled toolbar on its way somewhere else. The proxy also zeroes `SH_ToolTip_FallAsleepDelay` (Qt default 2000ms): without this, only the *first* tooltip in a cold session waited the full delay, then any subsequent tooltip shown within Qt's 2-second "awake" window popped instantly, so the longer cold delay was only felt once per app session. With fall-asleep collapsed, every tooltip cold-starts with the full 800ms delay. Re-apply safe: `apply_theme` detects the existing override by reading the style-hint value back out rather than via `isinstance` (PyQt slices `QProxyStyle` back to `QCommonStyle` when you call `app.style()`, so `isinstance` never sees the subclass).
* [x] Guided tutorial — interactive coach-mark tour (Option B). New `src/gui/coach_mark.py` module ships a `CoachMarkOverlay(QWidget)` that dims the main window with a semi-opaque black layer, cuts a rounded "spotlight" rect around a target widget via `QPainterPath.subtracted()`, and floats a themed callout frame (title, description, step counter, Back / Next / Skip) positioned on whichever side of the spotlight fits inside the window. Companion `TutorialTour(QObject)` sequences the steps, runs an optional per-step `pre_action` (used to switch to the Config or Enhancements tab so the target widget is laid out before we map its geometry), re-paints on parent window Resize/Move via an event filter so the spotlight tracks, and emits `finished(completed)` on Finish or Skip. Seven-step sequence assembled from **`assets/tutorial.json`** (user-editable copy: `id`, `title`, `description`, `preferred_side`, step order) zipped against `MainWindow._tutorial_step_wiring()` (per-id widget-target lambda + optional tab-switch `pre_action` — the bits that can't be serialized). `_build_tutorial_steps()` loads the JSON, skips entries whose `id` has no wiring or whose title/description is blank (logged at WARNING so typos surface in the Log Tab), and constructs a `CoachMarkStep` per survivor. Bundled default sequence: Welcome (no spotlight) → Extract from Data.p4k (Config tab) → Load Base File → Edit strings (whole table + filter-row copy) → Apply to Game → Generate Enhancements (Enhancements tab) → Help & feedback. Reorder by reordering the JSON array, remove a step by deleting its entry, add one by adding an `id` to the JSON plus a matching wiring entry in `_tutorial_step_wiring()`. First-run trigger hooks `MainWindow.showEvent` → `QTimer.singleShot(400, _start_tutorial)` if `AppSettings.get_tutorial_completed_version()` doesn't match the current app version (stored as a version string, not a bool, so a future release can re-trigger the tour if new steps land). Manual re-open via a new Tutorial button next to Help in the toolbar (shares the info-action `open` color role). Skip doesn't burn the completion flag — users who fat-finger Skip still see the tour on next launch; only Finish records the version. Exposed small glue pieces for targeting: `MainWindow.tabs` + `_strings_tab_index` / `_config_tab_index` so pre_actions can switch tabs; `ConfigTab._extract_btn` (was a local var). Smoke-tested end-to-end: booted app headless-style, drove four steps + a skip, verified tab switching, widget resolution, and `finished(False)` emission with the completion flag left intact.
* [x] Cache streamlining — DataForge cache now holds only the subtrees the enhancement generator actually reads, not the full unforge output. Inventoried the current cache (2.4 GB / 57,948 XML files) against every `records / ...` read-path in `scripts/generate_enhancements_ini.py`: 7 top-level subtrees are touched (`entities/scitem`, `entities/spaceships`, `contracts/contractgenerator` + `contracts/contracttemplates`, `crafting/blueprintrewards/blueprintmissionpools` + `crafting/blueprints/crafting`, `missionbroker/pu_missions`, `ammoparams/{vehicle,fps}`, `reputation/rewards/missionrewards_reputation`). Introduced `DATAFORGE_KEEP_SUBPATHS` in `src/utils/pak_extractor.py` and a `_copy_filtered_records()` helper that replaces the bulk `shutil.copytree(libs_dir / "libs", raw_dir / "libs")` in `extract_dataforge()` — instead of the full tree, unforge still writes everything to a temp dir (no filter flag exists upstream) but only the listed subpaths land in the persistent cache. Missing subpaths are `skipped`-counted rather than erroring (e.g. `entities/missions` / `entities/contracts` / `entities/jobterminal` come and go across 4.x patches; the generator already guards each read with `if dir.exists()`). Gains measured against the live cache: ~**52% fewer files** (57,948 → ~28,052), ~**42% smaller on disk** (2.4 GB → ~1.38 GB), ~**50% faster temp→cache copy** (per-file OneDrive/Defender/Indexer hooks dominate that phase), ~**2× faster `_robust_rmtree`** on clear-cache / re-extract with fewer transient WinError 5 retries. unp4k + unforge runtimes and the enhancement-generator rglob times are unchanged (generator was already scoped to these subpaths). Locked the maintenance contract with two new regression tests in `tests/test_pak_extraction.py`: `TestDataForgeKeepList::test_every_generator_read_path_is_covered` diffs a hardcoded list of the generator's leaf read-paths against `DATAFORGE_KEEP_SUBPATHS` (so a future generator change that reads an uncovered path fails at test time, not via silently-empty enhancements), plus a redundancy check that rejects entries already covered by an ancestor. Also three functional tests for `_copy_filtered_records` covering (1) only-kept-paths-survive, (2) missing-source-subpath is counted as skipped not failed, (3) unexpected unforge-output layout raises loudly.
* [x] Performance optimization — ran a survey of the Load Base File and Apply to Game hot paths, picked the three changes with real measured wall-clock savings:
  * **`extract_category()` in `src/models/string_model.py`**: the function was rebuilding a ~140-element `mission_prefixes` set, two sub-lists of FPS-weapon and armor tokens, and an 8-element component-code list on every call, compiling the ship-weapon-size regex fresh each time, and being called twice per loaded key (once during `ini_parser.load_sources_from_settings` filtering, once during StringEntry assignment). Hoisted all the literals to module scope, compiled `_SHIP_WEAPON_SIZE_RE` once, replaced the `any(key_lower.startswith(p) for p in prefixes)` loop with `key_lower.startswith(_MISSION_PREFIXES_TUPLE)` (CPython's C-level tuple startswith short-circuits on first match), and wrapped the impl in `@lru_cache(maxsize=None)` so the second call per key is a pure dict hit. Measured on the live 87,626-key base.ini: ~98 ms cold (both passes combined), ~7.5 ms warm — the pre-change version paid ~98 ms twice plus set/list rebuild overhead per call. Regression-tested against 21 real-world key shapes covering every branch.
  * **`_get_canonical_key()` in `src/merger/ini_merger.py`**: called ~87k times per `sync_key_variants()` pass, doing 8 sequential `.replace()` calls on every key when ~98% of keys contain no component code at all. Added a short-circuit — lower + underscore-strip, then check `any(c in stripped for c in _COMPONENT_CODES)`; if none present, return the stripped form directly (semantically identical to the full algorithm when the replace loop is a no-op). Wrapped the function in `@lru_cache(maxsize=None)` so Apply re-uses Load's work. Checked the short-circuit fires only when safe by running the new implementation against the original byte-for-byte reference over all 87,626 real keys — **0 mismatches**. Wall-clock: cold run roughly identical (fast-path savings cancelled by the cache-miss bookkeeping), **warm-cache run ~92% faster (~100 ms saved per subsequent merge)** — this lands as a direct Apply-to-Game speedup since Apply calls `merge_sources_by_hierarchy` → `sync_key_variants` again after Load already populated the cache.
  * **Validation double-parse in `MainWindow._validate_applied_file`**: was re-reading the ~87k-line base.ini from disk on every Apply to build the "stock keys" comparison set, even though `apply_to_game` had just parsed it seconds earlier via `load_sources_from_settings()` and held it in `sources_dict["global"]`. Added a `stock_keys: set[str] | None` parameter; `apply_to_game` now threads `set(sources_dict["global"].keys())` through, falling back to on-disk parse only when the global source isn't in memory (e.g. misconfigured cache). Saves one 87k-line parse per Apply — the written-file parse stays as independent merger-bug verification.
* [x] Per-channel Star Citizen install support — Smart Citizen now handles the four SC channels (LIVE, PTU, EPTU, TECH-PREVIEW) as first-class, switchable configurations instead of assuming LIVE. New `AppSettings.SC_INSTALL_ROOT` holds the Star Citizen parent directory (the folder containing `LIVE/`, `PTU/`, etc.) and `AppSettings.ACTIVE_CHANNEL` picks which channel the app reads and writes against. Every channel-scoped path helper — `get_cache_dir()`, `get_user_ini_path()`, `get_backups_dir()`, `get_dataforge_cache_dir()`, `get_p4k_path()`, plus a new `get_global_ini_path()` — now nests under `Documents\Smart Citizen\{active_channel}\`, so each channel has its own isolated cache, overrides, backups, DataForge extraction, and enhancement INIs. Old scattered "if game_path.name == 'LIVE': …" branches in `apply_to_game`, `clear_localization`, `open_localization_dir`, `restore_backup`, and `user_cfg.ensure_user_cfg_language` were replaced with calls to `get_global_ini_path()` / `get_game_install_path()` — they now resolve correctly for whichever channel is active. One-shot migrator `AppSettings.migrate_game_path_to_channel_layout()` (wired into `main.main()` after the other 0.9.x migrators, marker-gated for idempotence) handles both sides for existing users: (1) registry side — if `GAME_INSTALL_PATH` ends in a recognized channel suffix, split off the channel and set `SC_INSTALL_ROOT` + `ACTIVE_CHANNEL` accordingly, else treat it as the root and default to LIVE; (2) filesystem side — if `Documents\Smart Citizen\` still has flat `base.ini` / `cache\` / `backups\` / `user.ini` entries and no populated channel subfolder exists yet, move them into a LIVE subfolder. The filesystem migration tolerates empty channel shells (auto-created by an earlier path-helper `mkdir(exist_ok=True)`) by merging flat entries into them rather than bailing. Config tab gets a new **Channel** combo next to the install-path input: shows all four channels, disables entries whose `{root}\{channel}\Data.p4k` doesn't exist (tooltip: "PTU isn't installed — no Data.p4k at …"), and surfaces a `⚠` hint label when the stored active channel isn't currently available. Selecting a channel persists via `AppSettings.set_active_channel()` and emits a new `channel_changed(str)` signal that `MainWindow._on_channel_changed` picks up to trigger `perform_merge_and_reload()` — the table reloads immediately against the new channel's data without a restart. Status bar gains a permanent right-side **Channel: LIVE** indicator (via `addPermanentWidget`) and the existing SC-version display in `_update_status_bar()` now carries the channel suffix (e.g. `SC v4.7.176-PTU`, or `SC PTU (manifest missing)` when a channel is selected but not installed). 26 new tests in `tests/test_channel_layout.py` cover the channel constants, active-channel getter/setter round-trip with fallback on corrupt values, every channel-scoped path helper's nesting behavior, `get_available_channels()` auto-detection (present/absent/all-missing), and every migrator branch: LIVE/PTU suffix stripping, no-suffix defaulting to LIVE, flat→LIVE filesystem move, merging-into-empty-LIVE-shell, skipping when a populated channel dir exists, and marker-based idempotence.
* [ ] Stability & bugfixes
* [ ] End-to-end testing & version release
* [x] Consolidated Feedback, Bug Reports, and Feature Request Voting into a single Discord channel (`https://discord.com/channels/1438175448420057323/1472394204347895890`). Platform evaluation first: Canny.io's free tier caps at 25 tracked users (too tight for a free publicly-distributed Windows app) and its API requires Pro+ (~$80/mo), GitHub Issues/Discussions works but fragments the community between Discord (where users already are) and GitHub and requires a GitHub account to vote, in-app OAuth submit/vote is a friction spike disproportionate to the feature's value. Settled on a single Discord channel because voting is handled natively via Discord reactions/polls, users are already in the server for support, and the maintenance cost is zero. Surfaced in three places with matching copy: the footer link (`self.feedback_label` in `main_window.py`, renamed from "Feedback" to "Feedback, Bugs, & Feature Voting", tooltip expanded to mention voting), HELP.md (section heading renamed, bullet now calls out "vote on upcoming features" and notes prioritization is driven by reactions/votes), and ABOUT.md Community & Support block (bullet renamed to match). Server-invite fallback link (`https://discord.gg/BNzRegKZ7k`) preserved in HELP/ABOUT for users not yet in the Osiris DevWorks Discord.


## 1.0.0 Production Release

* [ ] Human read-through of all documentation for accuracy