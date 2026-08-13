# Changelog

This file records user-visible changes made by the Smart Citizen Hardened fork.
For the full security model and verification details, see
[SECURITY_HARDENING.md](SECURITY_HARDENING.md).

## v2.3.0-hardened.24

### Security and reliability

- Added pre-extraction free-space and temporary-cache safety checks, with a
  controlled temporary workspace and a clear local read/write report.
- Added size, archive, compression-ratio, duplicate-entry, and unsafe-path
  checks for imported settings archives and standalone INI imports.
- Strengthened Apply rollback snapshots by recording and verifying SHA-256
  hashes before restoring original game files.

### Setup and local data

- Quick Setup now enables its third step as soon as the local game data import
  finishes, rather than waiting for a stale worker reference to clear.
- Kept local-test runtime data outside the disposable application build folder
  so rebuilding does not remove extracted game data or local settings.
- Extraction progress now shows that the initial `Data.p4k` scan is still
  working instead of appearing stalled at 0%.

### Loot Tags

- Updated Finder catalog parsing to accept the endpoint's supported response
  wrappers while retaining strict response validation and record limits.
- Added an obvious on-page success message after a Finder refresh, including
  the number of exact-name records loaded.
- Moved Finder refresh, import, and export controls above the item list and
  compacted the list so tag controls remain visible without scrolling.

## Unreleased — Hardened portable baseline

### Security

- Removed application update checks, update downloads, installer execution,
  and the update user interface.
- Removed startup remote-source synchronization and Discord test-report
  submission.
- Restricted INI imports to local files.
- Replaced unsafe Python pickle cache loading with rebuilt local-data lookups.
- Added SHA-256 verification for bundled P4K extraction executables and DLLs.
- Rebuilt `unp4k` and `unforge` from reviewed source after removing the
  extractor’s exception-report upload and adding output-path containment.
- Restricted optional language downloads to approved HTTPS sources with
  redirect checks, a size limit, content validation, and atomic writes.
- Added an opt-in Offline Security Mode that blocks and logs network access.
- Added a visible Hardened Build & Integrity Report that verifies the
  extraction tools and DLLs against their pinned SHA-256 values on demand.
- Added an exportable, local-only JSON audit log for successful/failed Apply,
  emergency rollback, and audit-log export operations.
- Portable packages now verify their complete build manifest at startup and
  refuse to launch when a listed runtime file is missing or modified.

### Portability and recovery

- Added a portable ZIP build with settings stored locally in `data\\config.json`.
- Added a one-click emergency restore path and stronger backups for game-file
  changes.
- Added a first-run Quick Setup flow that prepares local game data before
  generation and Apply.
- Added explicit **Import Previous Settings** support for migrations; existing
  settings are never replaced automatically.
- Quick Setup now scans the local Star Citizen log history and imports earned
  blueprints before generating and applying enhancements.

### Blueprint Tracker

- Fixed the tracker and `[Owned]` tags when the user renames the mission
  **POTENTIAL BLUEPRINTS** heading.
- Fixed Ship Weapons tags using round or curly Tag Builder wrappers and
  collapsed stale stacked tags into one Blueprint Tracker item.

### Verification

- Added security-focused regression tests for network policy, bundled-tool
  integrity, rollback behavior, portable settings, and Blueprint Tracker
  custom headings.

## Upstream

This fork began from the Smart Citizen project by Osiris DevWorks. Refer to the
Git history and upstream project for changes that predate this fork.
