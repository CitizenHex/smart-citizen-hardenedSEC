"""UI string localization.

Load at startup:
    from src.utils import i18n
    i18n.set_language(AppSettings.get_selected_language())

Use everywhere user-visible text is needed:
    from src.utils.i18n import tr
    btn = QPushButton(tr("toolbar.apply_btn"))
    msg = tr("dialogs.export_complete", path=out_path, size=zip_size)

Key format: dot-separated path into the JSON tree.
Missing keys fall back to English, then return the bare key string so
nothing blows up if a translation file is incomplete.

The UI language is loaded once at startup from
``languages/<lang>/ui.json`` (overlaid onto English for missing keys).
A language switch at runtime calls set_language() again; widgets already
constructed will not update automatically — a full UI restart is needed
for the chrome to reflect the new language, but the game strings
(global.ini) reload immediately via the normal merge+reload path.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# The fallback base for every other language. i18n is deliberately a leaf
# module (no AppSettings import), so it carries its own constant instead of
# AppSettings.DEFAULT_LANGUAGE; the two must agree.
_DEFAULT_LANG = "english"

_current_lang: str = _DEFAULT_LANG
_strings: dict = {}


def _load_file(language: str) -> dict:
    """Load ``languages/<language>/ui.json``, returning {} on any error."""
    try:
        from src.utils.resource_path import get_resource_path
        path = Path(get_resource_path(f"languages/{language}/ui.json"))
        if not path.exists():
            return {}
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        logger.warning(f"i18n: could not load ui.json for {language!r}: {exc}")
        return {}


def _deep_merge(base: dict, overlay: dict) -> None:
    """Recursively merge *overlay* into *base* in-place."""
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            if isinstance(base.get(k), dict) and not isinstance(v, dict):
                logger.warning(f"i18n: key {k!r} in overlay is a scalar but base has a dict; replacing")
            base[k] = v


def set_language(lang: str) -> None:
    """Switch the active UI language.

    Always starts from the English base so missing keys in *lang* fall
    back to English rather than returning the bare key string.
    """
    global _current_lang, _strings
    new_strings = _load_file(_DEFAULT_LANG)
    if lang != _DEFAULT_LANG:
        _deep_merge(new_strings, _load_file(lang))
    _current_lang = lang
    _strings = new_strings
    logger.debug(f"i18n: UI language set to {lang!r}")


def tr(key: str, **kwargs) -> str:
    """Return the translated string for *key*.

    Supports dot-separated paths: ``tr("toolbar.apply_btn")``.
    Interpolates *kwargs* using str.format — e.g.
    ``tr("config.p4k_status_found_with_base", date="2025-01-01")``.
    Returns the bare *key* if not found anywhere so callers never crash.
    """
    global _strings
    if not _strings:
        # Lazy default: callers outside the app's startup path (helpers used
        # by tests, CLI-adjacent utils) get English instead of bare keys.
        set_language(_current_lang)
    node = _strings
    for part in key.split("."):
        if not isinstance(node, dict):
            node = None
            break
        node = node.get(part)

    if node is None:
        logger.debug(f"i18n: missing key {key!r} (lang={_current_lang!r})")
        return key

    val = str(node)
    if kwargs:
        try:
            return val.format(**kwargs)
        except (KeyError, ValueError):
            return val
    return val
