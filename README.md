# Smart Citizen Hardened

> A portable, security-focused Star Citizen localization enhancer.
> It adds clearer mission, blueprint, item, ship, and crafting information to
> the game without an installer, self-updater, or background service.

**[Download the latest hardened portable release](../../releases/latest)**

## Major Highlights

- **Hardened security design** — no application self-updater, no startup
  synchronization, no telemetry or Discord test reporting, local-only imports,
  hash checks for packaged extraction tools, and a package-integrity check.
- **Portable, not installed** — unzip it where you control it and run it.
  Settings, cache, logs, and backups stay beside the application; there is no
  installer or background service.
- **Blueprint intelligence** — mission text can show blueprint rewards,
  potential blueprints, reputation, and useful contract details. The Blueprint
  Tracker can scan local game logs to identify blueprints already earned.
- **Crafting Planner** — reads recipes and material quantities from your
  locally extracted game data. Search recipes and build a combined shopping
  list without changing `Data.p4k` or game files.
- **Loot Tags / shop identification** — optional `[Shop]` and `[Unlisted]`
  labels help evaluate items while looting. They use exact Finder community
  catalog matches, never guesses; manual `[Keep]` and `[Limited]` tags remain
  available too.
- **One-click first use with control later** — Apply Enhancements handles the
  normal initial flow; Advanced mode exposes previews, backups, restore, and
  detailed configuration whenever you want it.

## Start Here

1. Download `SmartCitizen-Portable-...zip` from **Releases**.
2. Extract the ZIP to a folder you control, such as `Documents\SmartCitizen`.
3. Run `SmartCitizen-Portable-...exe`.
4. On the first screen, click **Apply Enhancements** and confirm.

**Important Note - windows defender may try and block the app from running. If it does, in the popup click more info, then click Run Anyways** (same as the main branch, this is due to smaller developer teams not having Microsoft reputation). Hash is provided for safety and verification.

**Windows SmartScreen note:** Windows may initially show an “unrecognized app”
warning because this community build is not code-signed and has not built up
Microsoft reputation. Only continue after downloading from this repository’s
**Releases** page and verifying the published SHA-256 checksum. If it matches,
select **More info**, then **Run anyway**.

That is all most players need to do. The app reads game data from your local
Star Citizen installation, imports blueprint ownership from local game logs
when available, creates backups before it changes anything, and applies the
enhancements to the selected game channel.

## Featured Tools

### Crafting Planner

After the first Apply completes, choose **Switch to Advanced** and open
**Crafting Planner**. Select **Load Recipes from Local Game Data**, then
search for the item you want to craft. The planner shows the materials and
quantities authored in your current Star Citizen game data, so you can make a
shopping list before using an in-game fabricator. It is read-only: it never
changes `Data.p4k` or game files.

To plan several crafts at once, Ctrl-select multiple recipes. The planner
combines matching materials into one total shopping list, which you can copy
to the clipboard.

### Loot Tags

After loading your local game data, **Switch to Advanced** and open **Loot
Tags**. This tab labels actual in-game item names with `[Shop]`, `[Keep]`,
`[Limited]`, or `[Unlisted]` so they are easier to judge while looting. The
game files do not reliably say where an item is sold or how rare it is, so this
fork never guesses. Mark items you have reviewed, then Apply Enhancements to
write the labels to your local localization mod.

Use **Export Catalog** to save your reviewed list or **Import Catalog** to
explicitly replace it with a catalog file you trust. There are no automatic
catalog downloads or background update checks. **Refresh Finder Shop Data** is
an optional, confirmed action: it makes one HTTPS request to the displayed
Finder endpoint, rejects redirects, limits and validates the response, and
keeps your manual tags. `[Unlisted]` means an exact
item-name match was marked not sold by its reviewed catalog source; it does
not mean rare or loot-only.

This build includes a one-time Finder GetSearch starter snapshot supplied by a
user on 2026-08-09. Exact matched item names marked sold receive `[Shop]`;
exact matched names marked not sold receive `[Unlisted]`. Names absent from the
snapshot remain untagged rather than being guessed as rare or loot-only.

Loot Tags are grouped so the useful loot signals stay readable. Weapons,
armor, and other gear are enabled by default; clothing/accessories, food/drink,
and medical supplies start disabled. The catalog still retains those records,
so enabling a group later does not require another download.

## Supporting Features

- Mission, ship, FPS weapon, component, commodity, journal, and medical-text
  enhancements generated from your installed game data.
- Searchable String Editor with ship-first loading, live preview, direct text
  editing, and configurable component/weapon name tags.
- Blueprint ownership import/export, local log scanning, and in-game `[Owned]`
  mission-list markers.
- Per-channel LIVE / PTU / EPTU / HOTFIX / TECH-PREVIEW settings, cache, and
  backups, plus multi-language support.
- Automatic backups before Apply, Preview Apply, Restore, and **Emergency
  Remove From Game** for a clear rollback path.
- Explicit security controls: Offline Security Mode, local catalog
  import/export, and the separately confirmed Finder refresh option.

## Why This Hardened Fork

| Feature | What it means for you |
| --- | --- |
| **Portable** | No installer and no Windows Registry requirement. Settings, cache, backups, and logs remain in the application's local `data` folder. |
| **No application auto-updates** | The app never checks for, downloads, or installs its own updates. You choose when to download a new release. |
| **No telemetry or Discord reporting** | This fork removes the automatic reporting and test-submission features. |
| **Local game data** | English game strings, missions, blueprints, and item data come from your installed `Data.p4k`, not a community mirror. |
| **Integrity checks** | The bundled extraction tools are hash-checked before use, and the portable package verifies its packaged files at startup. |
| **Recovery built in** | Apply creates backups. **More → Emergency Remove From Game** restores the files from before the last Apply. |
| **Optional Offline Security Mode** | You can block all app network access. The core English workflow does not need network access. |

## What It Does to Star Citizen

Smart Citizen is a **localization mod**, not an injector or game launcher. It
adds or improves text the game already displays: mission reward details,
blueprint indicators, reputation information, component and ship statistics,
crafting references, and more. It changes only localization-related files for
the selected Star Citizen channel and keeps a rollback snapshot first.

Useful highlights include:

- Mission indicators for blueprints, potential blueprints, and reputation.
- Blueprint Tracker with local log scanning for blueprints you have already earned.
- Local Loot Tags for actual item names: `[Shop]`, `[Keep]`, `[Limited]`, and
  cautious `[Unlisted]` labels. Tags are user-reviewed, exportable/importable
  JSON; the app never infers availability or downloads a catalog automatically.
  An optional, confirmed Finder refresh is available for its reviewed shop
  endpoint and preserves manual tags.
- Crafting Planner: search local recipes, view required materials and quantities,
  and combine several recipes into a copyable shopping list.
- Searchable item, ship, weapon, and crafting information.
- Configurable name tags for components, missiles, and ship weapons.
- One-click first-run setup, plus Advanced mode for detailed control.

## Moving from another Smart Citizen build

Choose **Import Previous Settings** on the start screen and select an exported
settings ZIP. Nothing is imported automatically and your existing settings are
not overwritten without your action.

---

**This is an independent community fork, not an official Osiris DevWorks
release.** Original authorship, contributors, license, and acknowledgements
remain credited below. See [CHANGELOG.md](CHANGELOG.md) for fork changes and
[SECURITY_HARDENING.md](SECURITY_HARDENING.md) for the detailed security policy.

## Original Smart Citizen Features

- **Multi-Channel Star Citizen Support**: LIVE / PTU / EPTU / HOTFIX / TECH-PREVIEW each get their own isolated workspace — independent `user.ini`, cache, backups, DataForge extraction, and enhancement INIs. Switch channels from the Config tab without restarting.
- **Multi-Language Support**: Switch the app and game strings between English, French, Spanish, Brazilian Portuguese, Japanese, Chinese, Italian, and German from the Config tab. Non-English languages layer a community-translated `global.ini` (from [Dymerz/StarCitizen-Localization](https://github.com/Dymerz/StarCitizen-Localization), [42Kit](https://ini.42kit.com/), [stdblue/StarCitizenJapaneseResources](https://github.com/stdblue/StarCitizenJapaneseResources), [Thord82/Star_citizen_ES](https://github.com/Thord82/Star_citizen_ES), and [rjcncpt/StarCitizen-Deutsch-INI](https://github.com/rjcncpt/StarCitizen-Deutsch-INI)) over the English base, with English fallback for anything untranslated.
- **Simple & Advanced Mode**: A two-button Simple screen (one applies enhancements with your saved settings, the other switches to Advanced), or the full Advanced UI (table, filters, Enhancements, Config) for hand-editing. Pick your default at install; switch anytime in-app.
- **Multi-Source Merge System**: Sources (stock base, language overlay, enhancements, user) merge in a drag-and-drop priority order, with user overrides always applied last so your edits never get overwritten.
- **Sourced from Data.p4k**: All stock localization and DataForge entity data is extracted directly from your installed game — no community mirrors, no version drift, no network required after install.
- **Inline Editing & Live Preview**: Double-click any cell in the *Custom Value* column to edit. A preview pane next to the toolbar renders the selected string with the game's loc-tokens (line breaks, EM3/EM4 emphasis, mission placeholders) translated to styled HTML so you see roughly how it will appear in-game.
- **Persistent Edits**: Your customizations are saved to `user.ini` per channel and automatically re-applied across game updates.
- **Auto-Generated Enhancements**: Stat overlays for ships, ship components, ship weapons, FPS weapons, missions (with `[BP]`/`[BP?]` blueprint reward tags + structured detail blocks), journal entries, commodity crafting cross-references, and medical consumable effects — all togglable per category in the Enhancements tab. Stat blocks can sit above or below the description. Mission XP names the reputation track it feeds, Battaglia scan/mine titles carry `[RS ####]` resource-signature tags, and the Mining Compendium journal lists each ore's base RS.
- **Tag Builder & Mission Titles**: Customize the bracketed name tags on components, missiles, ship weapons, and commodities, and lead hauling mission titles with their route (e.g. `Area18 > Lorville`) — configurable placement, arrow, separator, and location detail, plus optional stock-title shortening, with a live preview.
- **Blueprint Tracker**: A dedicated tab for marking the crafting blueprints you already own. Shuttle items between Available and Owned, narrow the list with search and Mission / Type / Class / Size / Grade filters, and owned items get a blue `[Owned]` tag in mission blueprint lists. **Scan Logs for Owned Blueprints** reads your Star Citizen log files to populate ownership automatically, importing only what's new since the last scan; an **Also scan LIVE/HOTFIX** toggle picks up blueprints earned on the sibling channel, and a **Rescan all logs** checkbox forces a full re-read when something looks off. **Export / Import Owned Blueprints** moves your owned list between PCs (JSON or CSV; imports only ever add, and scmdb.net exports work too).
- **Declarative CIG Data-Bug Patches**: A patch system applies fixes to known DataForge bugs at extraction time so the in-game text reads correctly without waiting on CIG.
- **Search & Filter**: Free-text search, category filter (Ships, Ship Items, Missions, Gear, Commodities, Journal, Other), modified/unmodified status, per-column filter rows under every header, and a **Ship/Vehicle Names Only** toggle that narrows the table to the ship name rows favoriting applies to.
- **Ship Favorites**: Star a ship to prepend a configurable prefix (default `*`) so your favorites sort to the top of the in-game ASOP terminal.
- **Apply Enhancements**: Writes the merged result to your `global.ini`, takes a timestamped backup first, and validates the output against the stock key set — auto-rolls back on any mismatch.
- **Backup & Restore**: Up to 5 automatic backups per channel, oldest auto-pruned. One-click restore from any of them.
- **Settings Backup**: Export your preferences, tag configurations, and every channel's string overrides to one small zip; import it on a new PC (or a fresh portable unzip) and Smart Citizen restores everything, snapshotting your current files first so the import is reversible.
- **Clear Localization**: Revert your game to vanilla text without losing your saved overrides.
- **Guided Tutorial**: A coach-mark tour walks new users through the workflow on first launch of each version. Replayable any time from the Tutorial button.
- **In-App FAQ**: A FAQ tab answers the common questions (what files get touched, ban risk, the Windows unrecognized-app warning, undoing changes) without leaving the app.
- **In-App Log Viewer**: Real-time application log with level filter, auto-scroll, and an Export button for bug reports.
- **Hardened portable distribution**: Application update checks, downloads,
  installer execution, startup synchronization, and Discord test-report
  submission are removed. The portable build keeps its settings alongside the
  application rather than using an installer.
- **Themes**: Four built-in themes — SCLE (default deep-navy mobiGlas), Light, Dark, and ODW (Osiris DevWorks signature).

## Screenshots

<table>
  <tr>
    <td width="50%"><img src="assets/screenshots/ss.png" alt="Smart Citizen main window"/><br/><em>Smart Citizen — main window</em></td>
    <td width="50%"><img src="assets/screenshots/asop.png" alt="ASOP terminal with ship favorites"/><br/><em>ASOP terminal — favorites prefixed to top</em></td>
  </tr>
  <tr>
    <td width="50%"><img src="assets/screenshots/item_stats.png" alt="Item and ship stat overlays"/><br/><em>Item &amp; ship stat overlays</em></td>
    <td width="50%"><img src="assets/screenshots/mission_deets.png" alt="Mission details with blueprint reward tags"/><br/><em>Mission details with reward tags</em></td>
  </tr>
  <tr>
    <td width="50%"><img src="assets/screenshots/bps.png" alt="Blueprint reward list"/><br/><em>Blueprint reward list</em></td>
    <td width="50%"><img src="assets/screenshots/blue_prints.png" alt="Blueprint enhancements"/><br/><em>Blueprint enhancements</em></td>
  </tr>
  <tr>
    <td width="50%"><img src="assets/screenshots/journal.png" alt="Journal entries"/><br/><em>Journal entries</em></td>
    <td width="50%"><img src="assets/screenshots/radar.png" alt="Mission contract radar"/><br/><em>Mission contract radar</em></td>
  </tr>
  <tr>
    <td width="50%"><img src="assets/screenshots/LootTags.jpg" alt="Loot Tags catalog and category controls"/><br/><em>Loot Tags and shop identification</em></td>
    <td width="50%"><img src="assets/screenshots/CraftingPlanner.jpg" alt="Crafting Planner recipe and materials view"/><br/><em>Crafting Planner from local game data</em></td>
  </tr>
  <tr>
    <td width="50%"><img src="assets/screenshots/NewTag.jpg" alt="New in-game item tag"/><br/><em>New item tags in game</em></td>
    <td width="50%"></td>
  </tr>
</table>

## Advanced and Upstream Reference

Most hardened-fork users can stop after **Start Here** above. The remaining
sections retain detailed application and upstream reference material.

### Manual hardened-fork setup

Download the portable ZIP from this fork’s Releases page, extract it to a
folder you control, and run `SmartCitizen-Portable-v{VERSION}.exe`. No
installer is used. On first run, choose **Apply Enhancements** and confirm the
change; the app prepares required data from your local `Data.p4k`.

If you are moving from another Smart Citizen installation, choose **Import
Previous Settings** and select an exported settings ZIP. Existing settings are
never imported automatically.

### Do not use: upstream installer notes

> These installer instructions are retained for upstream-reference purposes.
> They do not apply to this portable hardened fork.
Grab the latest release here: [Smart Citizen Releases](https://github.com/Osiris-DevWorks/smart-citizen/releases)

Download the **`SmartCitizen-{VERSION}-Setup.exe`** installer and run it. The app auto-detects your Star Citizen installation.

> [!IMPORTANT]
> **Windows Smart App Control may block the installer.** Smart Citizen is not yet code-signed, and Windows 11's Smart App Control (SAC) silently blocks unsigned installers — right-click → Properties → Unblock does **not** help with SAC. To install:
>
> 1. Open **Settings → Privacy & security → Windows Security → App & browser control**.
> 2. Click **Smart App Control settings** and set Smart App Control to **Off**.
> 3. Run `SmartCitizen-{VERSION}-Setup.exe` and finish installation.
> 4. After install, you can return to that screen and turn Smart App Control back on if you'd like.
>
> Note: on stock Windows 11, turning SAC off can be a one-way change — Microsoft does not always permit re-enabling without resetting Windows. Weigh that before disabling. A code-signing certificate is the only way to remove this friction permanently; Smart Citizen is a free side project, so signing will only happen if community donations cover the recurring cost.

### On Linux

Smart Citizen runs on Linux through the same Wine prefix as Star Citizen — see **[LINUX.md](docs/LINUX.md)** for the full guide (download the portable build, then point a launch script at the Wine runner your game uses).

### For Developers

See **[docs/CONTRIBUTOR_GUIDE.md](docs/CONTRIBUTOR_GUIDE.md)** for local setup (prerequisites, clone, install, run).

## Usage

### First Run
1. The app creates `<data folder>\<channel>\` for user data — cache, backups, `user.ini`. The default data folder is `Documents\Smart Citizen`, and it can be changed in the Config tab.
2. Open the Config tab and click **Extract from Data.p4k** to unpack stock localization plus DataForge entity data from your installed game. When extraction finishes, sources merge by hierarchy and the strings load into the table automatically.
3. The guided tutorial auto-runs the first time you launch a new version, walking you through the rest.

### Standard Workflow
1. **Find & Edit**:
   - Use the **Search** box to find strings, the **Category** filter to narrow by domain (Ships, Ship Items, Missions, Gear, Commodities, Journal, Other), and per-column filter boxes for fine-grained narrowing.
   - Double-click the **Custom Value** column to edit. The preview pane shows the rendered result.
2. **Apply Changes**: Click **Apply Enhancements**. Your edits are persisted to `user.ini`, the merged file is written to your game's `global.ini`, and a timestamped backup is created automatically.
3. **Restore** (if needed): Click **Restore Backup** to revert to a previous version.

### After Star Citizen Updates
1. Re-run **Extract from Data.p4k** in the Config tab to pull fresh stock strings and DataForge entity data from the patched game. The table reloads automatically and your customizations re-apply on top.
2. Click **Apply Enhancements** to push the updated merge into the new build.

## Configuration

All settings are stored in Windows Registry under:
- **Organization**: Osiris DevWorks
- **Application**: Smart Citizen

The Config tab lets you set:
- **Star Citizen install path** (the SC root folder containing `LIVE/`, `PTU/`, etc. — auto-detected at install time)
- **Active channel** (LIVE / PTU / EPTU / HOTFIX / TECH-PREVIEW)
- **Language** (English, French, Spanish, Brazilian Portuguese, Japanese, Chinese, Italian, German; switches the app UI and the game strings)
- **Smart Citizen data folder** (where `user.ini`, cache, DataForge extraction, enhancement INIs, and backups live)
- **Theme**
- **Data sources**: enable/disable, drag-drop merge priority
- **Import INI**: fold an external `.ini` into your overrides
- **Reset / Restore user.ini**: wipe your edits for the channel (with an auto-backup), or roll them back to an earlier rotating snapshot

The Enhancements tab lets you toggle each enhancement category (ship stats, weapon stats, mission tags, etc.), configure the ship favorite prefix, customize the **Tag Builder** for components, missiles, ship weapons, and commodities (plus **Mission Titles** route tags), mark owned crafting blueprints, and adjust **Mission Labels** (section headers, XP label, emphasis tag).

### Data Storage

All per-user data lives under `<data folder>\<channel>\`, where `<data folder>` defaults to `Documents\Smart Citizen` and `<channel>` is one of `LIVE`, `PTU`, `EPTU`, `HOTFIX`, `TECH-PREVIEW`:

- **Your edits**: `user.ini`
- **Cached sources & extracted DataForge**: `cache\` (`base.ini`, `cache\dataforge\`, and the generated `*_enhancements.ini` files)
- **Backups**: `backups\` (max 5, oldest auto-deleted)

Each channel is fully isolated — you can run a different customization set on PTU than on LIVE without one bleeding into the other.

## Building & Release

### Development Run
```bash
python src/main.py
```

### Create Executable
```bash
python scripts/build/build_exe.py
```
This creates a PyInstaller onedir at `dist/SmartCitizen-v{VERSION}\` containing `SmartCitizen-v{VERSION}.exe`. VERSION comes from `VERSION.TXT`.

### Create Installer (Windows)
Requires [Inno Setup 6](https://jrsoftware.org/isdl.php):
```bash
powershell -NoProfile -Command "& 'C:\Users\<you>\AppData\Local\Programs\Inno Setup 6\ISCC.exe' installer.iss"
```

Outputs:
- `dist/SmartCitizen-v{VERSION}\` — Standalone executable (onedir, distributed via the installer)
- `dist/SmartCitizen-{VERSION}-Setup.exe` — Installer (this is what users download)

The installer preserves user data — `user.ini` and `backups/` survive both upgrades and uninstalls; only the regeneratable cache is removed on uninstall.

## Project Structure

```
src/
├── main.py                       # Application entry point
├── gui/                          # PyQt6 widgets and dialogs
├── models/                       # StringEntry dataclass, category extraction
├── parser/                       # INI parsing + source loading
├── merger/                       # Source merge engine
└── utils/                        # Settings, paths, P4K extraction, patcher,
                                  # version, updater, app_updater, progress sink

scripts/
├── generate_enhancements_ini.py  # DataForge XML → enhancement INI files
├── extract_components.py         # base.ini delta extraction
├── gen_commodity_crafting.py     # Commodity crafting cross-reference INI
├── diff_*.py                     # Diagnostic / research tools
└── build/                        # PyInstaller build script + helpers

patches/                          # Declarative DataForge patches (JSON)
tests/                            # pytest suite
assets/                           # Bundled resources (unp4k, fonts, icon, tutorial)
```

For a deeper guide to architecture and conventions, see `CLAUDE.md` at the repo root.

## Game Installation Path

After applying localization, the relevant path inside your Star Citizen install looks like:
```
StarCitizen/
└── LIVE/                    (or PTU/, EPTU/, HOTFIX/, TECH-PREVIEW/)
    ├── user.cfg
    └── data/
        └── Localization/
            └── english/     (or the selected language's folder,
                └── global.ini   e.g. french_(france)/)
```

## Legal

> [!IMPORTANT]
> **Made by the Community** — This is an unofficial Star Citizen fan project, not affiliated with the Cloud Imperium group of companies. All content in this repository not authored by its host or users is the property of its respective owners.

- The ability to customize your localization using extracted `global.ini` files is **authorized by CIG** to support community translations until officially integrated.
  - *[Star Citizen: Community Localization Update](https://robertsspaceindustries.com/spectrum/community/SC/forum/1/thread/star-citizen-community-localization-update) 2023-10-11*
- Use at your own discretion as a third-party contribution.
- [RSI Terms of Service](https://robertsspaceindustries.com/en/tos)
- [Translation & Fan Localization Statement](https://support.robertsspaceindustries.com/hc/en-us/articles/360006895793-Star-Citizen-Fankit-and-Fandom-FAQ#h_01JNKSPM7MRSB1WNBW6FGD2H98)

## Contributors

Thanks to those who've contributed code to Smart Citizen:

- [**Stealrull**](https://github.com/Stealrull)
- [**Ishikudeska**](https://github.com/Ishikudeska)
- **jonigirl**
- [**Coerwyn**](https://github.com/Coerwyn)
- [**denis-coach**](https://github.com/denis-coach) (also [h0use](https://github.com/h0useRus))
- [**scubamount**](https://github.com/scubamount)
- **hkstrongside**
- [**odw-okano**](https://github.com/odw-okano)

## Acknowledgments

- **Boogie Man, Perseuscz, Flat Earth, Lord Valium, Zero, Apolleon Phoibos, Epiq, Narull, XaileiShiv, Mindbulletz** — testers who helped shape Smart Citizen with their feedback
- **Akwa** — French interface translation
- **Nxzzin** — Brazilian Portuguese interface translation
- [**Thord82**](https://github.com/Thord82) — Spanish interface translation, plus the [Spanish `global.ini` source](https://github.com/Thord82/Star_citizen_ES) that powers the Spanish game strings
- [**stdblue/StarCitizenJapaneseResources**](https://github.com/stdblue/StarCitizenJapaneseResources) — the Japanese `global.ini` source that powers the Japanese game strings; the Japanese interface translation is AI-generated pending a human reviewer
- [**42Kit**](https://ini.42kit.com/) — the [Chinese `global.ini` source](https://ini.42kit.com/full/global.ini) that powers the Chinese game strings; the Chinese interface translation is AI-generated pending a human reviewer
- The Italian interface translation is AI-generated pending a human reviewer; the Italian `global.ini` source is the same [Dymerz/StarCitizen-Localization](https://github.com/Dymerz/StarCitizen-Localization) repo credited below
- [**rjcncpt**](https://github.com/rjcncpt) — the [German `global.ini` source](https://github.com/rjcncpt/StarCitizen-Deutsch-INI) that powers the German game strings; the German interface translation is AI-generated pending a human reviewer
- [**Osiris-DevWorks/odw-fast-unp4k**](https://github.com/Osiris-DevWorks/odw-fast-unp4k) — Bundled `unp4k.exe` / `unforge.exe` used to unpack `Data.p4k` and convert DataForge to XML; our parallelized fork of the original [dolkensp/unp4k](https://github.com/dolkensp/unp4k)
- [**Dymerz/StarCitizen-Localization**](https://github.com/Dymerz/StarCitizen-Localization) — Community-maintained `global.ini` translations that power the non-English language options
- [**ExoAE**](https://github.com/ExoAE/ScCompLangPack) — Original ScCompLangPack concept and merge logic that inspired Smart Citizen's foundation
- [**MrKraken**](https://github.com/MrKraken/StarStrings) — ASOP terminal enhancements, workflow improvements, and mission contract localization work
- The **Star Citizen community** — for endless feedback, testing, and ideas

### Supporters

Thanks to those who've supported the project financially — your contributions help keep Smart Citizen free for everyone:

- **Dimwit the Wise**

## License

Smart Citizen is licensed under the **Apache License, Version 2.0** — see [LICENSE](LICENSE) for the full text and [NOTICE](NOTICE) for attribution of bundled third-party software (`unp4k` / `unforge`) and the Star Citizen / CIG trademark notice.

## Support & Community

### Feedback, Bugs & Feature Voting
All bug reports, feature requests, and prioritization happen in the dedicated `#smart-citizen` channel on the Osiris DevWorks Discord. Reactions and polls drive what lands next.

- **[Discord Server Invite](https://discord.gg/BNzRegKZ7k)** — join the server first, then jump into the [Smart Citizen feedback channel](https://discord.com/channels/1438175448420057323/1472394204347895890).
- When reporting a bug, attach the log (Log tab → **Export**) and mention the SC version you're on.

### Video Guides

- **[Star Citizen Hides Important Mission Info – This Tool Shows It In-Game & More!](https://www.youtube.com/watch?v=Xo1t404gsgs)** by **Karolinger** — a community overview of Smart Citizen's features.

### Support the Project

Smart Citizen is a free, open-source project. If you find it useful and want to support development:

- [PayPal Donation](https://paypal.me/RighteousKill)
- [Venmo Donation](https://venmo.com/u/Amr-Abouelleil)

---

**Fly safe, Citizen!** o7
