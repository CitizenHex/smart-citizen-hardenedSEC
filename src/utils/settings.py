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
    APP_NAME = "SC Localization Editor"

    # Settings keys - Favorites
    FAVORITE_PREFIX = "favorite_prefix"

    # Settings keys - Stats enhancements
    STATS_ENABLED = "stats_enhancements_enabled"

    # Stats cache filenames (written by generate_stats_ini.py into cache dir)
    STATS_FILES = {
        "ship_descs":          "ships_desc_stats.ini",
        "component_descs":     "components_desc_stats.ini",
        "ship_weapon_descs":   "ship_weapons_desc_stats.ini",
        "fps_weapon_descs":    "fps_weapons_desc_stats.ini",
    }

    # Settings keys - Legacy (kept for migration)
    BASE_GLOBAL_PATH = "base_global_path"
    VEHICLES_PATH = "vehicles_path"
    LAST_OVERRIDES_PATH = "last_overrides_path"
    GAME_INSTALL_PATH = "game_install_path"
    AUTO_WRITE_ENABLED = "auto_write_enabled"
    WINDOW_GEOMETRY = "window_geometry"
    WINDOW_STATE = "window_state"

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
    AVAILABLE_SOURCES = [SOURCE_GLOBAL, SOURCE_CONTRACTS, SOURCE_COMPONENTS, SOURCE_SHIPS, SOURCE_COMMODITIES, SOURCE_GEAR, SOURCE_USER]

    @staticmethod
    def settings() -> QSettings:
        """Get QSettings instance."""
        return QSettings(AppSettings.ORG_NAME, AppSettings.APP_NAME)

    @staticmethod
    def get_stats_enabled() -> bool:
        """Check whether stats enhancements are enabled (default: True)."""
        return AppSettings.settings().value(AppSettings.STATS_ENABLED, True, type=bool)

    @staticmethod
    def set_stats_enabled(enabled: bool) -> None:
        """Enable or disable stats enhancements."""
        AppSettings.settings().setValue(AppSettings.STATS_ENABLED, enabled)

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
        # First, check if installer set the SC directory in registry
        try:
            reg_path = r'Software\Osiris DevWorks\SC Localization Editor'
            registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path)
            sc_directory, _ = winreg.QueryValueEx(registry_key, 'sc_directory')
            winreg.CloseKey(registry_key)
            if sc_directory:
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
            List of source names in merge order, e.g. ["global", "contracts", "user"]
        """
        # Default: Global, Contracts, User (User always last but not in list - added implicitly)
        default = [AppSettings.SOURCE_GLOBAL, AppSettings.SOURCE_CONTRACTS, AppSettings.SOURCE_USER]
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
        contracts_url = "https://raw.githubusercontent.com/Osiris-DevWorks/sc-localization-editor/main/data/contracts.ini"
        AppSettings.set_source_path(AppSettings.SOURCE_CONTRACTS, contracts_url)
        AppSettings.set_source_enabled(AppSettings.SOURCE_CONTRACTS, True)
        AppSettings.set_source_auto_update(AppSettings.SOURCE_CONTRACTS, True)

        # Components: OsirisDevworks-hosted
        components_url = "https://raw.githubusercontent.com/Osiris-DevWorks/sc-localization-editor/main/data/components.ini"
        AppSettings.set_source_path(AppSettings.SOURCE_COMPONENTS, components_url)
        AppSettings.set_source_enabled(AppSettings.SOURCE_COMPONENTS, True)
        AppSettings.set_source_auto_update(AppSettings.SOURCE_COMPONENTS, True)

        # Ships: OsirisDevworks-hosted
        ships_url = "https://raw.githubusercontent.com/Osiris-DevWorks/sc-localization-editor/main/data/ships.ini"
        AppSettings.set_source_path(AppSettings.SOURCE_SHIPS, ships_url)
        AppSettings.set_source_enabled(AppSettings.SOURCE_SHIPS, True)
        AppSettings.set_source_auto_update(AppSettings.SOURCE_SHIPS, True)

        # Commodities: OsirisDevworks-hosted
        commodities_url = "https://raw.githubusercontent.com/Osiris-DevWorks/sc-localization-editor/main/data/commodities.ini"
        AppSettings.set_source_path(AppSettings.SOURCE_COMMODITIES, commodities_url)
        AppSettings.set_source_enabled(AppSettings.SOURCE_COMMODITIES, True)
        AppSettings.set_source_auto_update(AppSettings.SOURCE_COMMODITIES, True)

        # User source: set to overrides path
        user_path = str(AppSettings.get_overrides_path())
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
    def migrate_contracts_to_osiris() -> bool:
        """Migrate contracts source from MrKraken to OsirisDevworks-hosted URL (v0.6.0+).

        Only applies if Contracts still points to MrKraken's repo.

        Returns:
            True if migration was performed, False if already on OsirisDevworks or custom URL.
        """
        current_path = AppSettings.get_source_path(AppSettings.SOURCE_CONTRACTS)
        osiris_url = "https://raw.githubusercontent.com/Osiris-DevWorks/sc-localization-editor/main/data/contracts.ini"
        if "MrKraken" in current_path or "StarStrings" in current_path:
            AppSettings.set_source_path(AppSettings.SOURCE_CONTRACTS, osiris_url)
            AppSettings.set_source_enabled(AppSettings.SOURCE_CONTRACTS, True)
            AppSettings.set_source_auto_update(AppSettings.SOURCE_CONTRACTS, True)
            logger.info("Migrated contracts source to OsirisDevworks-hosted URL")
            return True
        return False

    @staticmethod
    def migrate_components_source_to_default() -> bool:
        """Configure Components source to OsirisDevworks repo default (v0.5.1+).

        Only applies if Components is currently disabled with no path set.
        Users who have already configured a custom Components source are not affected.

        Returns:
            True if migration was performed, False if already configured.
        """
        current_path = AppSettings.get_source_path(AppSettings.SOURCE_COMPONENTS)
        components_url = "https://raw.githubusercontent.com/Osiris-DevWorks/sc-localization-editor/main/data/components.ini"

        if current_path and "OsirisDevworks" not in current_path:
            return False  # Already configured with a correct URL — don't overwrite
        AppSettings.set_source_path(AppSettings.SOURCE_COMPONENTS, components_url)
        AppSettings.set_source_enabled(AppSettings.SOURCE_COMPONENTS, True)
        AppSettings.set_source_auto_update(AppSettings.SOURCE_COMPONENTS, True)

        # Insert components into hierarchy after global (before contracts)
        hierarchy = AppSettings.get_merge_hierarchy()
        if AppSettings.SOURCE_COMPONENTS not in hierarchy:
            try:
                idx = hierarchy.index(AppSettings.SOURCE_GLOBAL) + 1
            except ValueError:
                idx = 0
            hierarchy.insert(idx, AppSettings.SOURCE_COMPONENTS)
            AppSettings.set_merge_hierarchy(hierarchy)

        logger.info("Configured Components source to OsirisDevworks default URL")
        return True

    @staticmethod
    def migrate_commodities_source_to_default() -> bool:
        """Configure Commodities source to OsirisDevworks repo default (v0.5.1+).

        Only applies if Commodities is not yet configured. Users with a custom
        Commodities source are not affected.

        Returns:
            True if migration was performed, False if already configured.
        """
        current_path = AppSettings.get_source_path(AppSettings.SOURCE_COMMODITIES)
        commodities_url = "https://raw.githubusercontent.com/Osiris-DevWorks/sc-localization-editor/main/data/commodities.ini"

        if current_path and "OsirisDevworks" not in current_path:
            return False  # Already configured with a correct URL — don't overwrite
        AppSettings.set_source_path(AppSettings.SOURCE_COMMODITIES, commodities_url)
        AppSettings.set_source_enabled(AppSettings.SOURCE_COMMODITIES, True)
        AppSettings.set_source_auto_update(AppSettings.SOURCE_COMMODITIES, True)

        # Insert commodities into hierarchy before user (after contracts if present)
        hierarchy = AppSettings.get_merge_hierarchy()
        if AppSettings.SOURCE_COMMODITIES not in hierarchy:
            try:
                idx = hierarchy.index(AppSettings.SOURCE_CONTRACTS) + 1
            except ValueError:
                try:
                    idx = hierarchy.index(AppSettings.SOURCE_USER)
                except ValueError:
                    idx = len(hierarchy)
            hierarchy.insert(idx, AppSettings.SOURCE_COMMODITIES)
            AppSettings.set_merge_hierarchy(hierarchy)

        logger.info("Configured Commodities source to OsirisDevworks default URL")
        return True

    @staticmethod
    def migrate_ships_source_to_default() -> bool:
        """Configure Ships source to OsirisDevworks repo default (v0.5.2+).

        Only applies if Ships is not yet configured or uses a legacy wrong URL.

        Returns:
            True if migration was performed, False if already configured.
        """
        current_path = AppSettings.get_source_path(AppSettings.SOURCE_SHIPS)
        ships_url = "https://raw.githubusercontent.com/Osiris-DevWorks/sc-localization-editor/main/data/ships.ini"

        if current_path and "OsirisDevworks" not in current_path:
            return False  # Already configured with a correct URL — don't overwrite
        AppSettings.set_source_path(AppSettings.SOURCE_SHIPS, ships_url)
        AppSettings.set_source_enabled(AppSettings.SOURCE_SHIPS, True)
        AppSettings.set_source_auto_update(AppSettings.SOURCE_SHIPS, True)

        # Insert ships into hierarchy after components (before contracts)
        hierarchy = AppSettings.get_merge_hierarchy()
        if AppSettings.SOURCE_SHIPS not in hierarchy:
            try:
                idx = hierarchy.index(AppSettings.SOURCE_COMPONENTS) + 1
            except ValueError:
                try:
                    idx = hierarchy.index(AppSettings.SOURCE_GLOBAL) + 1
                except ValueError:
                    idx = 0
            hierarchy.insert(idx, AppSettings.SOURCE_SHIPS)
            AppSettings.set_merge_hierarchy(hierarchy)

        logger.info("Configured Ships source to OsirisDevworks default URL")
        return True

    @staticmethod
    def migrate_gear_source_to_default() -> bool:
        """Configure Gear source to OsirisDevworks repo default (v0.5.2+).

        Only applies if Gear is not yet configured or uses a legacy wrong URL.

        Returns:
            True if migration was performed, False if already configured.
        """
        current_path = AppSettings.get_source_path(AppSettings.SOURCE_GEAR)
        gear_url = "https://raw.githubusercontent.com/Osiris-DevWorks/sc-localization-editor/main/data/gear.ini"

        if current_path and "OsirisDevworks" not in current_path:
            return False  # Already configured with a correct URL — don't overwrite
        AppSettings.set_source_path(AppSettings.SOURCE_GEAR, gear_url)
        AppSettings.set_source_enabled(AppSettings.SOURCE_GEAR, True)
        AppSettings.set_source_auto_update(AppSettings.SOURCE_GEAR, True)

        # Insert gear after ships in hierarchy (before contracts)
        hierarchy = AppSettings.get_merge_hierarchy()
        if AppSettings.SOURCE_GEAR not in hierarchy:
            try:
                idx = hierarchy.index(AppSettings.SOURCE_SHIPS) + 1
            except ValueError:
                try:
                    idx = hierarchy.index(AppSettings.SOURCE_COMPONENTS) + 1
                except ValueError:
                    try:
                        idx = hierarchy.index(AppSettings.SOURCE_GLOBAL) + 1
                    except ValueError:
                        idx = 0
            hierarchy.insert(idx, AppSettings.SOURCE_GEAR)
            AppSettings.set_merge_hierarchy(hierarchy)

        logger.info("Configured Gear source to OsirisDevworks default URL")
        return True

    @staticmethod
    def get_user_data_dir() -> Path:
        r"""Get the user data directory: Documents\SC Localization Editor\.

        Uses the real Documents folder path from the registry, which correctly
        handles OneDrive/folder-redirection. Falls back to Path.home()/Documents.

        Returns:
            Path to Documents\SC Localization Editor\ (created if needed)
        """
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
            )
            docs_path = Path(winreg.QueryValueEx(key, "Personal")[0])
            winreg.CloseKey(key)
        except (WindowsError, OSError):
            docs_path = Path.home() / "Documents"

        data_dir = docs_path / "SC Localization Editor"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    @staticmethod
    def get_cache_dir() -> Path:
        r"""Get canonical cache directory in Documents\SC Localization Editor\cache\.

        Returns:
            Path to Documents\SC Localization Editor\cache\ (created if needed)
        """
        cache_dir = AppSettings.get_user_data_dir() / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @staticmethod
    def get_overrides_path() -> Path:
        r"""Get canonical path for overrides.ini in Documents\SC Localization Editor\.

        Returns:
            Path to Documents\SC Localization Editor\overrides.ini
        """
        return AppSettings.get_user_data_dir() / "overrides.ini"

    @staticmethod
    def get_backups_dir() -> Path:
        r"""Get canonical backups directory in Documents\SC Localization Editor\backups\.

        Returns:
            Path to Documents\SC Localization Editor\backups\ (created if needed)
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
    def ensure_overrides_file() -> None:
        """Ensure overrides.ini exists, creating empty file if needed."""
        overrides_path = AppSettings.get_overrides_path()

        # Create parent directory if needed
        overrides_path.parent.mkdir(parents=True, exist_ok=True)

        # Create empty overrides file if it doesn't exist
        if not overrides_path.exists():
            try:
                overrides_path.touch()
                logger.info(f"Created empty overrides.ini: {overrides_path}")
            except Exception as e:
                logger.error(f"Failed to create overrides.ini: {e}")
