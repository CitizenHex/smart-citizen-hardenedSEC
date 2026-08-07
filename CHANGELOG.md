# Changelog

This file records user-visible changes made by the Smart Citizen Hardened fork.
For the full security model and verification details, see
[SECURITY_HARDENING.md](SECURITY_HARDENING.md).

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

### Verification

- Added security-focused regression tests for network policy, bundled-tool
  integrity, rollback behavior, portable settings, and Blueprint Tracker
  custom headings.

## Upstream

This fork began from the Smart Citizen project by Osiris DevWorks. Refer to the
Git history and upstream project for changes that predate this fork.
