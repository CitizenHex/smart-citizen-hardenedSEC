"""The tester test-plan: content, progress math, and report formatting (#144).

Smart Citizen ships a "Test Plan" panel so testers on a pre-release build can
work through what changed in the release and check items off as they verify
them. This module is the Qt-free core: the plan content itself, the
progress/key helpers, and the markdown report a tester submits. The Qt panel
(`src/gui/test_plan_panel.py`) and the Discord-submit worker
(`TestPlanSubmitWorker` in `src/gui/workers.py`) build on these.

The content tracks the diff that the active release branch carries over its
integration base, so each release's plan covers exactly what's new. Update
TEST_SECTIONS when a release's scope changes; `plan_hash()` changes with it, so
a tester's stale check-marks are dropped rather than silently mislabelled.
"""
from __future__ import annotations

import hashlib
import json

# Each section is a title plus a flat list of one-line test items. Keep items
# imperative and self-contained ("do X, confirm Y") so a tester needs no other
# doc. This plan covers Smart Citizen 2.3.0 (the diff over its 2.2.1 base).
TEST_SECTIONS: list[dict] = [
    {
        "title": "Core workflow (smoke)",
        "items": [
            "Launch the app: it opens to the strings table with no crash dialog.",
            "Config tab: extract DataForge from Data.p4k; the progress bar runs start to finish and the table reloads.",
            "Generate Enhancements, edit a string's Custom Value, then Apply to Game; confirm the change shows in-game.",
            "Restore Backup (More menu): a previous global.ini is offered and restores cleanly.",
        ],
    },
    {
        "title": "New languages (#298, #299, #300, #301)",
        "items": [
            "Switch to Italian, restart: the UI, the guided tour, and the FAQ tab all show Italian text.",
            "Repeat for Chinese: game strings download from the 42Kit source without an error (this exercises the new download fix).",
            "Repeat for Japanese and German: UI translated, game strings load, Apply writes to the matching Localization folder and the game shows the language.",
            "In each language, open Help, About, and the FAQ tab: the text is translated (not English), and Help carries the Export / Import Settings section at 13.",
            "Run the installer fresh: the Select Language page offers all 8 languages; pick German and the app opens in German.",
            "Reinstall over an existing install: the language page pre-selects your previously saved language.",
        ],
    },
    {
        "title": "Blueprint Tracker additions (#249, #268, #308, #335, #336)",
        "items": [
            "Type filter: an Ammo option exists, and magazine/battery/canister blueprints (e.g. P4-AR Magazine, salvage canisters) sit under it, not FPS Weapon or Other.",
            "\"Also scan LIVE/HOTFIX (whichever isn't active)\" is checked by default; scanning with it on reads the sibling channel's logs too, and PTU/EPTU/TECH-PREVIEW are never touched.",
            "Check \"Rescan all logs (ignore last scan)\", scan: every log is re-read, the checkbox unchecks itself after the scan.",
            "Export Owned Blueprints to JSON, then import the same file: the summary says 0 blueprints were added (not the file size).",
            "Export to CSV, clear a few owned items, import the CSV: only the missing ones are re-added; importing never removes anything.",
            "Import an scmdb.net export file: its blueprint names match and land in Owned.",
            "In a mission's POTENTIAL BLUEPRINTS, raw-filename bullets like \"bp_craft_nozzle_fuelgiver...\" no longer appear; those items show their real names (e.g. Harkin).",
        ],
    },
    {
        "title": "Settings Backup (#311)",
        "items": [
            "Config tab > Export Settings...: a small zip is written; open it and confirm it contains a manifest and per-channel user.ini files.",
            "Import Settings... with that zip: the confirm dialog names Restore user.ini as the undo path; after confirming, the app restarts and offers to regenerate and apply.",
            "After the restart, spot-check settings and a channel's user.ini contents match what was exported.",
            "Switch the app to French, Spanish, or Portuguese and open the import confirm dialog: the text is translated, carries accents, and references that language's Restore user.ini button name.",
        ],
    },
    {
        "title": "Ship favoriting rules (#329, #330)",
        "items": [
            "In the strings table, the favorite star works on ship/vehicle NAME rows only; a ship description row shows no star and right-click offers no Add Favorite.",
            "Turn on the Ship/Vehicle Names Only filter: the table narrows to exactly the rows favoriting applies to.",
            "If a description row still carries a favorite prefix from an older version (custom value starts with *): right-click offers Remove Favorite, and it strips the prefix.",
        ],
    },
    {
        "title": "Tags: nozzles, mining lasers, commodities, [BP?] (#266, #325, #341)",
        "items": [
            "With Components > Type enabled, generate: fuel nozzle names (Norfield, Harkin, ...) and mining-laser heads carry a bracketed tag in blueprint lists and the String Editor.",
            "On a fresh profile, commodities show no name tags until you enable the commodity elements in the Tag Builder (all three default off).",
            "Find a Rayari \"resources for research\" mission: its title shows [BP?] and its details body says 25% chance; a Recco Battaglia mission still shows plain [BP].",
        ],
    },
    {
        "title": "Fit and finish (#292, #296, #302, #303, #304, #319)",
        "items": [
            "Simple mode's one-button apply: after the run, Generate Enhancements is green, not stuck red.",
            "After a log scan that applies owned tags, Apply Owned Tags is green, not stuck red.",
            "Switch channels: Save Tag Changes lights up correctly for the new channel (not stale-green from the old one).",
            "Start an extraction while the RSI Launcher is downloading or verifying: a plain-language message explains Data.p4k is locked, with no crash or raw error.",
            "After Apply, the launcher version string shows the Smart Citizen watermark on its own second line, once (no piling up after repeated applies).",
            "Mission descriptions show reputation rewards without a leading + (e.g. \"500\", not \"+500\").",
        ],
    },
    {
        "title": "Resource Signature ore-name annotation + mission-details breakdown (#331)",
        "items": [
            "Enhancements Tab: the ore-name RS checkbox and the Mission Detail Field's Resource Signatures checkbox are independent, both on by default.",
            "With the default settings, generate and check a mineable ore's Mining Compendium entry: its name reads e.g. \"Aluminium (RS 4285)\".",
            "Same setting, then find a Recco Battaglia scan/mining mission: the Work Brief text and Primary Objectives panel also show the ore name with its RS value appended.",
            "Same mission, MISSION DETAILS shows a per-ore RS value progression line too, e.g. \"Ice: 4300 - 8600 - ...\".",
            "Turn both off and regenerate: neither the ore-name annotation nor the DETAILS breakdown appears; the mission-title [RS ####] tag (General Tags) is unaffected either way.",
        ],
    },
    {
        "title": "Portable build (#293)",
        "items": [
            "Unzip the portable build into a deep folder path (several nested folders), run it, extract and apply: no path-length errors.",
            "Close the app and delete the whole portable folder to the Recycle Bin: the delete succeeds without a path-too-long failure.",
        ],
    },
]


def plan_hash() -> str:
    """Short stable digest of the plan content.

    Stored alongside a tester's check-marks; when the plan changes the hash
    changes, so stale marks (now pointing at different items) are discarded.
    """
    blob = json.dumps(TEST_SECTIONS, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def item_key(section_idx: int, item_idx: int) -> str:
    """Stable key for one checklist item (``"<section>:<item>"``)."""
    return f"{section_idx}:{item_idx}"


def all_item_keys() -> list[str]:
    """Every item key in section/item order."""
    return [
        item_key(s, i)
        for s, section in enumerate(TEST_SECTIONS)
        for i in range(len(section["items"]))
    ]


def total_items() -> int:
    return sum(len(section["items"]) for section in TEST_SECTIONS)


def progress(checked) -> tuple[int, int, int]:
    """Return (done, total, percent) for the set of checked item keys.

    Only keys that exist in the current plan count, so a stale/foreign key
    can't push the count past the total.
    """
    valid = set(all_item_keys())
    done = sum(1 for k in checked if k in valid)
    total = len(valid)
    pct = round(done * 100 / total) if total else 0
    return done, total, pct


def build_report(checked, tester_name: str, version: str, notes: str = "") -> str:
    """Render the tester's run as a markdown report (clipboard or Discord).

    Shows overall and per-section progress and a ✅/⬜ line per item, so a
    reader sees exactly what was and wasn't verified.
    """
    checked = set(checked)
    done, total, pct = progress(checked)
    tester = tester_name.strip() or "Anonymous"
    lines = [
        f"**Smart Citizen v{version} - Test Plan Report**",
        f"Tester: {tester}",
        f"Progress: {done}/{total} ({pct}%)",
        "",
    ]
    for s, section in enumerate(TEST_SECTIONS):
        sec_keys = [item_key(s, i) for i in range(len(section["items"]))]
        sec_done = sum(1 for k in sec_keys if k in checked)
        lines.append(f"__{section['title']}__ ({sec_done}/{len(sec_keys)})")
        for i, text in enumerate(section["items"]):
            mark = "✅" if item_key(s, i) in checked else "⬜"
            lines.append(f"{mark} {text}")
        lines.append("")
    notes = notes.strip()
    if notes:
        lines.append("__Notes__")
        lines.append(notes)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def discord_chunks(report: str, limit: int = 1900) -> list[str]:
    """Split a report into Discord-message-sized chunks (2000-char hard cap).

    Splits on line boundaries so a markdown line is never cut mid-way. A single
    line longer than *limit* is hard-sliced as a last resort.
    """
    chunks: list[str] = []
    current = ""
    for line in report.split("\n"):
        while len(line) > limit:
            # Pathological single long line: hard-slice it.
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = line if not current else current + "\n" + line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks
