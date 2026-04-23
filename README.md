# Smart Citizen

*Smarter Strings for Star Citizen*

A PyQt6 GUI application for managing Star Citizen localization string customizations.

> [!NOTE]
> This project is forked from [ExoAE's ScCompLangPack](https://github.com/ExoAE/ScCompLangPack) and built upon the merge concepts from [MrKraken's ASOP terminal enhancements](https://www.youtube.com/@MrKraken). In this application, we've created an intuitive desktop GUI to make localization customization more user-friendly.

## Features

- **Multi-Source Data System**: Configure multiple data sources (Global, Contracts, Components, Ships, Commodities, Gear) with drag-and-drop merge hierarchy
- **Auto-Update**: Automatically checks GitHub for the latest localization files from community repos
- **Load & Edit**: Load and merge sources, then customize strings in an intuitive table view
- **Persistent Edits**: Your customizations are saved to `overrides.ini` and automatically re-applied
- **Seamless Migration**: When Star Citizen updates, your edits are automatically re-applied to new base files
- **Search & Filter**: Filter by search text, category (Ships, Ship Items, Gear, Commodities, Missions, Other), or modification status
- **Ship Favorites**: Mark ships as favorites with a configurable prefix; filter to show favorites only
- **Stats Enhancements**: Auto-generated ship, component, and weapon stat descriptions via DataForge extraction
- **P4K Extraction**: Extract and convert game data from Data.p4k for stats generation
- **Apply to Game**: Writes merged localization file directly to your installation
- **Backup & Restore**: Automatic timestamped backups with easy one-click restore (max 5)
- **Clear Localization**: Revert to vanilla game text while preserving your saved edits
- **Settings Persistence**: All paths and preferences saved in Windows Registry

## Quick Start

### Using the Release
Grab the latest release here: [Smart Citizen Releases](https://github.com/Osiris-DevWorks/smart-citizen/releases)

Just download the **-Setup.exe** installer and run it. The app will auto-detect your Star Citizen installation.

### For Developers

**Prerequisites**:
- Python 3.9+ (recommended 3.10+)
- Windows 10/11 (application uses Windows Registry for settings)

**Installation**:

1. **Clone the repository**
   ```bash
   git clone https://github.com/Osiris-DevWorks/smart-citizen.git
   cd smart-citizen
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python src/main.py
   ```

## Usage

### First Run
1. The app creates `Documents\SC Localization Editor\` for user data (cache, backups, overrides)
2. Pre-configured sources (Global, Contracts from MrKraken; Ships, Commodities, Gear from Osiris-DevWorks) are auto-downloaded
3. Sources are merged in hierarchy order and displayed in the table

### Standard Workflow
1. **Configure Sources** (optional): Use the Config tab to add/edit sources and drag-drop to set merge priority
2. **Find & Customize**:
   - Use the **Search** box to find strings (searches key and value)
   - Use **Category** filter (Ships, Ship Items, Gear, Commodities, Missions, Other)
   - Double-click the **Custom Value** column to edit
3. **Apply Changes**: Click **"Apply to Game"**
   - Your customizations are saved to `overrides.ini`
   - The game file is updated with all your edits merged in
   - A timestamped backup is created automatically
4. **Restore** (if needed): Click **"Restore Backup"** to revert to a previous version

### After Star Citizen Updates
1. Obtain the new base file (the app can auto-download from GitHub)
2. Your saved customizations automatically re-apply (shown as "Modified" in green)
3. Click **"Apply to Game"** — done! Your game has all new keys + your custom edits
4. If the game update includes a new Data.p4k, use the Config tab to re-extract DataForge data for updated stats

## Configuration

All settings are stored in Windows Registry under:
- **Organization**: Osiris DevWorks
- **Application**: Smart Citizen

The Config tab lets you set:
- **Data sources**: Path/URL, enable/disable, auto-update per source
- **Merge hierarchy**: Drag-and-drop source priority order
- **Star Citizen install path**: Where to apply your customizations
- **Stats toggle**: Enable/disable auto-generated stat descriptions
- **DataForge extraction**: Extract entity data from game's Data.p4k

### Data Storage
- **Your edits**: `Documents\SC Localization Editor\overrides.ini`
- **Cached sources**: `Documents\SC Localization Editor\cache\` (base.ini, contracts.ini, ships.ini, etc.)
- **DataForge cache**: `Documents\SC Localization Editor\cache\dataforge\` (entity XMLs)
- **Stats data**: `Documents\SC Localization Editor\cache\` (ships_desc_stats.ini, components_desc_stats.ini, etc.)
- **Backups**: `Documents\SC Localization Editor\backups\` (max 5, oldest auto-deleted)

## Building & Release

### Development Build
```bash
python src/main.py
```

### Create Executable
```bash
cd scripts/build
python build_exe.py
```
This creates `dist/SmartCitizen-v{VERSION}.exe` using PyInstaller, where VERSION comes from `VERSION.TXT`.

### Create Installer (Windows)
Requires [Inno Setup](https://jrsoftware.org/isdl.php):
```bash
cd scripts/build
build_all.bat
```

The build script:
1. Cleans old builds
2. Builds the executable with PyInstaller
3. Compiles the installer with Inno Setup (if installed)

Outputs:
- `dist/SmartCitizen-v{VERSION}\SmartCitizen-v{VERSION}.exe` - Standalone executable (onedir)
- `dist/SmartCitizen-v{VERSION}-Setup.exe` - Installer

## Project Structure

```
src/
├── main.py                 # Application entry point
├── gui/
│   ├── main_window.py      # Main UI window with threading
│   └── config_tab.py       # Settings panel
├── models/
│   └── string_model.py     # StringEntry dataclass
├── parser/
│   └── ini_parser.py       # INI file parsing & source loading
├── merger/
│   └── ini_merger.py       # Merge engine
└── utils/
    ├── settings.py         # Windows Registry settings management
    ├── version.py          # Version reader from VERSION.TXT
    ├── updater.py          # GitHub API check + download/extract
    ├── pak_extractor.py    # P4K extraction + DataForge conversion
    └── overrides_manager.py # Overrides persistence

scripts/
├── generate_stats_ini.py   # DataForge XML → stats INI files
├── extract_components.py   # base.ini delta extraction vs stock vanilla
└── build/
    ├── build_exe.py        # PyInstaller build script
    └── build_all.bat       # Build exe + installer
```

## Game Installation Path

After applying localization, your Star Citizen directory should look like:
```
StarCitizen/
└── LIVE/
    ├── user.cfg
    └── data/
        └── Localization/
            └── english/
                └── global.ini
```

## Legal

> [!IMPORTANT]
> **Made by the Community** - This is an unofficial Star Citizen fan project, not affiliated with the Cloud Imperium group of companies. All content in this repository not authored by its host or users are property of their respective owners.

- The ability to customize your localization using extracted global.ini files is **authorized by CIG** to support community translations until officially integrated
  - *[Star Citizen: Community Localization Update](https://robertsspaceindustries.com/spectrum/community/SC/forum/1/thread/star-citizen-community-localization-update) 2023-10-11*
- Use at your own discretion as a third-party contribution
- [RSI Terms of Service](https://robertsspaceindustries.com/en/tos)
- [Translation & Fan Localization Statement](https://support.robertsspaceindustries.com/hc/en-us/articles/360006895793-Star-Citizen-Fankit-and-Fandom-FAQ#h_01JNKSPM7MRSB1WNBW6FGD2H98)

## Acknowledgments

- [ExoAE](https://github.com/ExoAE/ScCompLangPack) - Original ScCompLangPack concept and merge logic
- [MrKraken](https://github.com/MrKraken/StarStrings) - ASOP terminal enhancements, workflow improvements, and mission contract localization strings
- [BeltaKoda](https://github.com/BeltaKoda/ScCompLangPackRemix) - Community language pack remix (base file source for auto-update)
- [dolkensp/unp4k](https://github.com/dolkensp/unp4k) - Bundled `unp4k.exe` / `unforge.exe` used to unpack Data.p4k and convert DataForge to XML
- Star Citizen Community - Localization support and testing

## License

This project is provided as-is for community use. See LICENSE file for details.

## Support & Community

### Getting Help

For issues, feature requests, or contributions:
- **Join the Discord community** (link below) - Ask questions and get support
- **Report bugs** with steps to reproduce on the GitHub issues page
- **Request features** and suggest improvements
- **Share your custom localization sets** with the community

### Support the Project

Smart Citizen is a free, open-source project created to help Star Citizen players customize their game localization. If you find it useful and would like to support the development:

**Donate:**
- [PayPal Donation](https://paypal.me/RighteousKill) - Support via PayPal
- [Venmo Donation](https://venmo.com/u/Amr-Abouelleil) - Support via Venmo

**Contribute:**
- Report bugs with steps to reproduce
- Request features you'd like to see
- Share configurations and localization sets with the community
- Submit code contributions via GitHub

**Join the Community:**
- [Discord Community](https://discord.gg/BNzRegKZ7k) - Support, discussions, and feature requests

---

**Fly safe, Citizen!** o7
