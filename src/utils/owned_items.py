"""Owned-blueprint tagging (#157).

Users mark blueprint items they already own; an ``[Owned]`` tag is then woven
onto that item wherever it appears in a mission reward POTENTIAL BLUEPRINTS
list. Keyed by item *display name* (issue #157 option a) because the GUI table
never sees item UUIDs — it works purely from localization keys and values.

Qt-free and settings-free so it can be unit-tested with plain strings. The
transform is idempotent: it strips any existing ``[Owned]`` tags before
re-applying, so it can run on every load and on every toggle without doubling.

Values use a literal ``\\n`` (backslash-n) line separator — the in-INI encoding
the parser and game both read — so all matching here is on the two-character
sequence, not a real newline.
"""
from __future__ import annotations

import re
import unicodedata

# The bullet line separator inside a stored INI value (literal backslash-n).
_NL = "\\n"
# A POTENTIAL BLUEPRINTS bullet: "\n- <name>". Names can carry a leading
# component tag ("[Mil-S1-A] Norfield") and we keep everything up to the next
# separator.
_BULLET_RE = re.compile(re.escape(_NL) + r"- ([^\\]+)")
# The owned tag we weave in. EM4 renders blue in-game — the visibility the
# request asked for ("so it's in blue").
_OWNED_TAG = " <EM4>[Owned]</EM4>"
# Strip a previously-applied owned tag (with or without the leading space).
_OWNED_STRIP_RE = re.compile(r"\s*<EM4>\[Owned\]</EM4>")
# A leading bracketed component tag on a bullet name, e.g. "[Mil-S1-A] ".
_LEADING_TAG_RE = re.compile(r"^\[[^\]]*\]\s*")
# A trailing bracketed tag, e.g. "10-Series Greatsword Cannon [B-S2-A]". The
# Tag Builder's placement setting is per-category and user-configurable
# (prepend/append), so the same class/size/grade tag can land on either side
# of the name depending on which category (components vs. ship_weapons vs.
# missiles) it came from. Stripping both sides keeps matching independent of
# that setting instead of only handling the default leading placement.
_TRAILING_TAG_RE = re.compile(r"\s*\[[^\]]*\]\s*$")
# Collapse any run of whitespace to a single space. Runs after NFKC folds a
# non-breaking space (U+00A0, seen in log names like "Lynx\xa0Legs") into a
# plain space, so the same item from a log and from loc data normalize alike.
_WS_RE = re.compile(r"\s+")

# Marks the start of a POTENTIAL BLUEPRINTS section. The header text is
# user-configurable (AppSettings.MISSION_HEADER_DEFAULTS["blueprints"]) but the
# default is BP_SECTION_HEADER; we match that default case-insensitively. This
# module stays settings-free by design, so it owns the default literal rather
# than importing AppSettings, and the settings default is kept in sync with it.
# blueprint_meta.py and entry_filter.py import BP_SECTION_HEADER from here so
# the three matchers share one source of truth. A value with no such header has
# no bullets to tag, so it passes through untouched.
BP_SECTION_HEADER = "POTENTIAL BLUEPRINTS"
_BP_HEADER_RE = re.compile(BP_SECTION_HEADER, re.IGNORECASE)
# A genuine section header (POTENTIAL BLUEPRINTS, ITEM REWARDS, MISSION
# DETAILS, BLUEPRINT DATA, ...) as opposed to a per-region sub-header inside
# the blueprints list itself (e.g. <EM4>[Nyx]</EM4>,
# <EM4>[Pyro RegionA, Pyro RegionB]</EM4>) — region labels always start with
# "[" right after the tag, section headers never do.
_SECTION_HEADER_RE = re.compile(r"<EM([34])>(?!\[)[^<]*</EM\1>")


def _bp_section_span(value: str):
    """Return (start, end) spanning just the POTENTIAL BLUEPRINTS section's
    bullet content — from right after its header up to the next real section
    header (or end of string). ``None`` when there's no such section.

    Bounding the scan this way matters: CIG mission bodies sometimes carry a
    stray "\\n- <word>" line in the flavor-text prose *before* the header
    (e.g. "\\n- Stows\\n"), and a body with both a POTENTIAL BLUEPRINTS
    section and a later ITEM REWARDS section (e.g. "\\n- Council Scrip")
    puts a real bullet-shaped line after it too. Un-scoped bullet matching
    swept both into the blueprint item set.
    """
    m = _BP_HEADER_RE.search(value)
    if not m:
        return None
    start = m.end()
    next_header = _SECTION_HEADER_RE.search(value, start)
    end = next_header.start() if next_header else len(value)
    return start, end


def normalize_item_name(name: str) -> str:
    """Reduce a bullet/name to a stable identity for matching.

    Applies, in order: NFKC unicode folding (so a non-breaking space becomes a
    plain space), removal of any ``[Owned]`` tag, removal of a leading *and* a
    trailing bracketed component tag (``[Mil-S1-A] Norfield`` and
    ``Norfield [Mil-S1-A]`` both reduce to the bare name), and whitespace
    collapse. Used for both the owned set and bullet matching, so a tagged
    bullet, a log-imported name, and a bare item row all resolve to one key.

    Both sides of every comparison pass through here (the owned-set entries and
    the mission bullets in ``apply_owned_to_value``), so the folding is
    symmetric and can never introduce a one-sided mismatch.
    """
    if not name:
        return ""
    s = unicodedata.normalize("NFKC", name)
    s = _OWNED_STRIP_RE.sub("", s)
    s = _LEADING_TAG_RE.sub("", s)
    s = _TRAILING_TAG_RE.sub("", s)
    return _WS_RE.sub(" ", s).strip()


def extract_bp_item_names(value: str) -> set[str]:
    """Return the normalized item names in *value*'s POTENTIAL BLUEPRINTS list.

    Empty when the value has no such section. Scoped to just that section's
    span (see :func:`_bp_section_span`) so a stray prose bullet before the
    header or a real bullet in a later section (ITEM REWARDS, ...) isn't
    picked up as a blueprint item.
    """
    if not value:
        return set()
    span = _bp_section_span(value)
    if span is None:
        return set()
    start, end = span
    return {normalize_item_name(m.group(1))
            for m in _BULLET_RE.finditer(value, start, end)
            if normalize_item_name(m.group(1))}


def apply_owned_to_value(value: str, owned: set[str]) -> str:
    """Return *value* with ``[Owned]`` on bullets whose item is in *owned*.

    Idempotent: any existing ``[Owned]`` tag is removed first, so the result is
    a pure function of (value, owned) and re-running never doubles the tag.
    Values without a POTENTIAL BLUEPRINTS section are returned unchanged (after
    stripping stale owned tags, in case an item was just un-owned). Retagging
    is scoped to just that section's span (see :func:`_bp_section_span`) so a
    stray prose bullet before the header or a bullet in a later section can
    never be mistaken for a blueprint item.
    """
    if not value:
        return value
    # Strip any prior owned tags first (handles un-owning + idempotency).
    value = _OWNED_STRIP_RE.sub("", value)
    if not owned:
        return value
    span = _bp_section_span(value)
    if span is None:
        return value
    start, end = span

    def _retag(m: re.Match) -> str:
        raw = m.group(1)
        if normalize_item_name(raw) in owned:
            return f"{_NL}- {raw}{_OWNED_TAG}"
        return m.group(0)

    return value[:start] + _BULLET_RE.sub(_retag, value[start:end]) + value[end:]
