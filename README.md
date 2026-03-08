# SC Localization Editor

A PyQt6 GUI application for managing Star Citizen localization string customizations.

> [!NOTE]
> This project is forked from [ExoAE's ScCompLangPack](https://github.com/ExoAE/ScCompLangPack) and built upon the merge concepts from [MrKraken's ASOP terminal enhancements](https://www.youtube.com/@MrKraken). Rather than another fork, we've created an intuitive desktop GUI to make localization customization more user-friendly.

## ✨ Features

- **Load & Edit**: Load base global.ini and vehicles.ini files, then easily customize strings in a table view
- **Search & Filter**: Filter by search text, source file, category, or modification status
- **Save Overrides**: Export custom strings to target_strings.ini
- **Merge & Export**: Combine base files with your customizations into a merged file
- **Apply to Game**: Automatically copy merged localization files to your Star Citizen installation
- **Settings Persistence**: All paths and preferences are saved between sessions

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Star Citizen global.ini and vehicles.ini files (extracted from Data.p4k)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/OsirisDevworks/sc-localization-editor.git
   cd sc-localization-editor
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python src/main.py
   ```

## 📖 Usage

1. **Load Files**: Click "Load Base & Custom" and select:
   - Base global.ini (from your Star Citizen Data.p4k)
   - vehicles.ini (from your Star Citizen Data.p4k)
   - Optional: target_strings.ini (existing customizations)

2. **Find & Customize**: Use the filter bar to find strings, then double-click the "Custom Value" column to edit

3. **Save Your Work**: Click "Save Overrides" to export your customizations as target_strings.ini

4. **Merge & Export**: Click "Merge & Export" to combine your customizations with the base files

5. **Apply to Game**: Click "Apply to Game" to copy the merged file to your Star Citizen installation
   - The installer automatically adds `g_language = english` to your user.cfg

## 🛠️ Configuration

All settings are stored in Windows Registry under:
- **Organization**: Osiris DevWorks
- **Application**: SC Localization Editor

You can configure the following in the Config tab:
- Path to base global.ini
- Path to vehicles.ini
- Star Citizen installation directory
- Auto-write to game (optionally copy files automatically after merge)

## 📦 Building an Installer

### Create Executable
```bash
pyinstaller SCLocalizationEditor.spec
```

### Create Installer (Windows)
Use [Inno Setup](https://jrsoftware.org/isdl.php) to compile `installer.iss`:
```
- Install Inno Setup
- Open installer.iss
- Click "Compile"
```

The installer will:
- Install the application to Program Files
- Create Start Menu shortcuts
- Automatically set up user.cfg with `g_language = english`

## 📁 Project Structure

```
src/
├── main.py                 # Application entry point
├── gui/
│   ├── main_window.py      # Main UI window
│   └── config_tab.py       # Settings panel
├── models/
│   └── string_model.py     # StringEntry dataclass
├── parser/
│   └── ini_parser.py       # INI file parsing
├── merger/
│   └── ini_merger.py       # Merge logic
└── utils/
    ├── settings.py         # Settings management
    └── version.py          # Version reader
```

## 🎮 Installation Path Structure

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

## ⚖️ Legal

> [!IMPORTANT]
> **Made by the Community** - This is an unofficial Star Citizen fan project, not affiliated with the Cloud Imperium group of companies. All content in this repository not authored by its host or users are property of their respective owners.

- The ability to customize your localization using extracted global.ini files is **authorized by CIG** to support community translations until officially integrated
  - *[Star Citizen: Community Localization Update](https://robertsspaceindustries.com/spectrum/community/SC/forum/1/thread/star-citizen-community-localization-update) 2023-10-11*
- Use at your own discretion as a third-party contribution
- [RSI Terms of Service](https://robertsspaceindustries.com/en/tos)
- [Translation & Fan Localization Statement](https://support.robertsspaceindustries.com/hc/en-us/articles/360006895793-Star-Citizen-Fankit-and-Fandom-FAQ#h_01JNKSPM7MRSB1WNBW6FGD2H98)

## 🙏 Acknowledgments

- [ExoAE](https://github.com/ExoAE/ScCompLangPack) - Original ScCompLangPack concept and merge logic
- [MrKraken](https://www.youtube.com/@MrKraken) - ASOP terminal enhancements and workflow improvements
- Star Citizen Community - Localization support and testing

## 📝 License

This project is provided as-is for community use. See LICENSE file for details.

## 🤝 Support & Community

### Getting Help

For issues, feature requests, or contributions:
- **Join the Discord community** (link below) - Ask questions and get support
- **Report bugs** with steps to reproduce on the GitHub issues page
- **Request features** and suggest improvements
- **Share your custom localization sets** with the community

### Support the Project

SC Localization Editor is a free, open-source project created to help Star Citizen players customize their game localization. If you find it useful and would like to support the development:

**Donate:**
- 💳 **[PayPal Donation](https://paypal.me/RighteousKill)** - Support via PayPal
- 💰 **[Venmo Donation](https://venmo.com/u/Amr-Abouelleil)** - Support via Venmo

**Contribute:**
- Report bugs with steps to reproduce
- Request features you'd like to see
- Share configurations and localization sets with the community
- Submit code contributions via GitHub

**Join the Community:**
- 💬 **[Discord Community](https://discord.gg/BNzRegKZ7k)** - Support, discussions, and feature requests

Even if you can't donate, your feedback and bug reports are invaluable!

---

**Fly safe, Citizen!** o7
