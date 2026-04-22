"""Settings management using QSettings."""
import logging
import os
from pathlib import Path

from PyQt6.QtCore import QSettings
import winreg

logger = logging.getLogger(__name__)


class AppSettings:
    """Wrapper around QSettings for application configuration."""

    ORG_NAME = "Osiris DevWorks"
    # QSettings registry node — 0.9.2+ uses "Smart Citizen" to match the
    # product rebrand. Legacy installs at "SC Localization Editor" are
    # migrated on first launch by migrate_registry_appname().
    APP_NAME = "Smart Citizen"
    # The old node name, preserved so the one-shot migration can find it.
    _LEGACY_APP_NAME = "SC Localization Editor"

    # Settings keys - Favorites
    FAVORITE_PREFIX = "favorite_prefix"

    # Settings keys - Appearance
    THEME = "theme"

    # Settings keys - Enhancements
    ENHANCEMENTS_ENABLED = "enhancements_enabled"

    # Enhancements cache filenames (written by generate_enhancements_ini.py into cache dir)
    ENHANCEMENTS_FILES = {
        "ship_descs":          "ships_desc_enhancements.ini",
        "component_descs":     "components_desc_enhancements.ini",
        "ship_weapon_descs":   "ship_weapons_desc_enhancements.ini",
        "fps_weapon_descs":    "fps_weapons_desc_enhancements.ini",
        "mission_rewards":     "mission_rewards_enhancements.ini",
        "commodity_crafting":  "commodity_crafting_enhancements.ini",
        "journal":            "journal_enhancements.ini",
        "missile_enhancements": "missile_enhancements.ini",
    }

    # User-facing category labels — match the filter categories on the main page
    ENHANCEMENT_LABELS = {
        "ships":       "Ships",
        "ship_items":  "Ship Items",
        "gear":        "Gear",
        "missions":    "Missions",
        "commodities": "Commodities",
        "journal":     "Journal",
    }

    # Maps each checkbox key to the enhancement file keys it controls
    ENHANCEMENT_CATEGORY_FILES = {
        "ships":       ["ship_descs"],
        "ship_items":  ["component_descs", "ship_weapon_descs", "missile_enhancements"],
        "gear":        ["fps_weapon_descs"],
        "missions":    ["mission_rewards"],
        "commodities": ["commodity_crafting"],
        "journal":     ["journal"],
    }

    # Settings keys - Legacy (kept for migration)
    BASE_GLOBAL_PATH = "base_global_path"
    VEHICLES_PATH = "vehicles_path"
    LAST_OVERRIDES_PATH = "last_overrides_path"
    GAME_INSTALL_PATH = "game_install_path"
    AUTO_WRITE_ENABLED = "auto_write_enabled"
    WINDOW_GEOMETRY = "window_geometry"
    WINDOW_STATE = "window_state"
    # Explicit override for the user-data directory. When set, takes
    # precedence over the Documents\Smart Citizen\ default. Users who have
    # Documents redirected to OneDrive can point this at a local path to
    # avoid slow extraction / rmtree races on OneDrive-synced folders.
    USER_DATA_DIR = "user_data_dir"

    # Settings keys - Data sources (new)
    # Prefix: data_sources/{source_name}/
    DATA_SOURCES_PREFIX = "data_sources"
    MERGE_HIERARCHY = "merge_hierarchy"
    SOURCE_AUTO_UPDATE_PREFIX = "source_auto_update"

    # Available data sources
    SOURCE_GLOBAL = "global"
    SOURCE_CONTRACTS = "contracts"
    SOURCE_COMPONENTS = "components"
    SOURCE_SHIPS = "ships"
    SOURCE_COMMODITIES = "commodities"
    SOURCE_GEAR = "gear"
    SOURCE_USER = "user"
    AVAILABLE_SOURCES = [SOURCE_GLOBAL, SOURCE_USER]

    @staticmethod
    def settings() -> QSettings:
        """Get QSettings instance."""
        return QSettings(AppSettings.ORG_NAME, AppSettings.APP_NAME)

    @staticmethod
    def get_enhancements_enabled() -> bool:
        """Check whether enhancements are enabled (default: True)."""
        return AppSettings.settings().value(AppSettings.ENHANCEMENTS_ENABLED, True, type=bool)

    @staticmethod
    def set_enhancements_enabled(enabled: bool) -> None:
        """Enable or disable enhancements."""
        AppSettings.settings().setValue(AppSettings.ENHANCEMENTS_ENABLED, enabled)

    @staticmethod
    def get_enhancement_category_enabled(key: str) -> bool:
        """Check if a specific enhancement category is enabled (default: True)."""
        return AppSettings.settings().value(
            f"enhancements/categories/{key}/enabled", True, type=bool)

    @staticmethod
    def set_enhancement_category_enabled(key: str, enabled: bool) -> None:
        """Enable or disable a specific enhancement category."""
        AppSettings.settings().setValue(
            f"enhancements/categories/{key}/enabled", enabled)

    @staticmethod
    def get_enabled_enhancement_categories() -> set[str]:
        """Return the set of enabled enhancement file keys (expanding grouped categories)."""
        result = set()
        for checkbox_key, file_keys in AppSettings.ENHANCEMENT_CATEGORY_FILES.items():
            if AppSettings.get_enhancement_category_enabled(checkbox_key):
                result.update(file_keys)
        return result

    @staticmethod
    def get_theme() -> str:
        """Get UI theme name ('light' or 'dark')."""
        from src.gui.theme import DEFAULT_THEME, AVAILABLE_THEMES
        value = AppSettings.settings().value(AppSettings.THEME, DEFAULT_THEME)
        return value if value in AVAILABLE_THEMES else DEFAULT_THEME

    @staticmethod
    def set_theme(theme: str) -> None:
        """Persist UI theme name."""
        AppSettings.settings().setValue(AppSettings.THEME, theme)
        AppSettings.settings().sync()

    @staticmethod
    def get_favorite_prefix() -> str:
        """Get the character prepended to favorited ship names (default '*')."""
        return AppSettings.settings().value(AppSettings.FAVORITE_PREFIX, "*")

    @staticmethod
    def set_favorite_prefix(prefix: str) -> None:
        """Set the character prepended to favorited ship names."""
        AppSettings.settings().setValue(AppSettings.FAVORITE_PREFIX, prefix)

    @staticmethod
    def get_base_global_path() -> str:
        """Get legacy base global path (for backward compatibility).

        This is deprecated. Use get_source_path(SOURCE_GLOBAL) instead.
        """
        return AppSettings.settings().value(AppSettings.BASE_GLOBAL_PATH, "")

    @staticmethod
    def set_base_global_path(path: str) -> None:
        """Set legacy base global path (for backward compatibility).

        This is deprecated. Use set_source_path(SOURCE_GLOBAL, path) instead.
        """
        AppSettings.settings().setValue(AppSettings.BASE_GLOBAL_PATH, path)

    @staticmethod
    def get_vehicles_path() -> str:
        """Get path to vehicles.ini."""
        return AppSettings.settings().value(AppSettings.VEHICLES_PATH, "")

    @staticmethod
    def set_vehicles_path(path: str) -> None:
        """Set path to vehicles.ini."""
        AppSettings.settings().setValue(AppSettings.VEHICLES_PATH, path)

    @staticmethod
    def get_last_overrides_path() -> str:
        """Get last directory used for overrides."""
        return AppSettings.settings().value(AppSettings.LAST_OVERRIDES_PATH, "")

    @staticmethod
    def set_last_overrides_path(path: str) -> None:
        """Set last directory used for overrides."""
        AppSettings.settings().setValue(AppSettings.LAST_OVERRIDES_PATH, path)

    @staticmethod
    def get_game_install_path() -> str:
        """Get Star Citizen install path from registry (installer) or QSettings."""
        # First, check if installer set the SC directory in registry. Mirror it
        # into QSettings on first read so the app is self-sufficient if the
        # installer key is later cleared (e.g. clean reinstall, registry cleanup).
        try:
            reg_path = r'Software\Osiris DevWorks\SC Localization Editor'
            registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path)
            sc_directory, _ = winreg.QueryValueEx(registry_key, 'sc_directory')
            winreg.CloseKey(registry_key)
            if sc_directory:
                saved = AppSettings.settings().value(AppSettings.GAME_INSTALL_PATH, "")
                if saved != sc_directory:
                    AppSettings.settings().setValue(AppSettings.GAME_INSTALL_PATH, sc_directory)
                return sc_directory
        except (WindowsError, OSError):
            pass

        # Fall back to QSettings
        saved = AppSettings.settings().value(AppSettings.GAME_INSTALL_PATH, "")
        if saved:
            return saved

        # Auto-detect from common install locations
        for candidate in [
            r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE",
            r"C:\Program Files (x86)\Roberts Space Industries\StarCitizen\LIVE",
        ]:
            if Path(candidate).exists():
                return candidate

        return ""

    @staticmethod
    def get_game_version() -> str:
        """Get Star Citizen game version from build_manifest.id.

        Returns:
            Version string (e.g., "4.7.176.58286") or empty string if not found/invalid
        """
        import json
        game_path = AppSettings.get_game_install_path()
        if not game_path:
            return ""

        manifest_path = Path(game_path) / "build_manifest.id"
        if not manifest_path.exists():
            return ""

        try:
            with open(manifest_path, 'r') as f:
                data = json.load(f)
                version = data.get("Data", {}).get("Version", "")
                return version
        except Exception as e:
            logger.debug(f"Could not read game version from {manifest_path}: {e}")
            return ""

    @staticmethod
    def set_game_install_path(path: str) -> None:
        """Set Star Citizen install path."""
        AppSettings.settings().setValue(AppSettings.GAME_INSTALL_PATH, path)

    @staticmethod
    def get_auto_write_enabled() -> bool:
        """Get auto-write to game enabled flag."""
        return AppSettings.settings().value(AppSettings.AUTO_WRITE_ENABLED, False, type=bool)

    @staticmethod
    def set_auto_write_enabled(enabled: bool) -> None:
        """Set auto-write to game enabled flag."""
        AppSettings.settings().setValue(AppSettings.AUTO_WRITE_ENABLED, enabled)

    @staticmethod
    def get_window_geometry() -> bytes:
        """Get saved window geometry."""
        return AppSettings.settings().value(AppSettings.WINDOW_GEOMETRY, b"")

    @staticmethod
    def set_window_geometry(geometry: bytes) -> None:
        """Save window geometry."""
        AppSettings.settings().setValue(AppSettings.WINDOW_GEOMETRY, geometry)

    @staticmethod
    def get_window_state() -> bytes:
        """Get saved window state."""
        return AppSettings.settings().value(AppSettings.WINDOW_STATE, b"")

    @staticmethod
    def set_window_state(state: bytes) -> None:
        """Save window state."""
        AppSettings.settings().setValue(AppSettings.WINDOW_STATE, state)

    @staticmethod
    def get_source_path(source_name: str) -> str:
        """Get path/URL for a data source.

        Args:
            source_name: One of SOURCE_GLOBAL, SOURCE_CONTRACTS, SOURCE_COMPONENTS, SOURCE_SHIPS, SOURCE_USER

        Returns:
            Path or URL string, empty string if not set
        """
        key = f"{AppSettings.DATA_SOURCES_PREFIX}/{source_name}/path"
        return AppSettings.settings().value(key, "")

    @staticmethod
    def set_source_path(source_name: str, path: str) -> None:
        """Set path/URL for a data source.

        Args:
            source_name: One of SOURCE_GLOBAL, SOURCE_CONTRACTS, SOURCE_COMPONENTS, SOURCE_SHIPS, SOURCE_USER
            path: File path or URL
        """
        key = f"{AppSettings.DATA_SOURCES_PREFIX}/{source_name}/path"
        AppSettings.settings().setValue(key, path)

    @staticmethod
    def is_source_enabled(source_name: str) -> bool:
        """Check if a data source is enabled.

        Args:
            source_name: One of SOURCE_GLOBAL, SOURCE_CONTRACTS, SOURCE_COMPONENTS, SOURCE_SHIPS, SOURCE_USER

        Returns:
            True if enabled, False otherwise. Defaults to True for Global and User, False for others.
        """
        key = f"{AppSettings.DATA_SOURCES_PREFIX}/{source_name}/enabled"
        # Default: Global and User always enabled, others disabled
        default = source_name in [AppSettings.SOURCE_GLOBAL, AppSettings.SOURCE_USER]
        return AppSettings.settings().value(key, default, type=bool)

    @staticmethod
    def set_source_enabled(source_name: str, enabled: bool) -> None:
        """Enable or disable a data source.

        Args:
            source_name: One of SOURCE_GLOBAL, SOURCE_CONTRACTS, SOURCE_COMPONENTS, SOURCE_SHIPS, SOURCE_USER
            enabled: True to enable, False to disable
        """
        key = f"{AppSettings.DATA_SOURCES_PREFIX}/{source_name}/enabled"
        AppSettings.settings().setValue(key, enabled)

    @staticmethod
    def get_merge_hierarchy() -> list:
        """Get the merge hierarchy (ordered list of source names).

        Returns:
            List of source names in merge order, e.g. ["global", "user"]
        """
        default = [AppSettings.SOURCE_GLOBAL, AppSettings.SOURCE_USER]
        value = AppSettings.settings().value(AppSettings.MERGE_HIERARCHY, default)
        # Handle QVariant/list conversion
        if isinstance(value, str):
            # If stored as comma-separated string, split it
            return value.split(",") if value else default
        return value if value else default

    @staticmethod
    def set_merge_hierarchy(hierarchy: list) -> None:
        """Set the merge hierarchy (ordered list of source names).

        Args:
            hierarchy: List of source names in merge order
        """
        AppSettings.settings().setValue(AppSettings.MERGE_HIERARCHY, hierarchy)

    @staticmethod
    def get_source_auto_update(source_name: str) -> bool:
        """Check if auto-update is enabled for a source.

        Args:
            source_name: One of SOURCE_GLOBAL, SOURCE_CONTRACTS, SOURCE_COMPONENTS, SOURCE_SHIPS
            (SOURCE_USER does not support auto-update)

        Returns:
            True if auto-update enabled, False otherwise. Defaults to True.
        """
        if source_name == AppSettings.SOURCE_USER:
            return False  # User source never auto-updates
        key = f"{AppSettings.SOURCE_AUTO_UPDATE_PREFIX}/{source_name}"
        return AppSettings.settings().value(key, True, type=bool)

    @staticmethod
    def set_source_auto_update(source_name: str, enabled: bool) -> None:
        """Enable or disable auto-update for a source.

        Args:
            source_name: One of SOURCE_GLOBAL, SOURCE_CONTRACTS, SOURCE_COMPONENTS, SOURCE_SHIPS
            enabled: True to auto-update, False to disable
        """
        if source_name == AppSettings.SOURCE_USER:
            return  # Cannot change auto-update for User source
        key = f"{AppSettings.SOURCE_AUTO_UPDATE_PREFIX}/{source_name}"
        AppSettings.settings().setValue(key, enabled)

    @staticmethod
    def migrate_legacy_settings() -> None:
        """Migrate old settings keys to new data source format.

        Called on first run with new version. Preserves old settings while
        populating new ones for backward compatibility.
        """
        settings = AppSettings.settings()

        # Check if migration has already been done (look for contracts as the latest addition)
        if settings.value(f"{AppSettings.DATA_SOURCES_PREFIX}/{AppSettings.SOURCE_CONTRACTS}/path"):
            return  # Already migrated

        # Global: point to local cached base.ini (populated by P4K extraction).
        # No remote URL — users extract from their own Data.p4k.
        global_local_path = str(AppSettings.get_cache_dir() / 'base.ini')
        AppSettings.set_source_path(AppSettings.SOURCE_GLOBAL, global_local_path)
        AppSettings.set_source_enabled(AppSettings.SOURCE_GLOBAL, True)
        AppSettings.set_source_auto_update(AppSettings.SOURCE_GLOBAL, False)

        # Contracts: OsirisDevworks-hosted
        contracts_url = "https://raw.githubusercontent.com/Osiris-DevWorks/smart-citizen/main/data/contracts.ini"
        AppSettings.set_source_path(AppSettings.SOURCE_CONTRACTS, contracts_url)
        AppSettings.set_source_enabled(AppSettings.SOURCE_CONTRACTS, True)
        AppSettings.set_source_auto_update(AppSettings.SOURCE_CONTRACTS, True)

        # Components: OsirisDevworks-hosted
        components_url = "https://raw.githubusercontent.com/Osiris-DevWorks/smart-citizen/main/data/components.ini"
        AppSettings.set_source_path(AppSettings.SOURCE_COMPONENTS, components_url)
        AppSettings.set_source_enabled(AppSettings.SOURCE_COMPONENTS, True)
        AppSettings.set_source_auto_update(AppSettings.SOURCE_COMPONENTS, True)

        # Ships: OsirisDevworks-hosted
        ships_url = "https://raw.githubusercontent.com/Osiris-DevWorks/smart-citizen/main/data/ships.ini"
        AppSettings.set_source_path(AppSettings.SOURCE_SHIPS, ships_url)
        AppSettings.set_source_enabled(AppSettings.SOURCE_SHIPS, True)
        AppSettings.set_source_auto_update(AppSettings.SOURCE_SHIPS, True)

        # Commodities: OsirisDevworks-hosted
        commodities_url = "https://raw.githubusercontent.com/Osiris-DevWorks/smart-citizen/main/data/commodities.ini"
        AppSettings.set_source_path(AppSettings.SOURCE_COMMODITIES, commodities_url)
        AppSettings.set_source_enabled(AppSettings.SOURCE_COMMODITIES, True)
        AppSettings.set_source_auto_update(AppSettings.SOURCE_COMMODITIES, True)

        # User source: set to user.ini path
        user_path = str(AppSettings.get_user_ini_path())
        AppSettings.set_source_path(AppSettings.SOURCE_USER, user_path)

        # Default hierarchy: global → components → contracts → commodities → user
        AppSettings.set_merge_hierarchy(
            [AppSettings.SOURCE_GLOBAL, AppSettings.SOURCE_COMPONENTS,
             AppSettings.SOURCE_CONTRACTS, AppSettings.SOURCE_COMMODITIES,
             AppSettings.SOURCE_USER]
        )

    @staticmethod
    def migrate_global_to_p4k_local() -> bool:
        """Migrate global source from any remote URL to local cached base.ini (v0.6.0+).

        For existing users whose Global source still points to MrKraken, BeltaKoda,
        or any other remote URL: switch to local cache path and disable auto-update
        so the file is managed by P4K extraction instead of remote download.

        Returns:
            True if migration was performed, False if already using local path.
        """
        current_path = AppSettings.get_source_path(AppSettings.SOURCE_GLOBAL)
        if current_path.startswith('http'):
            local_path = str(AppSettings.get_cache_dir() / 'base.ini')
            AppSettings.set_source_path(AppSettings.SOURCE_GLOBAL, local_path)
            AppSettings.set_source_auto_update(AppSettings.SOURCE_GLOBAL, False)
            logger.info("Migrated global source from remote URL to local P4K cache path")
            return True
        return False





    @staticmethod
    def _resolve_docs_base() -> Path:
        """Resolve the real Documents root (honors OneDrive redirection)."""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
            )
            docs_path = Path(winreg.QueryValueEx(key, "Personal")[0])
            winreg.CloseKey(key)
        except (WindowsError, OSError):
            docs_path = Path.home() / "Documents"
        return docs_path

    # ── Registry appname migration (0.9.0 rebrand) ──────────────────────────
    # Rebrand moved the product name from "SC Localization Editor" to
    # "Smart Citizen" in 0.9.0. The Documents folder got renamed back then
    # (see migrate_docs_folder_rename). The registry node was left alone
    # to preserve existing users' settings, which meant fresh-eyes readers
    # kept seeing the old name under HKCU. The helpers below perform a
    # one-shot copy from the legacy node to the new node, then delete the
    # old subtree. A marker value (_MIGRATION_MARKER) short-circuits
    # subsequent runs so this is cheap on every startup.

    _MIGRATION_MARKER = "_migrated_from_legacy_appname"

    @staticmethod
    def migrate_registry_appname() -> None:
        r"""Copy HKCU\Software\<ORG>\SC Localization Editor → HKCU\Software\<ORG>\Smart Citizen.

        Must run **before** any ``AppSettings.settings()`` call — QSettings
        under the new APP_NAME would otherwise read from an empty node and
        silently lose every saved preference (themes, paths, favorites,
        window geometry, the USER_DATA_DIR override, etc.).

        Idempotent: a marker value written under the new node on first
        success prevents re-migration on every startup. Fresh installs
        (no legacy node present) stamp the marker directly so the check
        stays cheap.
        """
        org = AppSettings.ORG_NAME
        old_path = rf"SOFTWARE\{org}\{AppSettings._LEGACY_APP_NAME}"
        new_path = rf"SOFTWARE\{org}\{AppSettings.APP_NAME}"

        # Fast-path: marker already set → nothing to do.
        if AppSettings._reg_has_marker(new_path, AppSettings._MIGRATION_MARKER):
            return

        # No legacy node present — this is a fresh install (or an already-
        # cleaned-up migration where the marker was somehow lost). Stamp
        # the marker so future runs short-circuit.
        if not AppSettings._reg_key_exists(old_path):
            AppSettings._reg_write_marker(new_path, AppSettings._MIGRATION_MARKER)
            return

        logger.info(
            f"Migrating registry settings "
            f"HKCU\\{old_path}  →  HKCU\\{new_path}"
        )
        try:
            AppSettings._reg_copy_tree(old_path, new_path)
            AppSettings._reg_write_marker(new_path, AppSettings._MIGRATION_MARKER)
            AppSettings._reg_delete_tree(old_path)
            logger.info("Registry migration complete — legacy node removed")
        except OSError as e:
            # Leave the marker unset so we retry next launch. Log loudly
            # so any partial migration is visible in the Log tab.
            logger.error(f"Registry migration failed: {e}", exc_info=True)

    @staticmethod
    def _reg_key_exists(path: str) -> bool:
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ)
            winreg.CloseKey(k)
            return True
        except FileNotFoundError:
            return False

    @staticmethod
    def _reg_has_marker(path: str, marker: str) -> bool:
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ)
        except FileNotFoundError:
            return False
        try:
            winreg.QueryValueEx(k, marker)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(k)

    @staticmethod
    def _reg_write_marker(path: str, marker: str) -> None:
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, path)
        try:
            winreg.SetValueEx(k, marker, 0, winreg.REG_SZ, "1")
        finally:
            winreg.CloseKey(k)

    @staticmethod
    def _reg_copy_tree(src_path: str, dst_path: str) -> None:
        """Recursive copy of every value and subkey from src to dst under HKCU.

        Preserves value types (REG_SZ / REG_DWORD / REG_BINARY / REG_MULTI_SZ
        / REG_EXPAND_SZ) by passing EnumValue's returned type directly to
        SetValueEx. Creates dst and its subtree as needed.
        """
        src = winreg.OpenKey(winreg.HKEY_CURRENT_USER, src_path, 0, winreg.KEY_READ)
        dst = winreg.CreateKey(winreg.HKEY_CURRENT_USER, dst_path)
        try:
            # Values at this level
            i = 0
            while True:
                try:
                    name, data, vtype = winreg.EnumValue(src, i)
                except OSError:
                    break
                # Skip the marker if it happens to exist on the source side
                # (shouldn't, but defensive against manual registry edits).
                if name != AppSettings._MIGRATION_MARKER:
                    winreg.SetValueEx(dst, name, 0, vtype, data)
                i += 1
            # Recurse into subkeys
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(src, i)
                except OSError:
                    break
                AppSettings._reg_copy_tree(
                    f"{src_path}\\{sub}", f"{dst_path}\\{sub}"
                )
                i += 1
        finally:
            winreg.CloseKey(src)
            winreg.CloseKey(dst)

    @staticmethod
    def _reg_delete_tree(path: str) -> None:
        """Depth-first delete of an HKCU subtree (winreg.DeleteKey refuses
        to remove a key that still has children, so we strip leaves first)."""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_ALL_ACCESS
            )
        except FileNotFoundError:
            return
        try:
            while True:
                try:
                    sub = winreg.EnumKey(key, 0)
                except OSError:
                    break
                AppSettings._reg_delete_tree(f"{path}\\{sub}")
        finally:
            winreg.CloseKey(key)
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
        except FileNotFoundError:
            pass

    @staticmethod
    def migrate_docs_folder_rename() -> None:
        r"""Rename legacy Documents\SC Localization Editor\ → Documents\Smart Citizen\.

        Safe to call on every startup — only acts when the old folder exists
        and the new one does not. The installer handles this on upgrade; this
        path covers dev runs and anyone who bypassed the installer.
        """
        docs = AppSettings._resolve_docs_base()
        old_dir = docs / "SC Localization Editor"
        new_dir = docs / "Smart Citizen"
        if old_dir.exists() and not new_dir.exists():
            try:
                old_dir.rename(new_dir)
                logger.info(f"Renamed data folder: {old_dir} → {new_dir}")
            except OSError as e:
                logger.warning(f"Could not rename data folder {old_dir}: {e}")

    @staticmethod
    def get_user_data_dir() -> Path:
        r"""Get the user data directory.

        Resolution order:
          1. Registry override ``USER_DATA_DIR`` — set by users who want the
             cache/user.ini off a OneDrive-synced Documents folder (extraction
             and rmtree are much slower under OneDrive's sync hooks).
          2. ``Documents\Smart Citizen\`` via the ``Personal`` shell-folder
             key, which honors OneDrive/folder redirection.
          3. ``~/Documents/Smart Citizen\`` as a last-ditch fallback.

        Returns:
            Path to the resolved directory (created if needed).
        """
        override = AppSettings.settings().value(AppSettings.USER_DATA_DIR, "", type=str)
        if override:
            override_path = Path(override)
            try:
                override_path.mkdir(parents=True, exist_ok=True)
                return override_path
            except OSError as e:
                logger.warning(
                    f"USER_DATA_DIR override {override!r} not usable ({e}); "
                    f"falling back to Documents default"
                )
        data_dir = AppSettings._resolve_docs_base() / "Smart Citizen"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    @staticmethod
    def set_user_data_dir(path: "str | Path | None") -> None:
        r"""Override the user data directory. Pass ``None`` or an empty
        string to clear the override and revert to the Documents default.

        Writes to the Osiris DevWorks\SC Localization Editor registry key
        (same scope as every other AppSettings value), so it survives
        reinstalls and is per-user.
        """
        if not path:
            AppSettings.settings().remove(AppSettings.USER_DATA_DIR)
        else:
            AppSettings.settings().setValue(AppSettings.USER_DATA_DIR, str(path))
        AppSettings.settings().sync()

    @staticmethod
    def get_cache_dir() -> Path:
        r"""Get canonical cache directory in Documents\Smart Citizen\cache\.

        Returns:
            Path to Documents\Smart Citizen\cache\ (created if needed)
        """
        cache_dir = AppSettings.get_user_data_dir() / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @staticmethod
    def get_user_ini_path() -> Path:
        r"""Get canonical path for user.ini in Documents\Smart Citizen\.

        Migrates from overrides.ini → user.ini on first call if needed.

        Returns:
            Path to Documents\Smart Citizen\user.ini
        """
        data_dir = AppSettings.get_user_data_dir()
        user_ini = data_dir / "user.ini"
        old_overrides = data_dir / "overrides.ini"

        # Migrate: rename overrides.ini → user.ini if needed
        if old_overrides.exists() and not user_ini.exists():
            try:
                old_overrides.rename(user_ini)
                logger.info(f"Migrated {old_overrides} → {user_ini}")
            except OSError as e:
                logger.warning(f"Failed to migrate overrides.ini → user.ini: {e}")
                return old_overrides  # fall back to old name

        return user_ini

    @staticmethod
    def get_backups_dir() -> Path:
        r"""Get canonical backups directory in Documents\Smart Citizen\backups\.

        Returns:
            Path to Documents\Smart Citizen\backups\ (created if needed)
        """
        backups_dir = AppSettings.get_user_data_dir() / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        return backups_dir

    @staticmethod
    def migrate_data_to_documents() -> None:
        """Copy user data files from old AppData location to new Documents location.

        Safe to call on every startup — skips files that already exist at the
        destination. Handles the upgrade path for users on previous versions.
        """
        import shutil

        old_base = Path(
            os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        ) / "Osiris DevWorks" / "SC Localization Editor"
        old_cache = old_base / "cache"

        new_base  = AppSettings.get_user_data_dir()
        new_cache = AppSettings.get_cache_dir()

        # Migrate overrides.ini
        old_overrides = old_base / "overrides.ini"
        new_overrides = new_base / "overrides.ini"
        if old_overrides.exists() and not new_overrides.exists():
            try:
                shutil.copy2(old_overrides, new_overrides)
                logger.info(f"Migrated overrides.ini to Documents")
            except Exception as e:
                logger.warning(f"Could not migrate overrides.ini: {e}")

        # Migrate cache files
        if old_cache.exists():
            for ini_file in old_cache.glob("*.ini"):
                dest = new_cache / ini_file.name
                if not dest.exists():
                    try:
                        shutil.copy2(ini_file, dest)
                        logger.info(f"Migrated {ini_file.name} to Documents cache")
                    except Exception as e:
                        logger.warning(f"Could not migrate {ini_file.name}: {e}")

        # Migrate backup files from old AppData location
        old_backups = old_base / "backups"
        if old_backups.exists():
            new_backups = AppSettings.get_backups_dir()
            for bak_file in old_backups.glob("global.ini.bak_*"):
                dest = new_backups / bak_file.name
                if not dest.exists():
                    try:
                        shutil.copy2(bak_file, dest)
                        logger.info(f"Migrated {bak_file.name} to Documents backups")
                    except Exception as e:
                        logger.warning(f"Could not migrate {bak_file.name}: {e}")

    @staticmethod
    def get_unp4k_exe_path() -> Path:
        """Resolve bundled unp4k.exe — works both frozen (PyInstaller) and in dev."""
        import sys
        if getattr(sys, 'frozen', False):
            base = Path(sys._MEIPASS)
        else:
            # src/utils/settings.py → src/utils → src → project root
            base = Path(__file__).parent.parent.parent
        return base / 'assets' / 'unp4k' / 'unp4k.exe'

    @staticmethod
    def get_unforge_exe_path() -> Path:
        """Resolve bundled unforge.exe — works both frozen (PyInstaller) and in dev."""
        import sys
        if getattr(sys, 'frozen', False):
            base = Path(sys._MEIPASS)
        else:
            base = Path(__file__).parent.parent.parent
        return base / 'assets' / 'unp4k' / 'unforge.exe'

    @staticmethod
    def get_dataforge_cache_dir() -> Path:
        """Return the directory where DataForge entity XMLs are cached after unforge."""
        return AppSettings.get_cache_dir() / 'dataforge'

    @staticmethod
    def get_p4k_path() -> Path:
        """Return path to Data.p4k based on configured game install path.

        Handles both the SC root directory and the LIVE subdirectory, since the
        stored path may point to either depending on how it was configured.
        """
        game_path = Path(AppSettings.get_game_install_path())
        if game_path.name.upper() == "LIVE":
            return game_path / 'Data.p4k'
        return game_path / 'LIVE' / 'Data.p4k'

    @staticmethod
    def ensure_user_ini_file() -> None:
        """Ensure user.ini exists, creating empty file if needed."""
        user_ini_path = AppSettings.get_user_ini_path()

        user_ini_path.parent.mkdir(parents=True, exist_ok=True)

        if not user_ini_path.exists():
            try:
                user_ini_path.touch()
                logger.info(f"Created empty user.ini: {user_ini_path}")
            except Exception as e:
                logger.error(f"Failed to create user.ini: {e}")
