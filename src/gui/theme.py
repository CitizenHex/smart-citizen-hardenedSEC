"""Application theme management — light and dark modes.

Themes are applied by swapping the Qt palette on the QApplication. Widgets that
need theme-aware text colors should rely on the palette's WindowText/Text roles
(the default); secondary/dim labels use the static SECONDARY_TEXT_COLOR below.
"""
import logging
import os
import sys
from pathlib import Path

from PyQt6.QtGui import QColor, QFontDatabase, QPalette
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


# Branded display font used on the main window title + tagline. Loaded from
# assets/fonts/ at app startup via load_application_fonts(). The family name
# is what Qt reports after registering the OTF — the Fontspring demo ships
# with a prefixed family string, which we match here.
BRAND_FONT_FAMILY = "FONTSPRING DEMO - Hyperspace Race Expanded"
_BRAND_FONT_FILE = "HyperspaceRace-ExpandedBold.otf"


def _assets_fonts_dir() -> Path:
    """Resolve the assets/fonts directory for both dev and PyInstaller builds."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return base / "assets" / "fonts"


def load_application_fonts() -> None:
    """Register bundled display fonts with Qt. Call once at startup after
    QApplication is constructed and before any widgets use the font."""
    font_path = _assets_fonts_dir() / _BRAND_FONT_FILE
    if not font_path.exists():
        logger.warning(f"Brand font not found at {font_path}; using system fallback")
        return
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    if font_id < 0:
        logger.warning(f"Failed to register brand font {font_path}")
        return
    families = QFontDatabase.applicationFontFamilies(font_id)
    logger.info(f"Registered brand font families: {families}")

THEME_LIGHT = "light"
THEME_DARK = "dark"
THEME_SCLE = "scle"
THEME_ODW = "odw"
AVAILABLE_THEMES = (THEME_LIGHT, THEME_DARK, THEME_SCLE, THEME_ODW)
DEFAULT_THEME = THEME_SCLE

# Neutral mid-gray used for secondary/dim text in both themes. Readable on
# both light and dark backgrounds. Kept theme-independent so live theme
# switching doesn't need to walk every label to re-apply stylesheets.
SECONDARY_TEXT_COLOR = "#888888"


def get_secondary_text_color() -> str:
    """Return the secondary/dim text color (theme-independent)."""
    return SECONDARY_TEXT_COLOR


# Toolbar action button colors per theme. Light uses Material 500 shades;
# dark uses Material 300 so buttons read softer against the dark background.
_BUTTON_COLORS = {
    THEME_LIGHT: {
        "load":    "#2196F3",
        "restore": "#FF5722",
        "apply":   "#4CAF50",
        "clear":   "#9E9E9E",
        "open":    "#2196F3",
    },
    THEME_DARK: {
        "load":    "#64B5F6",
        "restore": "#FF8A65",
        "apply":   "#81C784",
        "clear":   "#BDBDBD",
        "open":    "#64B5F6",
    },
    THEME_SCLE: {
        "load":    "#4FD7E8",   # cube-glow cyan
        "restore": "#FF8A42",   # pencil-tip orange
        "apply":   "#4ADE80",   # bright green that pops against navy
        "clear":   "#5F7A95",   # muted cyan-gray
        "open":    "#4FD7E8",
    },
    THEME_ODW: {
        "load":    "#D4B876",   # brighter gold (navigate)
        "restore": "#C77A4D",   # copper (rollback)
        "apply":   "#A5B989",   # sage green (commit)
        "clear":   "#7A7D87",   # slate gray (cleanup)
        "open":    "#D4B876",
    },
}


def get_button_color(role: str) -> str:
    """Return the button color for the given role (load/restore/apply/clear/open)."""
    from src.utils.settings import AppSettings
    theme = AppSettings.get_theme()
    palette = _BUTTON_COLORS.get(theme, _BUTTON_COLORS[DEFAULT_THEME])
    return palette[role]


def get_button_text_color() -> str:
    """Return the readable text color for toolbar action buttons.

    Material 500 (light theme) buttons need white text. Every other theme
    uses lighter button backgrounds — black reads better on those.
    """
    from src.utils.settings import AppSettings
    return "white" if AppSettings.get_theme() == THEME_LIGHT else "black"


# Per-theme colors for the branded title + tagline labels at the top of the
# main window. Each pair ties to the theme's signature accent so the header
# reads as "of" that theme.
_TITLE_COLORS = {
    THEME_LIGHT: "#1565C0",   # rich blue
    THEME_DARK:  "#64B5F6",   # soft sky blue
    THEME_SCLE:  "#4FD7E8",   # cube-glow cyan
    THEME_ODW:   "#C9A961",   # Osiris gold
}

_TAGLINE_COLORS = {
    THEME_LIGHT: "#555555",
    THEME_DARK:  "#A0A0A0",
    THEME_SCLE:  "#6FB5D0",   # muted cyan
    THEME_ODW:   "#A08C5A",   # muted gold
}


def get_title_color() -> str:
    from src.utils.settings import AppSettings
    return _TITLE_COLORS.get(AppSettings.get_theme(), _TITLE_COLORS[DEFAULT_THEME])


def get_tagline_color() -> str:
    from src.utils.settings import AppSettings
    return _TAGLINE_COLORS.get(AppSettings.get_theme(), _TAGLINE_COLORS[DEFAULT_THEME])


def _light_palette() -> QPalette:
    """Return a palette matching the Fusion light defaults with adjusted placeholder."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(200, 200, 200))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(25, 25, 25))
    p.setColor(QPalette.ColorRole.Base,            QColor(215, 215, 215))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(208, 208, 208))
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(240, 240, 218))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor(25, 25, 25))
    p.setColor(QPalette.ColorRole.Text,            QColor(25, 25, 25))
    p.setColor(QPalette.ColorRole.Button,          QColor(200, 200, 200))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(25, 25, 25))
    p.setColor(QPalette.ColorRole.BrightText,      QColor(255, 0, 0))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(0, 120, 215))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Link,            QColor(0, 102, 204))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(110, 110, 110))
    # Disabled-state overrides so disabled text reads clearly in both modes
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(150, 150, 150))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       QColor(150, 150, 150))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(150, 150, 150))
    return p


def _dark_palette() -> QPalette:
    """Return a dark palette inspired by the Qt-community "Fusion dark" pattern."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(30, 30, 30))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(220, 220, 220))
    p.setColor(QPalette.ColorRole.Base,            QColor(30, 30, 30))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(45, 45, 48))
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(45, 45, 48))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor(220, 220, 220))
    p.setColor(QPalette.ColorRole.Text,            QColor(220, 220, 220))
    p.setColor(QPalette.ColorRole.Button,          QColor(55, 55, 58))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(220, 220, 220))
    p.setColor(QPalette.ColorRole.BrightText,      QColor(255, 80, 80))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(38, 112, 182))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Link,            QColor(100, 170, 255))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(160, 160, 160))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(120, 120, 120))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       QColor(120, 120, 120))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(120, 120, 120))
    return p


def _scle_palette() -> QPalette:
    """Star Citizen Localization Editor branded palette — deep navy + cyan
    highlights inspired by the app's splash artwork."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(13, 24, 38))    # #0D1826 deep navy
    p.setColor(QPalette.ColorRole.WindowText,      QColor(216, 232, 240)) # #D8E8F0 silver-blue
    p.setColor(QPalette.ColorRole.Base,            QColor(13, 24, 38))    # match Window for tab consistency
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(21, 37, 56))    # #152538
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(21, 37, 56))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor(216, 232, 240))
    p.setColor(QPalette.ColorRole.Text,            QColor(216, 232, 240))
    p.setColor(QPalette.ColorRole.Button,          QColor(26, 45, 68))    # #1A2D44 raised panel
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(216, 232, 240))
    p.setColor(QPalette.ColorRole.BrightText,      QColor(255, 138, 66))  # #FF8A42 orange accent
    p.setColor(QPalette.ColorRole.Highlight,       QColor(0, 212, 255))   # #00D4FF selection cyan
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(10, 18, 32))    # dark on cyan
    p.setColor(QPalette.ColorRole.Link,            QColor(79, 215, 232))  # #4FD7E8
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(111, 181, 208)) # #6FB5D0
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(88, 120, 144))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       QColor(88, 120, 144))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(88, 120, 144))
    return p


def _odw_palette() -> QPalette:
    """Osiris DevWorks branded palette — navy charcoal + antique gold,
    matching the ODW logo."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(26, 31, 46))    # #1A1F2E navy
    p.setColor(QPalette.ColorRole.WindowText,      QColor(240, 230, 207)) # #F0E6CF cream
    p.setColor(QPalette.ColorRole.Base,            QColor(26, 31, 46))    # match Window
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(36, 41, 56))    # #242938 panel
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(36, 41, 56))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor(240, 230, 207))
    p.setColor(QPalette.ColorRole.Text,            QColor(240, 230, 207))
    p.setColor(QPalette.ColorRole.Button,          QColor(36, 41, 56))    # raised
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(240, 230, 207))
    p.setColor(QPalette.ColorRole.BrightText,      QColor(199, 122, 77))  # #C77A4D copper
    p.setColor(QPalette.ColorRole.Highlight,       QColor(201, 169, 97))  # #C9A961 Osiris gold
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(26, 31, 46))    # navy on gold
    p.setColor(QPalette.ColorRole.Link,            QColor(212, 184, 118)) # #D4B876 brighter gold
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(160, 140, 90))  # #A08C5A muted gold
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(100, 90, 70))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       QColor(100, 90, 70))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(100, 90, 70))
    return p


def _palette_for(theme: str) -> QPalette:
    if theme == THEME_DARK:
        return _dark_palette()
    if theme == THEME_SCLE:
        return _scle_palette()
    if theme == THEME_ODW:
        return _odw_palette()
    return _light_palette()


def apply_theme(app: QApplication, theme: str) -> None:
    """Apply the named theme to the application.

    Forces Fusion style on the first call so palette changes render
    consistently regardless of the OS theme. Re-calling setStyle on a live
    app can crash Qt 6 during widget re-polish, so subsequent calls only
    swap the palette.
    """
    if theme not in AVAILABLE_THEMES:
        logger.warning(f"Unknown theme {theme!r}; using {DEFAULT_THEME}")
        theme = DEFAULT_THEME

    current_style = app.style().objectName() if app.style() else ""
    if current_style.lower() != "fusion":
        app.setStyle("Fusion")
    app.setPalette(_palette_for(theme))
    logger.info(f"Applied theme: {theme}")
