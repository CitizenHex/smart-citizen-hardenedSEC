# SC Localization Editor - Claude Instructions

## Project Overview

SC Localization Editor is a PyQt6 GUI application for editing Star Citizen localization strings. It allows users to:
- Load base global.ini and vehicles.ini files
- Create and manage custom string overrides
- Merge custom strings back into the source files
- Export localized versions for use in the game

## Architecture

The application follows a modular, layered architecture:

```
src/
├── main.py                 # Entry point
├── gui/
│   ├── main_window.py      # Main UI, toolbar, table, filters
│   └── config_tab.py       # Configuration settings
├── models/
│   └── string_model.py     # StringEntry dataclass
├── parser/
│   └── ini_parser.py       # INI file parsing
├── merger/
│   └── ini_merger.py       # Merge/export logic
└── utils/
    ├── settings.py         # QSettings wrapper
    └── version.py          # Version reader
```

## Key Design Patterns

### 1. Data Model (StringEntry)
Each localization string is represented as a `StringEntry` with:
- `key`: The localization key
- `source_file`: "global.ini" or "vehicles.ini"
- `category`: Extracted from key prefix (Ships/ANVL, Weapons, etc.)
- `original_value`: Value from source file
- `custom_value`: User's override (empty if unmodified)
- `status`: "Modified", "Unmodified", or "New"

Category extraction is automatic based on key patterns:
- `vehicle_NameANVL_*` → "Ships/ANVL"
- `weapons_*` → "Weapons"
- Uppercase prefixes → use prefix as category
- Lowercase prefixes → convert to title case

### 2. Parsing (ini_parser.py)
- Line-by-line parsing for efficiency (handles 83k lines)
- Strips comments (`;` prefix)
- Splits on first `=` only (preserves `,P` plural markers in keys)
- Preserves file structure during merge

### 3. Merging (ini_merger.py)
- Reads source file line-by-line
- For matching keys, replaces values
- Preserves all structural elements (comments, blank lines, formatting)
- Writes UTF-8 output

### 4. GUI (main_window.py)
- Toolbar with colored action buttons (green=load, blue=save, purple=merge, orange=apply)
- Filter bar: search text, source file, category, status dropdowns
- 5-column table: Category, Key, Original Value, Custom Value, Status
- Row-based filtering (no proxy model) for simplicity
- Double-click "Custom Value" to edit in-place
- Context menu: Edit, Reset to Original, Copy Key
- Status bar showing "Showing X of Y strings"

### 5. Settings (settings.py)
Uses QSettings with Osiris DevWorks organization:
- `base_global_path` - Path to base global.ini
- `vehicles_path` - Path to vehicles.ini
- `game_install_path` - SC installation directory
- `auto_write_enabled` - Auto-copy to game after merge
- `window_geometry`, `window_state` - Window restoration

## Configuration Tab (config_tab.py)
Settings persist via QSettings:
- Browse for base global.ini (CIG original or existing language pack)
- Browse for vehicles.ini
- Browse for game installation path
- Auto-write toggle
- Save Configuration button

## Workflow

1. **Load Files** → Select base global.ini, vehicles.ini, optional target_strings.ini
2. **Filter & Edit** → Use filters, double-click cells to customize values
3. **Save Overrides** → Export custom values as target_strings.ini
4. **Merge & Export** → Combine base + custom into merged_global.ini
5. **Apply to Game** → Copy merged file to game's Localization/english/ directory

## File Locations

- Source files: `src/` folder (global.ini, vehicles.ini)
- Data: Can be loaded from anywhere via file dialogs
- Output: `output/` directory (merged_global.ini)
- Config: Windows Registry (via QSettings)

## Testing Checklist

- [ ] Run `python src/main.py` - window opens
- [ ] Load source files - table populates
- [ ] Filter by text, source, category, status - rows show/hide
- [ ] Double-click custom value - edit in-place
- [ ] Save overrides - target_strings.ini written
- [ ] Merge & export - merged_global.ini created
- [ ] Apply to game - file copied to correct location
- [ ] Build installer - runs without errors

## Build Instructions

### Development
```bash
pip install -r requirements.txt
python src/main.py
```

### Build Executable
```bash
pyinstaller SCLocalizationEditor.spec
```

### Create Installer
Use Inno Setup to compile `installer.iss`

## Common Issues

### "Device or resource busy" when renaming directory
- Close IDE/text editor with directory open
- Close any file explorer windows
- Run in separate terminal

### QSettings not persisting
- QSettings uses Windows Registry (HKEY_CURRENT_USER)
- Check organization/app names match (Osiris DevWorks / SC Localization Editor)

### Large file performance
- Parser uses line-by-line iteration (no full file load)
- Table filtering via `setRowHidden()` (no proxy model)
- Should handle 83k+ lines smoothly

## Future Enhancements

- Diff view for before/after comparisons
- Batch find & replace
- Import/export to other formats (CSV, Excel)
- Profile/preset support for different customization sets
- Real-time preview of merged output
- Undo/redo history

## Dependencies

- **PyQt6** (>=6.10.0) - GUI framework
- **pyinstaller** (>=6.3.0) - Executable builder
- **pyperclip** (>=1.8.2) - Clipboard access

## Contact

Osiris DevWorks - https://github.com/OsirisDevworks/sc-localization-editor
