"""
generate_stats_ini.py
─────────────────────
Generates stats-augmented INI files for use as additional sources in
SC Localization Editor.

Component / weapon stats are sourced directly from the game's DataForge
entity XML files (extracted from Data.p4k via unforge).  Ship flight stats
(SCM speed, cargo, etc.) still come from the scunpacked-data JSON until
a full DataForge-based ship parser is implemented.

Output files (written to OUTPUT_DIR / cache):
  ships_desc_stats.ini        – vehicle_Desc* entries with flight/cargo/shield stats
  components_desc_stats.ini   – item_Desc* COOL/SHLD/POWR/QDRV with numerical stats
  ship_weapons_desc_stats.ini – item_Desc* ship weapon stats
  fps_weapons_desc_stats.ini  – item_Desc* FPS weapon stats

Usage:
  python scripts/generate_stats_ini.py [base_ini_path [dataforge_cache_dir]]
"""

import os
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

# ── Paths ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent


def _get_documents_dir() -> Path:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        )
        docs = Path(winreg.QueryValueEx(key, "Personal")[0])
        winreg.CloseKey(key)
        return docs
    except Exception:
        return Path.home() / "Documents"


APP_CACHE_DIR    = _get_documents_dir() / "SC Localization Editor" / "cache"
DEFAULT_BASE_INI = APP_CACHE_DIR / "base.ini"
DEFAULT_FORGE_DIR = APP_CACHE_DIR / "dataforge"

OUTPUT_DIR  = APP_CACHE_DIR
# JSON cache for ships (still scunpacked-based)
SHIPS_CACHE_DIR = APP_CACHE_DIR / "stats_cache"

SHIPS_JSON_URL = "https://raw.githubusercontent.com/StarCitizenWiki/scunpacked-data/master/ships.json"


# ── Download helper (ships.json only) ─────────────────────────────────────────

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


def load_ships_json() -> list:
    dest = SHIPS_CACHE_DIR / "ships.json"
    if not dest.exists():
        download(SHIPS_JSON_URL, dest)
    else:
        print(f"  Using cached {dest.name}")
    return json.loads(dest.read_text(encoding="utf-8"))


# ── INI helpers ───────────────────────────────────────────────────────────────

def parse_ini(path: Path) -> dict[str, str]:
    result = {}
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line.strip() or line.strip().startswith(";"):
                continue
            if "=" not in line:
                continue
            k, _, v = line.partition("=")
            lookup_key = k.strip().split(",")[0].strip()
            if lookup_key:
                result[lookup_key] = v.strip()
    return result


def write_ini(path: Path, entries: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={v}" for k, v in sorted(entries.items())]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Written {len(entries):,} entries → {path}")


STAT_SEPARATOR = "\\n\\n== Stats ==\\n"


def append_stats(existing_value: str, stats_block: str) -> str:
    if not stats_block:
        return existing_value
    if "== Stats ==" in existing_value:
        existing_value = existing_value[:existing_value.index("\\n\\n== Stats ==")]
    return existing_value + STAT_SEPARATOR + stats_block


# ── Stat formatters ───────────────────────────────────────────────────────────

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


# ── XML parsing helpers ───────────────────────────────────────────────────────

def _find(root: ET.Element, tag: str) -> ET.Element | None:
    """Find first element with the given tag anywhere in the tree."""
    return root.find(f".//{tag}")


def _attr(root: ET.Element, tag: str, attr: str, default=None):
    el = _find(root, tag)
    return el.get(attr, default) if el is not None else default


def _loc_key(root: ET.Element) -> str | None:
    """Extract the item_Desc* localization key from the entity XML."""
    for el in root.iter("Localization"):
        desc = el.get("Description", "")
        if desc.startswith("@") and "LOC_EMPTY" not in desc and "UNINITIALIZED" not in desc:
            return desc.lstrip("@")
    return None


def _resource_amount(amount_el: ET.Element) -> str | None:
    """Extract the numeric value from a resourceAmountPerSecond element."""
    unit = amount_el.find(".//SPowerSegmentResourceUnit")
    if unit is not None:
        return unit.get("units")
    std = amount_el.find(".//SStandardResourceUnit")
    if std is not None:
        return std.get("standardResourceUnits")
    return None


def _find_resource(root: ET.Element, resource: str) -> str | None:
    """
    Find the amount/s for a given resource anywhere in the resource network,
    searching both Generation and Conversion delta types.

    For Conversion deltas, checks both <consumption> and <generation> children.
    """
    for delta_type in ("ItemResourceDeltaGeneration", "ItemResourceDeltaConversion"):
        for delta in root.iter(delta_type):
            for child in delta:
                if child.get("resource") == resource:
                    val = _resource_amount(child)
                    if val is not None:
                        return val
    return None


def _fire_rate(root: ET.Element) -> str | None:
    """Return the highest fire rate found across all weapon fire actions."""
    best = None
    for el in root.iter():
        if "WeaponActionFire" in el.tag:
            fr = el.get("fireRate")
            if fr:
                try:
                    v = float(fr)
                    if best is None or v > best:
                        best = v
                except ValueError:
                    pass
    return str(best) if best else None


def _fire_modes(root: ET.Element) -> list[str]:
    names = []
    for el in root.iter():
        if "WeaponActionFire" in el.tag:
            n = el.get("name") or el.get("localisedName")
            if n and n not in names:
                names.append(n)
    return names


def _ammo_damage(ammo_root: ET.Element) -> float:
    """Sum all damage types from the ammo's DamageInfo element."""
    total = 0.0
    for info in ammo_root.iter("DamageInfo"):
        for attr in ("DamagePhysical", "DamageEnergy", "DamageDistortion",
                     "DamageThermal", "DamageBiochemical", "DamageStun"):
            try:
                total += float(info.get(attr, 0))
            except ValueError:
                pass
    return total


# ── Per-type stat generators ──────────────────────────────────────────────────

def stats_shield(root: ET.Element) -> str:
    el = _find(root, "SCItemShieldGeneratorParams")
    if el is None:
        return ""
    hp      = el.get("MaxShieldHealth")
    regen   = el.get("MaxShieldRegen")
    downed  = el.get("DownedRegenDelay")
    damaged = el.get("DamagedRegenDelay")
    pwr     = _find_resource(root, "Power")

    lines = []
    if hp is not None or regen is not None:
        lines.append(f"Max HP: {_fmt(hp)}  |  Regen: {_fmt(regen, ' HP/s')}")
    delays = []
    if downed  is not None: delays.append(f"Downed Delay: {_fmt(downed, 's', 1)}")
    if damaged is not None: delays.append(f"Damaged Delay: {_fmt(damaged, 's', 1)}")
    if delays:
        lines.append("  |  ".join(delays))
    if pwr is not None:
        lines.append(f"Power Draw: {_fmt(pwr, ' PU/s')}")
    return "\\n".join(lines)


def stats_cooler(root: ET.Element) -> str:
    cooling = _find_resource(root, "Coolant")
    pwr     = _find_resource(root, "Power")

    lines = []
    if cooling is not None:
        lines.append(f"Cooling Rate: {_fmt(cooling, ' CR/s')}")
    if pwr is not None:
        lines.append(f"Power Draw: {_fmt(pwr, ' PU/s')}")
    return "\\n".join(lines)


def stats_powerplant(root: ET.Element) -> str:
    gen          = _find_resource(root, "Power")
    cooling_draw = _find_resource(root, "Coolant")

    lines = []
    if gen is not None:
        lines.append(f"Power Output: {_fmt(gen, ' PU/s')}")
    if cooling_draw is not None:
        lines.append(f"Cooling Draw: {_fmt(cooling_draw, ' CR/s')}")
    return "\\n".join(lines)


def stats_quantum_drive(root: ET.Element) -> str:
    qd = _find(root, "SCItemQuantumDriveParams")
    if qd is None:
        return ""
    fuel_req = qd.get("quantumFuelRequirement")

    params = _find(root, "SQuantumDriveParams")
    speed  = params.get("driveSpeed")  if params is not None else None
    spool  = params.get("spoolUpTime") if params is not None else None

    pwr = _find_resource(root, "Power")

    lines = []
    if speed is not None:
        speed_mm = float(speed) / 1_000_000
        spool_str = _fmt(spool, "s") if spool else "?"
        lines.append(f"QT Speed: {speed_mm:,.0f} Mm/s  |  Spool: {spool_str}")
    if fuel_req is not None:
        lines.append(f"Fuel/Gm: {float(fuel_req):.4f}")
    if pwr is not None:
        lines.append(f"Power Draw: {_fmt(pwr, ' PU/s')}")
    return "\\n".join(lines)


def stats_weapon(root: ET.Element, ammo_lookup: dict[str, ET.Element]) -> str:
    """Ship or FPS weapon stats."""
    fr    = _fire_rate(root)
    modes = _fire_modes(root)
    pwr   = _power_units(root, "Power", "ItemResourceDeltaConversion")

    # Ammo damage — look up the ammo record by GUID
    ammo_container = _find(root, "SAmmoContainerComponentParams")
    ammo_record_id = ammo_container.get("ammoParamsRecord") if ammo_container is not None else None
    ammo_damage = None
    dps = None
    if ammo_record_id and ammo_record_id != "00000000-0000-0000-0000-000000000000":
        ammo_root = ammo_lookup.get(ammo_record_id)
        if ammo_root is not None:
            ammo_damage = _ammo_damage(ammo_root)
            if ammo_damage and fr:
                try:
                    dps = ammo_damage * float(fr) / 60.0
                except ValueError:
                    pass

    # Capacity from regen consumer or ammo container
    regen = _find(root, "SWeaponRegenConsumerParams")
    capacity = None
    if regen is not None:
        capacity = regen.get("maxAmmoLoad")

    lines = []
    if fr:
        lines.append(f"Fire Rate: {_fmt(fr, ' RPM')}")
    if modes:
        lines.append(f"Fire Modes: {' / '.join(modes)}")
    if ammo_damage is not None or dps is not None:
        parts = []
        if ammo_damage: parts.append(f"Dmg/Shot: {_fmt(ammo_damage, '', 1)}")
        if dps:         parts.append(f"DPS: {_fmt(dps, '', 1)}")
        lines.append("  |  ".join(parts))
    if capacity:
        lines.append(f"Ammo: {_fmt(capacity)}")
    if pwr:
        lines.append(f"Power Draw: {_fmt(pwr, ' PU/s')}")
    return "\\n".join(lines)


# ── Ship stats (scunpacked-based, kept until DataForge parser covers it) ──────

def _normalize_classname(cls: str) -> str:
    return cls.removesuffix("_SCItem")


def _fmt_ship(value, unit="", decimals=0) -> str:
    return _fmt(value, unit, decimals)


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

    manned_turrets  = ship.get("MannedTurrets")  or []
    remote_turrets  = ship.get("RemoteTurrets")  or []
    wep_defensive   = ship.get("WeaponDefensive") or {}
    countermeasures = wep_defensive.get("CountermeasureLauncher")

    def turret_summary(turrets):
        size_counts: dict[int, int] = {}
        for t in turrets:
            sz = t.get("MaxSizeClass") or t.get("Size") or t.get("size") or 0
            try: sz = int(sz)
            except: sz = 0
            size_counts[sz] = size_counts.get(sz, 0) + 1
        return ", ".join(
            f"{cnt}× S{sz}" if sz else f"{cnt}× ?"
            for sz, cnt in sorted(size_counts.items(), reverse=True)
        )

    lines = []
    if scm is not None or max_spd is not None:
        lines.append(f"SCM Speed: {_fmt_ship(scm, ' m/s')}  |  Max Speed: {_fmt_ship(max_spd, ' m/s')}")
    if pitch is not None:
        lines.append(f"Pitch: {_fmt_ship(pitch, '°/s')}  |  Yaw: {_fmt_ship(yaw, '°/s')}  |  Roll: {_fmt_ship(roll, '°/s')}")
    if length is not None or crew is not None:
        lines.append(f"Length: {_fmt_ship(length, ' m')}  |  Crew: {_fmt_ship(crew)}")
    parts = []
    if cargo   is not None: parts.append(f"Cargo: {_fmt_ship(cargo, ' SCU')}")
    if shields is not None: parts.append(f"Shields: {_fmt_ship(shields, ' HP')}")
    if mass    is not None: parts.append(f"Mass: {_fmt_ship(mass, ' kg')}")
    if parts: lines.append("  |  ".join(parts))
    if qt_speed is not None:
        lines.append(f"QT Speed: {float(qt_speed) / 1_000_000:,.0f} Mm/s")
    if qt_range is not None:
        lines.append(f"QT Range: {float(qt_range) / 1_000_000:,.1f} Gm")
    turret_parts = []
    if manned_turrets: turret_parts.append(f"Manned Turrets: {turret_summary(manned_turrets)}")
    if remote_turrets: turret_parts.append(f"Remote Turrets: {turret_summary(remote_turrets)}")
    if turret_parts: lines.append("  |  ".join(turret_parts))
    if countermeasures is not None:
        lines.append(f"Countermeasures: {_fmt_ship(countermeasures)}")
    return "\\n".join(lines)


# ── Ammo lookup builder ───────────────────────────────────────────────────────

def build_ammo_lookup(ammo_dir: Path) -> dict[str, ET.Element]:
    """Parse all ammo XML files and index them by their __ref GUID."""
    lookup: dict[str, ET.Element] = {}
    if not ammo_dir.exists():
        return lookup
    for xml_file in ammo_dir.rglob("*.xml"):
        try:
            root = ET.parse(xml_file).getroot()
            ref = root.get("__ref")
            if ref:
                lookup[ref] = root
        except ET.ParseError:
            pass
    return lookup


# ── DataForge directory scanner ───────────────────────────────────────────────

def scan_entity_dir(
    entity_dir: Path,
    stat_fn,
    ammo_lookup: dict | None = None,
    loc: dict | None = None,
) -> dict[str, str]:
    """
    Scan all XML files in entity_dir, extract localization key + stats,
    and return {loc_key: augmented_value} for keys found in `loc`.

    ammo_lookup is passed to stat_fn only when it accepts it (weapons).
    loc is the base.ini localization dict for value lookup.
    """
    out: dict[str, str] = {}
    matched = missed = skipped = 0

    for xml_file in entity_dir.rglob("*.xml"):
        try:
            root = ET.parse(xml_file).getroot()
        except ET.ParseError:
            continue

        key = _loc_key(root)
        if not key:
            skipped += 1
            continue

        base_value = (loc or {}).get(key)
        if base_value is None:
            missed += 1
            continue

        try:
            if ammo_lookup is not None:
                stats_block = stat_fn(root, ammo_lookup)
            else:
                stats_block = stat_fn(root)
        except Exception as e:
            print(f"  Warning: stats failed for {xml_file.name}: {e}")
            continue

        if stats_block:
            out[key] = append_stats(base_value, stats_block)
            matched += 1
        else:
            missed += 1

    print(f"    {entity_dir.name}: {matched} matched, {missed} no stats, {skipped} no loc key")
    return out


# ── Main ──────────────────────────────────────────────────────────────────────

def main(base_ini_path: Path, forge_dir: Path | None = None) -> None:
    print("\n=== SC Stats INI Generator (DataForge edition) ===\n")

    if forge_dir is None:
        forge_dir = DEFAULT_FORGE_DIR

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Parse base.ini ─────────────────────────────────────────────────────────
    print(f"Parsing base.ini: {base_ini_path}")
    if not base_ini_path.exists():
        print(f"ERROR: base.ini not found at {base_ini_path}")
        sys.exit(1)
    loc = parse_ini(base_ini_path)
    print(f"  Loaded {len(loc):,} localization keys\n")

    # ── Check DataForge cache ─────────────────────────────────────────────────
    records = forge_dir / "libs" / "foundry" / "records"
    if not forge_dir.exists() or not records.exists():
        print(f"ERROR: DataForge cache not found at {forge_dir}")
        print("  Run 'Extract DataForge' in the app first (Config tab → Stats section).")
        sys.exit(1)

    # ── Build ammo lookups ────────────────────────────────────────────────────
    print("Building ammo damage lookups…")
    vehicle_ammo = build_ammo_lookup(records / "ammoparams" / "vehicle")
    fps_ammo     = build_ammo_lookup(records / "ammoparams" / "fps")
    print(f"  Vehicle ammo: {len(vehicle_ammo)} records")
    print(f"  FPS ammo:     {len(fps_ammo)} records\n")

    # ── Process components ────────────────────────────────────────────────────
    ships_scitem = records / "entities" / "scitem" / "ships"

    print("Processing ship components…")
    out_components: dict[str, str] = {}
    for subdir, fn in [
        ("shieldgenerator", stats_shield),
        ("cooler",          stats_cooler),
        ("powerplant",      stats_powerplant),
        ("quantumdrive",    stats_quantum_drive),
    ]:
        out_components.update(scan_entity_dir(ships_scitem / subdir, fn, loc=loc))

    # ── Process ship weapons ──────────────────────────────────────────────────
    print("\nProcessing ship weapons…")
    out_ship_weapons: dict[str, str] = {}
    weapons_dir = ships_scitem / "weapons"
    if weapons_dir.exists():
        out_ship_weapons = scan_entity_dir(
            weapons_dir,
            lambda root: stats_weapon(root, vehicle_ammo),
            loc=loc,
        )

    # ── Process FPS weapons ───────────────────────────────────────────────────
    print("\nProcessing FPS weapons…")
    out_fps_weapons: dict[str, str] = {}
    fps_dir = records / "entities" / "scitem" / "weapons" / "fps_weapons"
    if fps_dir.exists():
        out_fps_weapons = scan_entity_dir(
            fps_dir,
            lambda root: stats_weapon(root, fps_ammo),
            loc=loc,
        )

    # ── Process ships (scunpacked-based) ──────────────────────────────────────
    print("\nLoading ships.json (scunpacked-data)…")
    SHIPS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ships_raw = load_ships_json()
    ships_by_class: dict[str, dict] = {}
    ships_by_name:  dict[str, dict] = {}
    for s in ships_raw:
        cls  = (s.get("ClassName") or s.get("className") or "")
        name = (s.get("Name")      or s.get("name")      or "").lower().strip()
        if cls:  ships_by_class[_normalize_classname(cls).lower()] = s
        if name: ships_by_name[name] = s

    print("Processing ship descriptions…")
    out_ships: dict[str, str] = {}
    matched_ships = missed_ships = 0
    for key, value in loc.items():
        if not key.startswith("vehicle_Desc"):
            continue
        bare = key.split(",")[0][len("vehicle_Desc"):].lower()
        rec  = ships_by_class.get(bare)
        if not rec:
            name_key = "vehicle_Name" + key.split(",")[0][len("vehicle_Desc"):]
            display  = loc.get(name_key, "").lower().strip()
            if display:
                rec = ships_by_name.get(display)
        if rec:
            block = stats_ship(rec)
            if block:
                out_ships[key] = append_stats(value, block)
                matched_ships += 1
        else:
            missed_ships += 1
    print(f"  Ships: {matched_ships} matched, {missed_ships} unmatched")

    # ── Write output ──────────────────────────────────────────────────────────
    print("\nWriting output files…")
    write_ini(OUTPUT_DIR / "ships_desc_stats.ini",       out_ships)
    write_ini(OUTPUT_DIR / "components_desc_stats.ini",  out_components)
    write_ini(OUTPUT_DIR / "ship_weapons_desc_stats.ini",out_ship_weapons)
    write_ini(OUTPUT_DIR / "fps_weapons_desc_stats.ini", out_fps_weapons)

    total = len(out_ships) + len(out_components) + len(out_ship_weapons) + len(out_fps_weapons)
    print(f"\nDone — {total:,} total stat entries written to {OUTPUT_DIR}\n")


if __name__ == "__main__":
    base_ini  = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BASE_INI
    forge_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_FORGE_DIR
    main(base_ini, forge_dir)
