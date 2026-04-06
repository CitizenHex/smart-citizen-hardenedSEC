"""
generate_stats_ini.py
─────────────────────
Downloads scunpacked-data JSON files and generates stats-augmented INI files
for use as additional sources in SC Localization Editor.

Output files (written to OUTPUT_DIR):
  ships_desc_stats.ini        – vehicle_Desc* entries with flight/cargo/shield stats
  components_desc_stats.ini   – item_Desc* COOL/SHLD/POWR/QDRV with numerical stats
  ship_weapons_desc_stats.ini – item_Desc* WeaponGun/Missile/Bomb with weapon stats
  fps_weapons_desc_stats.ini  – item_Desc* WeaponPersonal with weapon stats

Usage:
  python scripts/generate_stats_ini.py [base_ini_path]

  base_ini_path defaults to the app's AppData cache (base.ini).
  Scunpacked JSON files are cached in OUTPUT_DIR/cache/ and re-used on subsequent runs.
"""

import json
import os
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

# ── Paths ────────────────────────────────────────────────────────────────────

SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

APPDATA = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
APP_CACHE_DIR    = Path(APPDATA) / "Osiris DevWorks" / "SC Localization Editor" / "cache"
DEFAULT_BASE_INI = APP_CACHE_DIR / "base.ini"

# Stats output goes to AppData cache so the app finds it automatically.
# JSON source cache lives in a sub-folder to keep it separate.
OUTPUT_DIR = APP_CACHE_DIR
CACHE_DIR  = APP_CACHE_DIR / "stats_cache"

REPO_BASE = "https://raw.githubusercontent.com/StarCitizenWiki/scunpacked-data/master/"

SOURCES = {
    "ships":      "ships.json",
    "ship_items": "ship-items.json",
    "fps_items":  "fps-items.json",
}

# ── Download ─────────────────────────────────────────────────────────────────

def download(url: str, dest: Path) -> None:
    print(f"  Downloading {url}")
    req = Request(url, headers={"User-Agent": "sc-localization-editor-stats/1.0"})
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(req, timeout=120) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        done  = 0
        with open(dest, "wb") as f:
            while chunk := resp.read(1 << 16):
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    print(f"\r  {pct}% ({done:,} / {total:,} bytes)", end="", flush=True)
        print()


def load_json(key: str) -> list | dict:
    dest = CACHE_DIR / SOURCES[key]
    if not dest.exists():
        download(REPO_BASE + SOURCES[key], dest)
    else:
        print(f"  Using cached {dest.name}")
    return json.loads(dest.read_text(encoding="utf-8"))


# ── INI parsing ──────────────────────────────────────────────────────────────

def parse_ini(path: Path) -> dict[str, str]:
    """Return key → value dict from a plain key=value INI file."""
    result = {}
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line.strip() or line.strip().startswith(";"):
                continue
            if "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            # Strip plural marker from key for lookup purposes
            lookup_key = k.split(",")[0].strip()
            if lookup_key:
                result[lookup_key] = v.strip()
    return result


# ── Lookup builders ──────────────────────────────────────────────────────────

def _normalize_classname(cls: str) -> str:
    """Strip common suffixes like _SCItem that are absent from localization keys."""
    return cls.removesuffix("_SCItem")


def build_lookup(records: list, extra_name_map: dict[str, str] | None = None) -> dict[str, dict]:
    """
    Build two-level lookup for a list of scunpacked records:
      by_class[classname_lower] → record   (suffix-normalized)
      by_name[name_lower]       → record   (fallback)
    Returns a single dict with both keys merged (class takes priority).
    """
    by_class: dict[str, dict] = {}
    by_name:  dict[str, dict] = {}
    for rec in records:
        cls  = (rec.get("ClassName") or rec.get("className") or "")
        name = (rec.get("Name")      or rec.get("name")      or "").lower().strip()
        if cls:
            by_class[_normalize_classname(cls).lower()] = rec
        if name:
            by_name[name] = rec
    return {"class": by_class, "name": by_name}


def find_record(lookup: dict, loc_key: str, prefix: str, name_values: dict) -> dict | None:
    """
    Look up a scunpacked record for a localization _desc key.

    Strategy:
      1. Strip `prefix` from loc_key → try as ClassName (case-insensitive)
      2. Fallback: find the corresponding Name key in name_values, then match by Name
    """
    # Strip plural marker from key before extracting class name
    bare = loc_key.split(",")[0]
    if not bare.startswith(prefix):
        return None
    cls_candidate = bare[len(prefix):].lower()

    rec = lookup["class"].get(cls_candidate)
    if rec:
        return rec

    # Fallback: look up the display name from the localization (item_Name* or vehicle_Name*)
    if prefix == "vehicle_Desc":
        name_key = "vehicle_Name" + bare[len(prefix):]
    else:
        name_key = "item_Name" + bare[len(prefix):]

    display_name = name_values.get(name_key, "").lower().strip()
    if display_name:
        rec = lookup["name"].get(display_name)
        if rec:
            return rec

    return None


# ── Stat formatters ──────────────────────────────────────────────────────────

def _fmt(value, unit="", decimals=0) -> str:
    if value is None:
        return "?"
    try:
        v = float(value)
        if decimals:
            return f"{v:,.{decimals}f}{unit}"
        return f"{int(round(v)):,}{unit}"
    except (TypeError, ValueError):
        return str(value)


def _get_std(item: dict) -> dict:
    """Return stdItem sub-dict (ship-items.json nests data there)."""
    return item.get("stdItem") or item


def _rn_generation(item: dict, resource: str) -> float | None:
    """Extract ResourceNetwork generation rate for a given resource type.

    Walks all state Deltas looking for Type=Generation with the matching Resource.
    """
    std = _get_std(item)
    rn = std.get("ResourceNetwork") or {}
    for state in (rn.get("States") or []):
        for delta in (state.get("Deltas") or []):
            dtype    = delta.get("Type") or delta.get("type") or ""
            dresource = delta.get("Resource") or delta.get("resource") or ""
            if dtype == "Generation" and dresource == resource:
                return delta.get("Rate") or delta.get("GeneratedRate")
            # Conversion: Resource consumed, GeneratedResource produced
            if dtype == "Conversion" and (delta.get("GeneratedResource") or "") == resource:
                return delta.get("GeneratedRate")
    return None


def _rn_usage(item: dict, resource: str) -> float | None:
    """Extract ResourceNetwork consumption rate for a given resource type.

    Walks all state Deltas looking for Consumption/Conversion that consumes the resource.
    """
    std = _get_std(item)
    rn = std.get("ResourceNetwork") or {}
    for state in (rn.get("States") or []):
        for delta in (state.get("Deltas") or []):
            dtype    = delta.get("Type") or delta.get("type") or ""
            dresource = delta.get("Resource") or delta.get("resource") or ""
            if dtype in ("Consumption", "Conversion") and dresource == resource:
                return delta.get("Rate")
    return None


def _turret_summary(turrets: list) -> str:
    """Summarise a list of turret dicts as e.g. '2× S5, 1× S3'."""
    if not turrets:
        return ""
    size_counts: dict[int, int] = {}
    for t in turrets:
        sz = t.get("MaxSizeClass") or t.get("Size") or t.get("size") or 0
        try:
            sz = int(sz)
        except (TypeError, ValueError):
            sz = 0
        size_counts[sz] = size_counts.get(sz, 0) + 1
    parts = []
    for sz in sorted(size_counts, reverse=True):
        label = f"S{sz}" if sz else "?"
        count = size_counts[sz]
        parts.append(f"{count}× {label}")
    return ", ".join(parts)


def stats_ship(ship: dict) -> str:
    fc = ship.get("FlightCharacteristics") or {}
    qt = ship.get("QuantumTravel") or {}

    scm     = fc.get("ScmSpeed")
    max_spd = fc.get("MaxSpeed")
    pitch   = fc.get("Pitch")
    yaw     = fc.get("Yaw")
    roll    = fc.get("Roll")

    cargo   = ship.get("Cargo")
    crew    = ship.get("Crew")
    length  = ship.get("Length")
    mass    = ship.get("MassTotal") or ship.get("Mass")
    shields = ship.get("ShieldHp")

    qt_speed = qt.get("Speed")
    qt_range = qt.get("Range")

    # Hardpoints
    manned_turrets  = ship.get("MannedTurrets")  or []
    remote_turrets  = ship.get("RemoteTurrets")  or []
    wep_defensive   = ship.get("WeaponDefensive") or {}
    countermeasures = wep_defensive.get("CountermeasureLauncher")

    lines = []
    # Flight
    if scm is not None or max_spd is not None:
        lines.append(f"SCM Speed: {_fmt(scm, ' m/s')}  |  Max Speed: {_fmt(max_spd, ' m/s')}")
    if pitch is not None:
        lines.append(f"Pitch: {_fmt(pitch, '°/s')}  |  Yaw: {_fmt(yaw, '°/s')}  |  Roll: {_fmt(roll, '°/s')}")
    # Dimensions / crew
    if length is not None or crew is not None:
        lines.append(f"Length: {_fmt(length, ' m')}  |  Crew: {_fmt(crew)}")
    # Cargo / shields / mass
    parts = []
    if cargo is not None:
        parts.append(f"Cargo: {_fmt(cargo, ' SCU')}")
    if shields is not None:
        parts.append(f"Shields: {_fmt(shields, ' HP')}")
    if mass is not None:
        parts.append(f"Mass: {_fmt(mass, ' kg')}")
    if parts:
        lines.append("  |  ".join(parts))
    # Quantum travel (no spool — not meaningful without context)
    if qt_speed is not None:
        qt_speed_mm = float(qt_speed) / 1_000_000
        lines.append(f"QT Speed: {qt_speed_mm:,.0f} Mm/s")
    if qt_range is not None:
        qt_range_gm = float(qt_range) / 1_000_000
        lines.append(f"QT Range: {qt_range_gm:,.1f} Gm")
    # Hardpoints
    turret_parts = []
    if manned_turrets:
        turret_parts.append(f"Manned Turrets: {_turret_summary(manned_turrets)}")
    if remote_turrets:
        turret_parts.append(f"Remote Turrets: {_turret_summary(remote_turrets)}")
    if turret_parts:
        lines.append("  |  ".join(turret_parts))
    if countermeasures is not None:
        lines.append(f"Countermeasures: {_fmt(countermeasures)}")

    return "\\n".join(lines)


def stats_shield(item: dict) -> str:
    std  = _get_std(item)
    shld = std.get("Shield") or {}
    hp      = shld.get("MaxShieldHealth")
    regen   = shld.get("MaxShieldRegen")
    downed  = shld.get("DownedDelay")
    damaged = shld.get("DamagedDelay")
    pwr     = _rn_usage(item, "Power")

    lines = []
    if hp is not None or regen is not None:
        lines.append(f"Max HP: {_fmt(hp)}  |  Regen: {_fmt(regen, ' HP/s')}")
    delays = []
    if downed  is not None: delays.append(f"Downed Delay: {_fmt(downed, 's', 1)}")
    if damaged is not None: delays.append(f"Damaged Delay: {_fmt(damaged, 's', 1)}")
    if delays:
        lines.append("  |  ".join(delays))
    if pwr is not None:
        lines.append(f"Power Draw: {_fmt(pwr, '/s')}")
    return "\\n".join(lines)


def stats_cooler(item: dict) -> str:
    std     = _get_std(item)
    cooling = _rn_generation(item, "Coolant")
    pwr     = _rn_usage(item, "Power")
    em_max  = ((std.get("Emission") or {}).get("Em") or {}).get("Maximum")
    ir      = (std.get("Emission") or {}).get("Ir")

    lines = []
    if cooling is not None:
        lines.append(f"Cooling Rate: {_fmt(cooling, '/s')}")
    if pwr is not None:
        lines.append(f"Power Draw: {_fmt(pwr, '/s')}")
    sigs = []
    if em_max is not None: sigs.append(f"EM: {_fmt(em_max)}")
    if ir     is not None: sigs.append(f"IR: {_fmt(ir)}")
    if sigs:
        lines.append("Signatures:  " + "  |  ".join(sigs))
    return "\\n".join(lines)


def stats_powerplant(item: dict) -> str:
    std     = _get_std(item)
    pwr_gen = _rn_generation(item, "Power")
    em_max  = ((std.get("Emission") or {}).get("Em") or {}).get("Maximum")
    cooling = _rn_usage(item, "Coolant")

    lines = []
    if pwr_gen is not None:
        lines.append(f"Power Output: {_fmt(pwr_gen, '/s')}")
    if cooling is not None:
        lines.append(f"Cooling Draw: {_fmt(cooling, '/s')}")
    if em_max is not None:
        lines.append(f"EM Signature: {_fmt(em_max)}")
    return "\\n".join(lines)


def stats_quantum_drive(item: dict) -> str:
    std      = _get_std(item)
    qd       = std.get("QuantumDrive") or {}
    jump     = qd.get("StandardJump") or {}
    speed    = jump.get("DriveSpeed")
    spool    = jump.get("SpoolUpTime")
    fuel_req = qd.get("QuantumFuelRequirement")
    fuel_eff = qd.get("FuelEfficiencyGMPerSCU")
    pwr      = _rn_usage(item, "Power")

    lines = []
    if speed is not None:
        speed_mm = float(speed) / 1_000_000
        lines.append(f"QT Speed: {speed_mm:,.0f} Mm/s  |  Spool: {_fmt(spool, 's')}")
    if fuel_req is not None:
        lines.append(f"Fuel/Gm: {fuel_req:.4f}")
    if fuel_eff is not None:
        lines.append(f"Efficiency: {_fmt(fuel_eff, ' Gm/SCU', 2)}")
    if pwr is not None:
        lines.append(f"Power Draw: {_fmt(pwr, '/s')}")
    return "\\n".join(lines)


def stats_ship_weapon(item: dict) -> str:
    """Ship weapon (WeaponGun / Missile / Bomb) stats."""
    std   = _get_std(item)
    wep   = std.get("Weapon") or {}
    modes = wep.get("Modes") or []

    rof       = wep.get("RateOfFire")
    capacity  = wep.get("Capacity")
    dmg       = wep.get("Damage") or {}
    alpha     = dmg.get("AlphaTotal")
    dps       = dmg.get("DpsTotal")
    pwr       = _rn_usage(item, "Power")
    health    = (std.get("Durability") or {}).get("Health")

    mode_labels = [m.get("LocalisedName") or m.get("Name") for m in modes
                   if m.get("LocalisedName") or m.get("Name")]

    lines = []
    if rof is not None:
        lines.append(f"Fire Rate: {_fmt(rof, ' RPM')}")
    if mode_labels:
        lines.append(f"Fire Modes: {' / '.join(mode_labels)}")
    if alpha is not None or dps is not None:
        parts = []
        if alpha is not None: parts.append(f"Dmg/Shot: {_fmt(alpha, '', 1)}")
        if dps   is not None: parts.append(f"DPS: {_fmt(dps, '', 1)}")
        lines.append("  |  ".join(parts))
    if capacity is not None:
        lines.append(f"Ammo Capacity: {_fmt(capacity)}")
    if pwr is not None:
        lines.append(f"Power Draw: {_fmt(pwr, '/s')}")
    if health is not None:
        lines.append(f"Health: {_fmt(health)}")
    return "\\n".join(lines)


def stats_fps_weapon(item: dict) -> str:
    """FPS personal weapon stats."""
    std  = _get_std(item)
    wep  = std.get("Weapon") or {}
    modes = wep.get("Modes") or []

    rof         = wep.get("RateOfFire")      # primary fire mode RPM
    capacity    = wep.get("Capacity")        # magazine size
    eff_range   = wep.get("EffectiveRange")
    dmg         = wep.get("Damage") or {}
    alpha       = dmg.get("AlphaTotal")      # damage per shot
    dps         = dmg.get("DpsTotal")        # damage per second
    health      = (std.get("Durability") or {}).get("Health")

    # Fire mode names from Modes list
    mode_labels = [m.get("LocalisedName") or m.get("Name") for m in modes
                   if m.get("LocalisedName") or m.get("Name")]

    lines = []
    if rof is not None:
        lines.append(f"Fire Rate: {_fmt(rof, ' RPM')}")
    if mode_labels:
        lines.append(f"Fire Modes: {' / '.join(mode_labels)}")
    if alpha is not None or dps is not None:
        parts = []
        if alpha is not None: parts.append(f"Dmg/Shot: {_fmt(alpha, '', 1)}")
        if dps   is not None: parts.append(f"DPS: {_fmt(dps, '', 1)}")
        lines.append("  |  ".join(parts))
    if capacity is not None:
        lines.append(f"Magazine: {_fmt(capacity)}")
    if eff_range is not None:
        lines.append(f"Effective Range: {_fmt(eff_range, ' m')}")
    if health is not None:
        lines.append(f"Durability: {_fmt(health)}")
    return "\\n".join(lines)


# ── INI writer ───────────────────────────────────────────────────────────────

STAT_SEPARATOR = "\\n\\n<EM4>== Stats ==</EM4>\\n"


def append_stats(existing_value: str, stats_block: str) -> str:
    """Append stats_block after existing description, avoiding duplicates."""
    if not stats_block:
        return existing_value
    separator_marker = "== Stats =="
    if separator_marker in existing_value:
        # Replace existing stats block entirely
        existing_value = existing_value[:existing_value.index("\\n\\n<EM4>== Stats ==")]
    return existing_value + STAT_SEPARATOR + stats_block


def write_ini(path: Path, entries: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={v}" for k, v in sorted(entries.items())]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Written {len(entries):,} entries -> {path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main(base_ini_path: Path) -> None:
    print("\n=== SC Stats INI Generator ===\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load scunpacked data ──────────────────────────────────────────────────
    print("Loading ships.json...")
    ships_raw: list = load_json("ships")

    print("Loading ship-items.json...")
    ship_items_raw: list = load_json("ship_items")

    print("Loading fps-items.json...")
    fps_items_raw: list = load_json("fps_items")

    # ── Parse base.ini ────────────────────────────────────────────────────────
    print(f"\nParsing base.ini: {base_ini_path}")
    if not base_ini_path.exists():
        print(f"ERROR: base.ini not found at {base_ini_path}")
        sys.exit(1)
    loc = parse_ini(base_ini_path)
    print(f"  Loaded {len(loc):,} localization keys")

    # ── Build lookups ─────────────────────────────────────────────────────────
    print("\nBuilding lookups...")

    ships_lookup      = build_lookup(ships_raw)
    ship_items_lookup = build_lookup(ship_items_raw)
    fps_items_lookup  = build_lookup(fps_items_raw)

    # ── Bucket ship items by type ─────────────────────────────────────────────
    SHIP_ITEM_TYPES = {
        "Shield":          (stats_shield,       "components"),
        "Cooler":          (stats_cooler,       "components"),
        "PowerPlant":      (stats_powerplant,   "components"),
        "QuantumDrive":    (stats_quantum_drive,"components"),
        "WeaponGun":       (stats_ship_weapon,  "ship_weapons"),
        "Missile":         (stats_ship_weapon,  "ship_weapons"),
        "Bomb":            (stats_ship_weapon,  "ship_weapons"),
    }

    item_by_type: dict[str, dict] = {}  # type → lookup dict
    for item in ship_items_raw:
        itype = item.get("Type") or item.get("type") or ""
        if itype in SHIP_ITEM_TYPES:
            cls  = (item.get("ClassName") or item.get("className") or "")
            name = (item.get("Name")      or item.get("name")      or "").lower().strip()
            if itype not in item_by_type:
                item_by_type[itype] = {"class": {}, "name": {}}
            if cls:
                item_by_type[itype]["class"][_normalize_classname(cls).lower()] = item
            if name:
                item_by_type[itype]["name"][name] = item

    fps_lookup = build_lookup([i for i in fps_items_raw if (i.get("Type") or i.get("type")) == "WeaponPersonal"])

    # ── Process each category ─────────────────────────────────────────────────
    out_ships      : dict[str, str] = {}
    out_components : dict[str, str] = {}
    out_ship_weapons: dict[str, str] = {}
    out_fps_weapons : dict[str, str] = {}

    matched_ships = missed_ships = 0
    matched_comp  = missed_comp  = 0
    matched_sw    = missed_sw    = 0
    matched_fps   = missed_fps   = 0

    for key, value in loc.items():
        # ── Ships ──────────────────────────────────────────────────────────────
        if key.startswith("vehicle_Desc"):
            bare = key.split(",")[0][len("vehicle_Desc"):].lower()
            rec  = ships_lookup["class"].get(bare)
            if not rec:
                # Fallback: match via vehicle_Name* display value
                name_key = "vehicle_Name" + key.split(",")[0][len("vehicle_Desc"):]
                display  = loc.get(name_key, "").lower().strip()
                if display:
                    rec = ships_lookup["name"].get(display)
            if rec:
                stats = stats_ship(rec)
                if stats:
                    out_ships[key] = append_stats(value, stats)
                    matched_ships += 1
            else:
                missed_ships += 1

        # ── Components & ship weapons ─────────────────────────────────────────
        elif key.startswith("item_Desc"):
            bare = key.split(",")[0][len("item_Desc"):].lower()
            matched = False
            for itype, (stat_fn, bucket) in SHIP_ITEM_TYPES.items():
                lookup = item_by_type.get(itype, {"class": {}, "name": {}})
                rec = lookup["class"].get(bare)
                if not rec:
                    name_key = "item_Name" + key.split(",")[0][len("item_Desc"):]
                    display  = loc.get(name_key, "").lower().strip()
                    if display:
                        rec = lookup["name"].get(display)
                if rec:
                    stats = stat_fn(rec)
                    if stats:
                        entry = append_stats(value, stats)
                        if bucket == "components":
                            out_components[key]  = entry
                            matched_comp  += 1
                        else:
                            out_ship_weapons[key] = entry
                            matched_sw    += 1
                    matched = True
                    break
            if not matched:
                # Try FPS weapons
                rec = fps_lookup["class"].get(bare)
                if not rec:
                    name_key = "item_Name" + key.split(",")[0][len("item_Desc"):]
                    display  = loc.get(name_key, "").lower().strip()
                    if display:
                        rec = fps_lookup["name"].get(display)
                if rec:
                    stats = stats_fps_weapon(rec)
                    if stats:
                        out_fps_weapons[key] = append_stats(value, stats)
                        matched_fps += 1
                else:
                    missed_comp += 1

    # ── Write output ──────────────────────────────────────────────────────────
    print("\nWriting output files...")
    write_ini(OUTPUT_DIR / "ships_desc_stats.ini",       out_ships)
    write_ini(OUTPUT_DIR / "components_desc_stats.ini",  out_components)
    write_ini(OUTPUT_DIR / "ship_weapons_desc_stats.ini",out_ship_weapons)
    write_ini(OUTPUT_DIR / "fps_weapons_desc_stats.ini", out_fps_weapons)

    print(f"""
Results:
  Ships:         {matched_ships:,} matched  ({missed_ships:,} unmatched)
  Components:    {matched_comp:,} matched
  Ship Weapons:  {matched_sw:,} matched
  FPS Weapons:   {matched_fps:,} matched

Output: {OUTPUT_DIR}
""")


if __name__ == "__main__":
    base_ini = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BASE_INI
    main(base_ini)
