"""Settings management using QSettings."""
import os
from pathlib import Path

from PyQt6.QtCore import QSettings
import winreg


class AppSettings:
    """Wrapper around QSettings for application configuration."""

    ORG_NAME = "Osiris DevWorks"
    APP_NAME = "SC Localization Editor"

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
    SOURCE_USER = "user"
    AVAILABLE_SOURCES = [SOURCE_GLOBAL, SOURCE_CONTRACTS, SOURCE_COMPONENTS, SOURCE_SHIPS, SOURCE_USER]

    @staticmethod
    def settings() -> QSettings:
        """Get QSettings instance."""
        return QSettings(AppSettings.ORG_NAME, AppSettings.APP_NAME)

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
        return AppSettings.settings().value(AppSettings.GAME_INSTALL_PATH, "")

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

        # Only migrate if new settings don't exist yet
        if settings.value(f"{AppSettings.DATA_SOURCES_PREFIX}/{AppSettings.SOURCE_GLOBAL}/path"):
            return  # Already migrated

        # Migrate base_global_path to global source
        old_base_path = settings.value(AppSettings.BASE_GLOBAL_PATH, "")
        if old_base_path:
            AppSettings.set_source_path(AppSettings.SOURCE_GLOBAL, old_base_path)

        # Pre-configure global.ini from MrKraken StarStrings repo
        if not old_base_path:  # Only if not already set
            global_url = "https://raw.githubusercontent.com/MrKraken/StarStrings/master/Data/Localization/english/global.ini"
            AppSettings.set_source_path(AppSettings.SOURCE_GLOBAL, global_url)

        # Contracts: Configure from MrKraken StarStrings repo
        # Contracts and global are separate files that must both be loaded
        contracts_url = "https://raw.githubusercontent.com/MrKraken/StarStrings/master/contracts.ini"
        AppSettings.set_source_path(AppSettings.SOURCE_CONTRACTS, contracts_url)
        AppSettings.set_source_enabled(AppSettings.SOURCE_CONTRACTS, True)

        # Components and Ships sources: empty by default
        AppSettings.set_source_path(AppSettings.SOURCE_COMPONENTS, "")
        AppSettings.set_source_enabled(AppSettings.SOURCE_COMPONENTS, False)
        AppSettings.set_source_path(AppSettings.SOURCE_SHIPS, "")
        AppSettings.set_source_enabled(AppSettings.SOURCE_SHIPS, False)

        # User source: set to overrides path
        user_path = str(AppSettings.get_overrides_path())
        AppSettings.set_source_path(AppSettings.SOURCE_USER, user_path)

        # Default hierarchy: global, contracts, user
        # (User is implicit, always added last, but include for clarity)
        AppSettings.set_merge_hierarchy(
            [AppSettings.SOURCE_GLOBAL, AppSettings.SOURCE_CONTRACTS, AppSettings.SOURCE_USER]
        )

        # Auto-update: enable for Global and Contracts by default
        AppSettings.set_source_auto_update(AppSettings.SOURCE_GLOBAL, True)
        AppSettings.set_source_auto_update(AppSettings.SOURCE_CONTRACTS, True)
        AppSettings.set_source_auto_update(AppSettings.SOURCE_COMPONENTS, False)
        AppSettings.set_source_auto_update(AppSettings.SOURCE_SHIPS, False)

    @staticmethod
    def get_overrides_path() -> Path:
        r"""Get canonical path for overrides.ini in AppData.

        Returns:
            Path to overrides.ini in %APPDATA%\Osiris DevWorks\SC Localization Editor\
        """
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(appdata) / "Osiris DevWorks" / "SC Localization Editor" / "overrides.ini"
