# SC Localization Editor

## About This Project

**SC Localization Editor** is a powerful, user-friendly tool for Star Citizen players to customize their game's localization strings. Load, edit, and apply localization changes with full persistence, automatic backups, and seamless support for game updates.

Built on the foundation of **ExoAE's ScCompLangPack** and **MrKraken's ASOP workflow**, SC Localization Editor combines proven localization concepts into an intuitive desktop application.

Developed by **Osiris DevWorks**, a one-man development studio dedicated to creating valuable tools for the gaming community.

## The Osiris DevWorks Promise

All Osiris DevWorks tools will be either **completely free** or have a **free tier**. We believe in creating value for gamers without paywalls or mandatory subscriptions.

## Key Features

### 🎯 Core Features
- **Load & Edit**: Load global.ini from your Star Citizen installation and customize strings in an intuitive table view
- **Mission Contracts**: Edit mission contract and briefing text from the dedicated Missions category
- **Smart Filtering**: Search strings, filter by category (Ships, Ship Components, Missions, Other), or modification status
- **Safe Application**: Automatic timestamped backups before applying changes to prevent data loss
- **Restore Backups**: Keep up to 5 backup versions — revert changes anytime with one click

### 🔄 Auto-Update & Persistence
- **Auto-Update**: Checks GitHub for the latest base localization file and mission contracts — download and apply with one click
- **Persistent Edits**: Your customizations are automatically saved and reloaded in every session
- **Seamless Migration**: When Star Citizen updates, your saved edits automatically re-apply to the new base file
- **Clean UI**: Table view with filters, in-line editing, keyboard shortcuts, and a modern interface

### 🛡️ Data Management
- **Automatic Backups**: Timestamped backups created before applying changes to your game
- **Registry Persistence**: All paths and preferences saved securely in Windows Registry
- **AppData Storage**: Your custom edits stored in `%APPDATA%` for safe persistence across sessions

## Quick Start

1. **First Launch**: App auto-detects your Star Citizen installation and checks for latest base files
2. **Load File**: Click "Load Base File" to load global.ini
3. **Edit Strings**: Use the search and filter tools, then double-click to customize any text
4. **Apply**: Click "Apply to Game" — your changes are saved and applied with an automatic backup
5. **Migrate**: After game updates, just reload the new base file — your edits reapply automatically

## Community & Support

### Join Us
- 💬 [Discord Community](https://discord.gg/BNzRegKZ7k) - Get support, share configs, request features

### Support This Project
SC Localization Editor is completely free. If you find it valuable:
- 💳 [Donate via PayPal](https://paypal.me/RighteousKill)
- 💰 [Donate via Venmo](https://venmo.com/u/Amr-Abouelleil)

## Other Tools by Osiris DevWorks

- **[SC Profile Editor](https://github.com/Osiris-DevWorks/sc-profile-editor)** - Import, edit, and export Star Citizen control profiles
- **[Extended AFK](https://github.com/Osiris-RK/extended-afk)** - AFK tool to prevent idle timeouts

## Built On

Built with **PyQt6** and powered by the Star Citizen community's localization work.

**Version**: 0.2.0 | **GitHub**: https://github.com/Osiris-DevWorks/sc-localization-editor
