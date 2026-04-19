# Smart Citizen

*Smarter Strings for Star Citizen*

## About This Project

**Smart Citizen** is a powerful, user-friendly tool for Star Citizen players to customize their game's localization strings. Load, edit, and apply localization changes with full persistence, automatic backups, and seamless support for game updates.

Developed by **Osiris DevWorks**, a one-man development studio dedicated to creating valuable tools for the gaming community.

## The Osiris DevWorks Promise

All Osiris DevWorks tools will be either **completely free** or have a **free tier**. We believe in creating value for gamers without paywalls or mandatory subscriptions.

## Key Features

### 🎯 Core Features
- **Load & Edit**: Load global.ini from your Star Citizen installation and customize strings in an intuitive table view
- **Mission Contracts**: Edit mission contract and briefing text from the dedicated Missions category
- **Smart Filtering**: Search strings, filter by category (Ships, Ship Items, Missions, Gear, Commodities, Journal, Other), or modification status
- **Per-Column Filters**: Type directly into filter boxes below each column header for fine-grained searching
- **Safe Application**: Automatic timestamped backups before applying changes to prevent data loss
- **Restore Backups**: Keep up to 5 backup versions — revert changes anytime with one click
- **Import INI**: Import an existing INI file and resolve conflicts key-by-key with the built-in conflict dialog

### 🔄 Auto-Update & Persistence
- **P4K Extraction**: Extracts stock localization strings directly from your installed Data.p4k — always in sync with your game version
- **Persistent Edits**: Your customizations are automatically saved and reloaded in every session
- **Seamless Migration**: When Star Citizen updates, your saved edits automatically re-apply to the new base strings
- **Clean UI**: High-performance table view with filters, in-line editing, keyboard shortcuts, and a modern interface

### 📊 Enhancements
- **Ship Stats**: SCM speed, hydrogen fuel, quantum fuel, cargo capacity, and weapon loadouts appended to ship descriptions
- **Component Stats**: Shield HP, power draw, cooling rate, and other stats for ship components
- **Weapon Stats**: DPS, fire rate, range, and damage stats for ship weapons and FPS weapons
- **Mission Rewards**: Payment amounts appended to mission descriptions
- **Selective Categories**: Enable or disable each enhancement category independently from the Enhancements tab

### 🎨 Themes
- **Light / Dark**: Classic UI themes
- **Default**: Deep-navy cyber theme inspired by Star Citizen's mobiGlas UI
- **ODW**: Osiris DevWorks signature theme — navy charcoal with antique gold

### 🛡️ Data Management
- **Automatic Backups**: Timestamped backups created before applying changes to your game
- **Registry Persistence**: All paths and preferences saved securely in Windows Registry
- **Documents Storage**: Your custom edits stored in `Documents\SC Localization Editor\` for safe persistence across sessions

## Quick Start

1. **First Launch**: App auto-detects your Star Citizen installation and downloads the latest base localization file
2. **Extract (Optional)**: Click "Extract from Data.p4k" in the Config tab to load stock game strings directly from your install
3. **Edit Strings**: Use the search and filter tools, then double-click any Custom Value cell to customize text
4. **Apply**: Click "Apply to Game" — your changes are saved and applied with an automatic backup
5. **Enhancements (Optional)**: Open the Enhancements tab to enable stat overlays for ships, components, and weapons
6. **Migrate**: After game updates, re-extract from Data.p4k — your edits reapply automatically

## Community & Support

### Join Us
- 💬 [Discord Community](https://discord.gg/BNzRegKZ7k) - Get support, share configs, request features

### Support This Project
Smart Citizen is completely free. If you find it valuable:
- 💳 [Donate via PayPal](https://paypal.me/RighteousKill)
- 💰 [Donate via Venmo](https://venmo.com/u/Amr-Abouelleil)

## Other Tools by Osiris DevWorks

- **[SC Profile Editor](https://github.com/Osiris-DevWorks/sc-profile-editor)** - Import, edit, and export Star Citizen control profiles
- **[Extended AFK](https://github.com/Osiris-RK/extended-afk)** - AFK tool to prevent idle timeouts

## Built On

Built with **PyQt6** and powered by the Star Citizen community's localization work.

**GitHub**: https://github.com/Osiris-DevWorks/smart-citizen
