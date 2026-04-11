"""
generate_stats_ini.py
─────────────────────
Generates stats-augmented INI files for use as additional sources in
SC Localization Editor.

All stats are sourced directly from the game's DataForge entity XML files
(extracted from Data.p4k via unp4k + unforge).  No external JSON sources.

Output files (written to OUTPUT_DIR / cache):
  ships_desc_stats.ini        – vehicle_Desc* entries with flight/specs stats
  components_desc_stats.ini   – item_Desc* COOL/SHLD/POWR/QDRV with numerical stats
  ship_weapons_desc_stats.ini – item_Desc* ship weapon stats
  fps_weapons_desc_stats.ini  – item_Desc* FPS weapon stats

Usage:
  python scripts/generate_stats_ini.py [base_ini_path [dataforge_cache_dir]]
"""

import logging
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

logger = logging.getLogger(__name__)

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

OUTPUT_DIR = APP_CACHE_DIR


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
    logger.info(f"Written {len(entries):,} entries -> {path}")


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


def _find_by_type(root: ET.Element, type_name: str) -> ET.Element | None:
    """Find first element with __type attribute matching type_name (DataForge inline structs)."""
    for el in root.iter():
        if el.get("__type") == type_name:
            return el
    return None


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
    micro = amount_el.find(".//SMicroResourceUnit")
    if micro is not None:
        return micro.get("microResourceUnits")
    return None


def _find_resource(root: ET.Element, resource: str) -> str | None:
    """
    Find the amount/s for a given resource anywhere in the resource network,
    searching both Generation and Conversion delta types.

    For Conversion deltas, checks both <consumption> and <generation> children.
    """
    for delta_type in ("ItemResourceDeltaGeneration", "ItemResourceDeltaConversion", "ItemResourceDeltaConsumption"):
        for delta in root.iter(delta_type):
            for child in delta:
                if child.get("resource") == resource:
                    val = _resource_amount(child)
                    if val is not None:
                        return val
    return None


def _fire_rate(root: ET.Element) -> str | None:
    """Return the primary fire rate found in weapon fire actions.

    Searches in priority order:
    1. Default or primary fire mode (if marked)
    2. Highest fire rate if multiple modes exist
    """
    fire_rates = []  # List of (rate_value, is_primary)

    try:
        for el in root.iter():
            if "WeaponActionFire" in el.tag:
                fr = el.get("fireRate")
                if not fr:
                    continue

                try:
                    v = float(fr)
                    if v <= 0:
                        continue

                    # Check if this is marked as default/primary
                    is_default = el.get("default") == "1" or el.get("isDefault") == "true"
                    action_type = el.get("actionType", "")
                    is_primary = (is_default or "primary" in action_type.lower())

                    fire_rates.append((v, is_primary))
                except (ValueError, TypeError):
                    pass
    except Exception:
        pass

    if not fire_rates:
        return None

    # Sort by primary first, then by rate (highest)
    fire_rates.sort(key=lambda x: (-int(x[1]), -x[0]))
    return str(fire_rates[0][0])


def _fire_modes(root: ET.Element, loc: dict | None = None) -> list[str]:
    names = []
    for el in root.iter():
        if "WeaponActionFire" in el.tag:
            loc_key = el.get("localisedName", "")
            if loc_key.startswith("@") and loc is not None:
                n = loc.get(loc_key[1:]) or el.get("name", "")
            else:
                n = el.get("name") or loc_key
            if n and n not in names:
                names.append(n)
    return names


_DAMAGE_TYPES = ("DamagePhysical", "DamageEnergy", "DamageDistortion",
                 "DamageThermal", "DamageBiochemical", "DamageStun")
_DAMAGE_LABELS = {"DamagePhysical": "Phys", "DamageEnergy": "Energy",
                  "DamageDistortion": "Distort", "DamageThermal": "Thermal",
                  "DamageBiochemical": "Bio", "DamageStun": "Stun"}


def _ammo_damage(ammo_root: ET.Element) -> float:
    """Sum all damage types from the ammo's DamageInfo element."""
    total = 0.0
    for info in ammo_root.iter("DamageInfo"):
        for attr in _DAMAGE_TYPES:
            try:
                total += float(info.get(attr, 0))
            except ValueError:
                pass
    return total


def _ammo_damage_breakdown(ammo_root: ET.Element) -> tuple[float, dict]:
    """Return (total_damage, {label: amount}) for non-zero damage types."""
    totals: dict[str, float] = {}
    for info in ammo_root.iter("DamageInfo"):
        for attr in _DAMAGE_TYPES:
            try:
                v = float(info.get(attr, 0))
                if v:
                    lbl = _DAMAGE_LABELS[attr]
                    totals[lbl] = totals.get(lbl, 0.0) + v
            except ValueError:
                pass
    return sum(totals.values()), totals


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
    comp_hp = _attr(root, "SHealthComponentParams", "Health")

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
    if comp_hp is not None:
        lines.append(f"Component HP: {_fmt(comp_hp)}")
    return "\\n".join(lines)


def stats_missile(root: ET.Element) -> str:
    """Extract missile/rocket/bomb stats: velocity, guidance, seeker type, lock ranges, tracking range,
    turn rate, detonation mode, proximity fuse range, G-force, acceleration, damage, blast radius,
    effective range, EM/IR signature, and component HP."""
    lines = []

    try:
        # Primary missile params container
        for el in root.iter():
            try:
                # Missile velocity and lifetime
                if "missile" in el.tag.lower() or "projectile" in el.tag.lower():
                    velocity = el.get("speed") or el.get("velocity") or el.get("initialVelocity")
                    if velocity and velocity != "0":
                        try:
                            vel_val = float(velocity)
                            if vel_val > 0:
                                lines.append(f"Velocity: {vel_val:,.0f} m/s")
                        except (ValueError, TypeError):
                            pass

                    lifetime = el.get("lifetime") or el.get("maxLifetime") or el.get("burnTime")
                    if lifetime and lifetime != "0":
                        try:
                            life_val = float(lifetime)
                            if life_val > 0:
                                lines.append(f"Lifetime: {life_val:.2f}s")
                        except (ValueError, TypeError):
                            pass

                # Guidance and tracking parameters
                if "guidance" in el.tag.lower() or "tracking" in el.tag.lower():
                    guidance_type = el.get("guidanceType") or el.get("type") or el.tag.replace("Guidance", "").replace("Tracking", "")
                    if guidance_type and "none" not in guidance_type.lower():
                        lines.append(f"Guidance: {guidance_type}")

                    # Seeker type (passive vs active)
                    seeker_type = el.get("seekerType") or el.get("seekerMode")
                    if seeker_type and "none" not in seeker_type.lower():
                        lines.append(f"Seeker: {seeker_type}")

                    # Lock-on time (how long to acquire lock)
                    lock_time = el.get("lockTime") or el.get("lockOnTime") or el.get("lockAcquisitionTime")
                    if lock_time and lock_time != "0":
                        try:
                            time_val = float(lock_time)
                            if time_val > 0:
                                lines.append(f"Lock Time: {time_val:.2f}s")
                        except (ValueError, TypeError):
                            pass

                    # Minimum lock range
                    min_lock = el.get("minLockRange") or el.get("minimumLockRange")
                    if min_lock and min_lock != "0":
                        try:
                            min_val = float(min_lock) / 1000  # Convert to km
                            if min_val > 0:
                                lines.append(f"Min Lock Range: {min_val:,.1f} km")
                        except (ValueError, TypeError):
                            pass

                    # Maximum lock range
                    max_lock = el.get("maxLockRange") or el.get("lockOnRange") or el.get("launchRange")
                    if max_lock and max_lock != "0":
                        try:
                            max_val = float(max_lock) / 1000  # Convert to km
                            if max_val > 0:
                                lines.append(f"Max Lock Range: {max_val:,.1f} km")
                        except (ValueError, TypeError):
                            pass

                    # Tracking range (how far missile can follow locked target)
                    track_range = el.get("trackingRange") or el.get("engagementRange") or el.get("maxEngagementRange")
                    if track_range and track_range != "0":
                        try:
                            track_val = float(track_range) / 1000  # Convert to km
                            if track_val > 0:
                                lines.append(f"Tracking Range: {track_val:,.1f} km")
                        except (ValueError, TypeError):
                            pass

                    # Proximity fuse range (detonation distance from target)
                    prox_range = el.get("proximityFuseRange") or el.get("detonationRange") or el.get("fuseRange")
                    if prox_range and prox_range != "0":
                        try:
                            prox_val = float(prox_range)
                            if prox_val > 0:
                                lines.append(f"Proximity Range: {prox_val:,.0f} m")
                        except (ValueError, TypeError):
                            pass

                    # Turn rate / Max G-force for guided missiles
                    max_g = el.get("maxGForce") or el.get("maxAcceleration") or el.get("maxG")
                    if max_g and max_g != "0":
                        try:
                            g_val = float(max_g)
                            if g_val > 0:
                                lines.append(f"Max G-Force: {g_val:.1f}G")
                        except (ValueError, TypeError):
                            pass

                    turn_rate = el.get("turnRate") or el.get("maxTurnRate") or el.get("angularVelocity")
                    if turn_rate and turn_rate != "0":
                        try:
                            turn_val = float(turn_rate)
                            if turn_val > 0:
                                lines.append(f"Turn Rate: {turn_val:.1f}°/s")
                        except (ValueError, TypeError):
                            pass

                    # Detonation mode
                    detonation = el.get("detonationMode") or el.get("fuseMode") or el.get("detonationType")
                    if detonation and "none" not in detonation.lower():
                        lines.append(f"Detonation: {detonation}")

                # Acceleration / Thrust
                if "propulsion" in el.tag.lower() or "thruster" in el.tag.lower() or "engine" in el.tag.lower():
                    accel = el.get("acceleration") or el.get("maxAcceleration") or el.get("thrust")
                    if accel and accel != "0":
                        try:
                            accel_val = float(accel)
                            if accel_val > 0:
                                lines.append(f"Acceleration: {accel_val:,.1f} m/s²")
                        except (ValueError, TypeError):
                            pass

                # Fuel/propellant for rockets and missiles
                if "propellant" in el.tag.lower() or "fuel" in el.tag.lower():
                    fuel_amount = el.get("amount") or el.get("fuelAmount")
                    if fuel_amount and fuel_amount != "0":
                        try:
                            fuel_val = float(fuel_amount)
                            if fuel_val > 0:
                                lines.append(f"Fuel: {fuel_val:.1f}s")
                        except (ValueError, TypeError):
                            pass
            except Exception:
                pass

        # Damage (inherited from base weapon/ammo structure)
        damage_info = _find(root, "DamageInfo")
        if damage_info is not None:
            total_dmg, breakdown = _ammo_damage_breakdown(root)
            if total_dmg and total_dmg > 0:
                type_str = ""
                if breakdown and len(breakdown) == 1:
                    type_str = f" ({list(breakdown.keys())[0]})"
                elif breakdown and len(breakdown) > 1:
                    type_str = " (" + " / ".join(f"{lbl}: {v:.1f}" for lbl, v in breakdown.items()) + ")"
                lines.append(f"Damage: {_fmt(total_dmg, '', 1)}{type_str}")

        # Blast radius (warhead explosion radius)
        blast = _attr(root, "DamageInfo", "DamageDropOffEnd") or _attr(root, "Warhead", "blastRadius") or _attr(root, "ExplosionParams", "radius")
        if blast:
            try:
                blast_val = float(blast)
                if blast_val > 0:
                    lines.append(f"Blast Radius: {blast_val:,.0f} m")
            except (ValueError, TypeError):
                pass

        # Effective range (calculated or stored)
        eff_range = _attr(root, "ProjectileParams", "effectiveRange")
        if eff_range and eff_range != "0":
            try:
                eff_val = float(eff_range) / 1000  # Convert to km
                if eff_val > 0:
                    lines.append(f"Effective Range: {eff_val:,.1f} km")
            except (ValueError, TypeError):
                pass

        # EM and IR signatures (how detectable the missile is)
        em_sig = _attr(root, "EMSignature", "nominalSignature")
        if em_sig and em_sig != "0":
            try:
                em_val = float(em_sig)
                if em_val > 0:
                    lines.append(f"EM Signature: {em_val:,.0f}")
            except (ValueError, TypeError):
                pass

        ir_sig = _attr(root, "IRSignature", "nominalSignature")
        if ir_sig and ir_sig != "0":
            try:
                ir_val = float(ir_sig)
                if ir_val > 0:
                    lines.append(f"IR Signature: {ir_val:,.0f}")
            except (ValueError, TypeError):
                pass

        # Component HP
        comp_hp = _attr(root, "SHealthComponentParams", "Health")
        if comp_hp is not None:
            lines.append(f"Component HP: {_fmt(comp_hp)}")
    except Exception:
        pass

    return "\\n".join(lines) if lines else ""


def stats_radar(root: ET.Element) -> str:
    """Extract radar/sensor detection and tracking stats."""
    lines = []

    try:
        # Look for radar/sensor parameter structures (detection range, tracking, signature threshold, etc.)
        for el in root.iter():
            try:
                # Scan for detection range fields
                if "detection" in el.tag.lower() or "range" in el.tag.lower() or "sensor" in el.tag.lower():
                    # Detection range
                    det_range = el.get("detectionRange") or el.get("range") or el.get("maxRange")
                    if det_range and det_range != "0":
                        try:
                            range_val = float(det_range)
                            if range_val > 0:
                                lines.append(f"Detection Range: {range_val / 1000:,.1f} km")
                        except (ValueError, TypeError):
                            pass

                    # Tracking range (how far it can track locked targets)
                    track_range = el.get("trackingRange") or el.get("trackRange") or el.get("maxTrackingRange")
                    if track_range and track_range != "0":
                        try:
                            track_val = float(track_range)
                            if track_val > 0:
                                lines.append(f"Tracking Range: {track_val / 1000:,.1f} km")
                        except (ValueError, TypeError):
                            pass

                    # Signature detection threshold
                    sig_threshold = el.get("signatureThreshold") or el.get("minSignature") or el.get("detectionThreshold")
                    if sig_threshold and sig_threshold != "0":
                        try:
                            sig_val = float(sig_threshold)
                            lines.append(f"Signature Threshold: {sig_val}")
                        except (ValueError, TypeError):
                            pass

                    # Track count (number of simultaneous tracks)
                    track_count = el.get("maxTargets") or el.get("trackCount") or el.get("trackingCapacity")
                    if track_count and track_count != "0":
                        try:
                            count_val = int(float(track_count))
                            if count_val > 0:
                                lines.append(f"Max Targets: {count_val}")
                        except (ValueError, TypeError):
                            pass

                # Power and signature characteristics
                if el.tag == "EMSignature" or el.tag == "IRSignature":
                    nom_sig = el.get("nominalSignature")
                    if nom_sig and nom_sig != "0":
                        try:
                            sig_val = float(nom_sig)
                            sig_type = "EM" if el.tag == "EMSignature" else "IR"
                            if not any(f"{sig_type} Sig:" in line for line in lines):
                                lines.append(f"{sig_type} Signature: {sig_val}")
                        except (ValueError, TypeError):
                            pass
            except Exception:
                pass

        # Power consumption for radar/sensors
        pwr = _find_resource(root, "Power")
        if pwr is not None:
            lines.append(f"Power Draw: {_fmt(pwr, ' PU/s')}")

        # Component health
        comp_hp = _attr(root, "SHealthComponentParams", "Health")
        if comp_hp is not None:
            lines.append(f"Component HP: {_fmt(comp_hp)}")
    except Exception:
        pass

    return "\\n".join(lines) if lines else ""


def stats_cooler(root: ET.Element) -> str:
    cooling   = _find_resource(root, "Coolant")
    pwr       = _find_resource(root, "Power")
    comp_hp   = _attr(root, "SHealthComponentParams", "Health")
    em_sig    = _attr(root, "EMSignature", "nominalSignature")
    ir_sig    = _attr(root, "IRSignature", "nominalSignature")
    overheat  = _attr(root, "itemResourceParams", "overheatTemperature")

    lines = []
    if cooling is not None:
        lines.append(f"Cooling Rate: {_fmt(cooling, ' CR/s')}")
    if pwr is not None:
        lines.append(f"Power Draw: {_fmt(pwr, ' PU/s')}")
    if comp_hp is not None:
        lines.append(f"Component HP: {_fmt(comp_hp)}")
    if em_sig is not None or ir_sig is not None:
        parts = []
        if em_sig is not None: parts.append(f"EM: {_fmt(em_sig)}")
        if ir_sig is not None: parts.append(f"IR: {_fmt(ir_sig)}")
        lines.append("Signatures:  " + "  |  ".join(parts))
    if overheat is not None:
        lines.append(f"Overheat Temp: {_fmt(overheat, 'K')}")
    return "\\n".join(lines)


def stats_powerplant(root: ET.Element) -> str:
    gen       = _find_resource(root, "Power")
    comp_hp   = _attr(root, "SHealthComponentParams", "Health")
    em_sig    = _attr(root, "EMSignature", "nominalSignature")
    ir_sig    = _attr(root, "IRSignature", "nominalSignature")
    overheat  = _attr(root, "itemResourceParams", "overheatTemperature")
    distort   = _attr(root, "SDistortionParams", "Maximum")

    lines = []
    if gen is not None:
        lines.append(f"Power Output: {_fmt(gen, ' PU/s')}")
    if comp_hp is not None:
        lines.append(f"Component HP: {_fmt(comp_hp)}")
    if em_sig is not None or ir_sig is not None:
        parts = []
        if em_sig is not None: parts.append(f"EM: {_fmt(em_sig)}")
        if ir_sig is not None: parts.append(f"IR: {_fmt(ir_sig)}")
        lines.append("Signatures:  " + "  |  ".join(parts))
    if overheat is not None:
        lines.append(f"Overheat Temp: {_fmt(overheat, 'K')}")
    if distort is not None:
        lines.append(f"Max Distortion: {_fmt(distort)}")
    return "\\n".join(lines)


def stats_quantum_drive(root: ET.Element) -> str:
    qd = _find(root, "SCItemQuantumDriveParams")
    if qd is None:
        return ""
    fuel_req = qd.get("quantumFuelRequirement")

    # SQuantumDriveParams is an inline struct: <params __type="SQuantumDriveParams" driveSpeed=... />
    params   = _find_by_type(root, "SQuantumDriveParams")
    speed    = params.get("driveSpeed")           if params is not None else None
    spool    = params.get("spoolUpTime")          if params is not None else None
    cooldown = params.get("cooldownTime")         if params is not None else None
    cal_rate = params.get("calibrationRate")      if params is not None else None
    cal_min  = params.get("minCalibrationRequirement") if params is not None else None
    cal_max  = params.get("maxCalibrationRequirement") if params is not None else None
    accel1   = params.get("stageOneAccelRate")    if params is not None else None
    accel2   = params.get("stageTwoAccelRate")    if params is not None else None

    pwr      = _find_resource(root, "Power")
    qt_fuel  = _find_resource(root, "QuantumFuel")
    comp_hp  = _attr(root, "SHealthComponentParams", "Health")
    em_sig   = _attr(root, "EMSignature", "nominalSignature")
    ir_sig   = _attr(root, "IRSignature", "nominalSignature")
    overheat = _attr(root, "itemResourceParams", "overheatTemperature")
    distort  = _attr(root, "SDistortionParams", "Maximum")

    lines = []
    if speed is not None:
        speed_mm = float(speed) / 1_000_000
        spool_str = _fmt(spool, "s") if spool else "?"
        lines.append(f"QT Speed: {speed_mm:,.0f} Mm/s  |  Spool: {spool_str}")
    if cooldown is not None:
        lines.append(f"Cooldown: {_fmt(cooldown, 's', 1)}")
    if fuel_req is not None:
        lines.append(f"Fuel/Gm: {float(fuel_req):.4f}")
    if qt_fuel is not None:
        lines.append(f"QT Fuel Use: {_fmt(qt_fuel)} μ/s")
    if accel1 is not None or accel2 is not None:
        parts = []
        if accel1: parts.append(f"S1: {_fmt(accel1)}")
        if accel2: parts.append(f"S2: {_fmt(accel2)}")
        lines.append("Accel:  " + "  |  ".join(parts))
    if cal_rate is not None:
        lines.append(f"Cal Rate: {_fmt(cal_rate)}  |  Required: {_fmt(cal_min)}–{_fmt(cal_max)}")
    if pwr is not None:
        lines.append(f"Power Draw: {_fmt(pwr, ' PU/s')}")
    if comp_hp is not None:
        lines.append(f"Component HP: {_fmt(comp_hp)}")
    if em_sig is not None or ir_sig is not None:
        parts = []
        if em_sig is not None: parts.append(f"EM: {_fmt(em_sig)}")
        if ir_sig is not None: parts.append(f"IR: {_fmt(ir_sig)}")
        lines.append("Signatures:  " + "  |  ".join(parts))
    if overheat is not None:
        lines.append(f"Overheat Temp: {_fmt(overheat, 'K')}")
    if distort is not None:
        lines.append(f"Max Distortion: {_fmt(distort)}")
    return "\\n".join(lines)


def stats_mission(root: ET.Element) -> str:
    """Extract mission/contract reward stats (XP, aUEC, reputation)."""
    lines = []

    try:
        # Look for reward containers or direct fields
        for el in root.iter():
            try:
                # Check for xpReward field
                xp = el.get("xpReward")
                if xp and xp != "0":
                    try:
                        xp_val = int(float(xp))
                        if xp_val > 0:
                            lines.append(f"XP Reward: {xp_val:,}")
                    except (ValueError, TypeError):
                        pass

                # Check for aUEC (Alpha UEC / in-game currency)
                auec = el.get("aUEC") or el.get("auec")
                if auec and auec != "0":
                    try:
                        auec_val = int(float(auec))
                        if auec_val > 0:
                            lines.append(f"aUEC: {auec_val:,}")
                    except (ValueError, TypeError):
                        pass

                # Check for reputation rewards
                rep = el.get("reputationReward") or el.get("reputation")
                if rep and rep != "0":
                    try:
                        rep_val = float(rep)
                        if rep_val > 0:
                            lines.append(f"Reputation: +{rep_val:,.2f}")
                    except (ValueError, TypeError):
                        pass

                # Check for other reward types in reward containers
                if "Reward" in el.tag:
                    # Look for amount fields within reward containers
                    amount = el.get("amount")
                    reward_type = el.get("type") or el.get("rewardType") or el.tag.replace("Reward", "").replace("Params", "")
                    if amount and amount != "0":
                        try:
                            amount_val = int(float(amount))
                            if amount_val > 0:
                                lines.append(f"{reward_type}: {amount_val:,}")
                        except (ValueError, TypeError):
                            pass
            except Exception:
                # Skip individual elements that cause errors
                pass
    except Exception:
        pass

    return "\\n".join(lines) if lines else ""


def scan_crafting_recipes(recipes_dir: Path) -> dict[str, list[str]]:
    """Scan crafting recipe entities to build a map of commodity → crafted items.

    Returns a dict mapping commodity localization keys (e.g., "items_commodities_agricium")
    to lists of crafted item names that use that commodity as an ingredient.
    """
    commodity_recipes: dict[str, list[str]] = {}  # commodity_key → [item1, item2, ...]

    if not recipes_dir.exists():
        return commodity_recipes

    try:
        for xml_file in recipes_dir.rglob("*.xml"):
            try:
                root = ET.parse(xml_file).getroot()
            except ET.ParseError:
                continue

            try:
                # Extract the output item's localization key (the result of the recipe)
                output_key = _loc_key(root)
                if not output_key:
                    continue

                # Scan for ingredient references (commodity keys)
                for el in root.iter():
                    try:
                        # Look for commodity ingredient references
                        if "ingredient" in el.tag.lower() or "input" in el.tag.lower():
                            # Try to find commodity references
                            item_guid = el.get("itemGUID") or el.get("itemGuid") or el.get("itemClass")
                            item_ref = el.get("item") or el.get("ref")

                            # If we find a commodity reference, map it to this output
                            if item_ref and "commodities" in item_ref.lower():
                                # Extract commodity key from reference
                                commodity_key = item_ref.lower().replace("@", "")
                                if commodity_key not in commodity_recipes:
                                    commodity_recipes[commodity_key] = []
                                if output_key not in commodity_recipes[commodity_key]:
                                    commodity_recipes[commodity_key].append(output_key)
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass

    return commodity_recipes


def stats_weapon(root: ET.Element, ammo_lookup: dict[str, ET.Element],
                 loc: dict | None = None) -> str:
    """Ship or FPS weapon stats."""
    fr    = _fire_rate(root)
    modes = _fire_modes(root, loc)
    pwr   = _find_resource(root, "Power")

    # Component health / signatures / heat
    comp_hp  = _attr(root, "SHealthComponentParams", "Health")
    em_sig   = _attr(root, "EMSignature", "nominalSignature")
    ir_sig   = _attr(root, "IRSignature", "nominalSignature")
    overheat = _attr(root, "itemResourceParams", "overheatTemperature")

    # Ammo damage — look up the ammo record by GUID
    ammo_container = _find(root, "SAmmoContainerComponentParams")
    ammo_record_id = ammo_container.get("ammoParamsRecord") if ammo_container is not None else None
    total_dmg = breakdown = proj_speed = proj_lifetime = None
    dps = None
    if ammo_record_id and ammo_record_id != "00000000-0000-0000-0000-000000000000":
        ammo_root = ammo_lookup.get(ammo_record_id)
        if ammo_root is not None:
            total_dmg, breakdown = _ammo_damage_breakdown(ammo_root)
            # Try multiple field names for projectile speed (varies by ammo type)
            proj_speed = (ammo_root.get("speed") or
                         ammo_root.get("velocity") or
                         ammo_root.get("projectileSpeed") or
                         ammo_root.get("initialSpeed"))
            # Try multiple field names for lifetime
            proj_lifetime = (ammo_root.get("lifetime") or
                           ammo_root.get("projectileLifetime") or
                           ammo_root.get("maxLifetime"))
            if total_dmg and fr:
                try:
                    dps = total_dmg * float(fr) / 60.0
                except ValueError:
                    pass

    # Capacity: energy weapons use regen pool; ballistic use fixed container
    regen    = _find(root, "SWeaponRegenConsumerParams")
    capacity = None
    regen_rate = regen_cooldown = regen_cost = None
    if regen is not None:
        capacity      = regen.get("maxAmmoLoad")
        regen_rate    = regen.get("requestedRegenPerSec")
        regen_cooldown = regen.get("regenerationCooldown")
        regen_cost    = regen.get("regenerationCostPerBullet")
    elif ammo_container is not None:
        capacity = ammo_container.get("maxAmmoCount")

    lines = []
    if fr:
        lines.append(f"Fire Rate: {_fmt(fr, ' RPM')}")
    if modes:
        lines.append(f"Fire Modes: {' / '.join(modes)}")

    # Damage line with per-type breakdown
    if total_dmg is not None and total_dmg > 0:
        type_str = ""
        if breakdown and len(breakdown) == 1:
            type_str = f" ({list(breakdown.keys())[0]})"
        elif breakdown and len(breakdown) > 1:
            type_str = " (" + " / ".join(f"{lbl}: {v:.1f}" for lbl, v in breakdown.items()) + ")"
        dmg_part = f"Dmg/Shot: {_fmt(total_dmg, '', 1)}{type_str}"
        dps_part = f"DPS: {_fmt(dps, '', 1)}" if dps else ""
        lines.append("  |  ".join(p for p in [dmg_part, dps_part] if p))

    if capacity:
        lines.append(f"Ammo: {_fmt(capacity)}")
    if regen_rate or regen_cooldown:
        parts = []
        if regen_rate:    parts.append(f"Regen: {_fmt(regen_rate)}/s")
        if regen_cooldown: parts.append(f"Cooldown: {_fmt(regen_cooldown, 's', 1)}")
        if regen_cost:    parts.append(f"Cost/Shot: {_fmt(regen_cost)}")
        lines.append("  |  ".join(parts))
    if proj_speed is not None:
        try:
            rng_m = float(proj_speed) * float(proj_lifetime)
            lines.append(f"Velocity: {_fmt(proj_speed, ' m/s')}  |  Range: {rng_m / 1000:,.1f} km")
        except (TypeError, ValueError):
            pass
    if pwr:
        lines.append(f"Power Draw: {_fmt(pwr, ' PU/s')}")
    if comp_hp is not None:
        lines.append(f"Component HP: {_fmt(comp_hp)}")
    if em_sig is not None or ir_sig is not None:
        parts = []
        if em_sig is not None: parts.append(f"EM: {_fmt(em_sig)}")
        if ir_sig is not None: parts.append(f"IR: {_fmt(ir_sig)}")
        lines.append("Signatures:  " + "  |  ".join(parts))
    if overheat is not None:
        lines.append(f"Overheat Temp: {_fmt(overheat, 'K')}")
    return "\\n".join(lines)


# ── Ship stats (DataForge-based) ──────────────────────────────────────────────

def _extract_item_size(cls: str) -> str | None:
    """Extract size code from entity class name, e.g. 'SHLD_ASAS_S01_Shimmer_SCItem' → 'S1'."""
    m = re.search(r'_S0*(\d+)_', cls)
    return f"S{int(m.group(1))}" if m else None


def _loadout_summary(root: ET.Element) -> tuple[str, str]:
    """Parse SEntityComponentDefaultLoadoutParams and return (weapons_line, core_line).

    Only iterates TOP-LEVEL ship hardpoints (not nested sub-items inside turrets or
    mounted equipment) to avoid double-counting turret weapon slots as ship guns.

    Gun detection handles two naming conventions:
    - Avenger-style fixed slot: hardpoint_weapon_gun_class1_*  (size in port name)
    - Connie-style gimbal/fixed mount: hardpoint_weapon_* with Mount_Gimbal_S3 entity
      → size extracted from mount entity class name (Mount_Gimbal_S3 → S3)
    """
    guns:    list[tuple[str, bool]] = []   # (size_str, filled)
    turrets: list[tuple[str, bool]] = []
    mracks:  list[tuple[str, bool]] = []
    shields: list[str] = []               # size strings for filled slots
    powers:  list[str] = []
    coolers: list[str] = []
    qd:      list[str] = []

    # Only process direct children of the top-level loadout entries element
    # to avoid counting nested sub-weapon slots inside turrets/mounts
    comp = _find(root, "SEntityComponentDefaultLoadoutParams")
    if comp is None:
        return "", ""
    top_entries = comp.find(".//entries")
    if top_entries is None:
        return "", ""

    for entry in top_entries:
        if entry.tag != "SItemPortLoadoutEntryParams":
            continue
        port = entry.get("itemPortName", "").lower()
        cls  = entry.get("entityClassName", "")

        if "controller" in port:
            continue

        # Size: _classN in port name (Avenger-style), or _S0N_ in entity class name
        sz = None
        m = re.search(r'_class_?(\d+)', port)
        if m:
            sz = f"S{int(m.group(1))}"
        elif cls:
            sz = _extract_item_size(cls)

        # Gimbal/fixed mount → counts as a gun slot; size from the mount entity (Mount_Gimbal_S3)
        if cls.startswith("Mount_Gimbal_") or cls.startswith("Mount_Fixed_"):
            guns.append((sz or "?", True))   # mount exists = slot is equipped
        # Avenger-style bare gun slot (may be empty)
        elif "weapon_gun" in port:
            guns.append((sz or "?", bool(cls)))
        elif "turret" in port and cls:
            turrets.append((sz or "?", bool(cls)))
        elif "missilerack" in port or "missilelauncher" in port:
            if cls:
                mracks.append((sz or "?", True))
        elif "shield_generator" in port and cls:
            shields.append(sz or "?")
        elif ("power_plant" in port or "powerplant" in port) and cls:
            powers.append(sz or "?")
        elif "cooler" in port and cls:
            coolers.append(sz or "?")
        elif "quantum_drive" in port and "fuel" not in port and cls:
            qd.append(sz or "?")

    def summarize_slots(slots: list[tuple[str, bool]]) -> str:
        counts: dict = {}
        for sz, filled in slots:
            key = (sz, filled)
            counts[key] = counts.get(key, 0) + 1
        parts = []
        for (sz, filled), cnt in sorted(counts.items()):
            suffix = "" if filled else " (empty)"
            if sz == "?":
                # Unknown size: show just count (e.g. turrets with no size info)
                parts.append(str(cnt))
            else:
                n = f"{cnt}× " if cnt > 1 else ""
                parts.append(f"{n}{sz}{suffix}")
        return "  ".join(p for p in parts if p)

    def summarize_items(sizes: list[str]) -> str:
        counts: dict = {}
        for sz in sizes:
            counts[sz] = counts.get(sz, 0) + 1
        parts = []
        for sz, cnt in sorted(counts.items()):
            n = f"{cnt}× " if cnt > 1 else ""
            parts.append(f"{n}{sz}")
        return "  ".join(parts)

    weapon_parts = []
    if guns:
        weapon_parts.append(f"Guns: {summarize_slots(guns)}")
    if turrets:
        weapon_parts.append(f"Turrets: {summarize_slots(turrets)}")
    if mracks:
        weapon_parts.append(f"MRacks: {summarize_slots(mracks)}")

    core_parts = []
    if shields:
        core_parts.append(f"Shields: {summarize_items(shields)}")
    if coolers:
        core_parts.append(f"Coolers: {summarize_items(coolers)}")
    if powers:
        core_parts.append(f"Power: {summarize_items(powers)}")
    if qd:
        core_parts.append(f"QD: {summarize_items(qd)}")

    return "  |  ".join(weapon_parts), "  |  ".join(core_parts)


def build_controller_lookup(controller_dir: Path) -> dict[str, ET.Element]:
    """Build lookup: ship_class_lower → flight controller XML root.

    Controller files are named 'controller_flight_{ship_class}.xml'.
    Blade/variant controllers (with '_flight_' in the class suffix) are
    included so each spaceship entity can find its exact match.
    """
    lookup: dict[str, ET.Element] = {}
    if not controller_dir.exists():
        logger.warning(f"Controller dir not found: {controller_dir}")
        return lookup
    for xml_file in controller_dir.glob("controller_flight_*.xml"):
        ship_class = xml_file.stem[len("controller_flight_"):]
        try:
            root = ET.parse(xml_file).getroot()
            lookup[ship_class.lower()] = root
        except ET.ParseError:
            pass
    return lookup


def stats_ship_dataforge(
    root: ET.Element,
    controller_root: ET.Element | None,
    loc: dict | None = None,
) -> str:
    """Generate stats block for a spaceship from DataForge entity + flight controller."""
    vpc = _find(root, "VehicleComponentParams")
    if vpc is None:
        return ""

    crew_size = vpc.get("crewSize")
    career_key = (vpc.get("vehicleCareer") or "").lstrip("@")
    role_key   = (vpc.get("vehicleRole")   or "").lstrip("@")
    career = (loc or {}).get(career_key) if career_key else None
    role   = (loc or {}).get(role_key)   if role_key   else None

    bbox   = vpc.find("maxBoundingBoxSize")
    length = bbox.get("y") if bbox is not None else None

    # Insurance — DataForge tag is lowercase 'shipInsuranceParams', __type is 'ShipInsuranceParams'
    ins         = _find(root, "shipInsuranceParams")
    ins_base    = ins.get("baseWaitTimeMinutes")      if ins is not None else None
    ins_express = ins.get("mandatoryWaitTimeMinutes") if ins is not None else None

    # Default loadout summary
    weapons_line, core_line = _loadout_summary(root)

    # Flight stats from controller
    scm = max_spd = boost_fwd = boost_bwd = None
    pitch = roll = yaw = None
    if controller_root is not None:
        ifcs = _find(controller_root, "IFCSParams")
        if ifcs is not None:
            scm       = ifcs.get("scmSpeed")
            max_spd   = ifcs.get("maxSpeed")
            boost_fwd = ifcs.get("boostSpeedForward")
            boost_bwd = ifcs.get("boostSpeedBackward")
        sp = _find_by_type(controller_root, "SIFCSSpeedProfile")
        if sp is not None:
            av = sp.find("angularVelocity")
            if av is not None:
                pitch = av.get("x")   # pitch rate °/s
                roll  = av.get("y")   # roll rate  °/s
                yaw   = av.get("z")   # yaw rate   °/s

    lines = []

    if scm is not None or max_spd is not None:
        lines.append(f"SCM: {_fmt(scm, ' m/s')}  |  Max: {_fmt(max_spd, ' m/s')}")
    if boost_fwd is not None or boost_bwd is not None:
        lines.append(f"Boost: +{_fmt(boost_fwd, ' m/s')}  /  -{_fmt(boost_bwd, ' m/s')}")
    if pitch is not None:
        lines.append(
            f"Pitch: {_fmt(pitch, '°/s')}  |  Roll: {_fmt(roll, '°/s')}  |  Yaw: {_fmt(yaw, '°/s')}"
        )

    basics = []
    if crew_size is not None: basics.append(f"Crew: {_fmt(crew_size)}")
    if length    is not None: basics.append(f"Length: {_fmt(length, 'm', 1)}")
    if career    is not None: basics.append(f"Class: {career}")
    if role      is not None: basics.append(f"Role: {role}")
    if basics:
        lines.append("  |  ".join(basics))

    if weapons_line:
        lines.append(weapons_line)
    if core_line:
        lines.append(core_line)

    if ins_base is not None:
        lines.append(
            f"Insurance: {_fmt(ins_base, ' min', 2)} base  |  {_fmt(ins_express, ' min', 2)} express"
        )

    return "\\n".join(lines)


def scan_spaceships(
    spaceships_dir: Path,
    controller_lookup: dict,
    loc: dict,
) -> dict[str, str]:
    """Scan DataForge spaceship entities and generate ship stat descriptions."""
    out: dict[str, str] = {}
    matched = missed = skipped = 0

    for xml_file in sorted(spaceships_dir.glob("*.xml")):
        # Skip AI variants, templates, and unmanned variants
        stem = xml_file.stem.lower()
        if "_pu_ai_" in stem or "_ai_template" in stem or "_unmanned_" in stem:
            skipped += 1
            continue

        try:
            root = ET.parse(xml_file).getroot()
        except ET.ParseError:
            continue

        # Loc key from VehicleComponentParams.vehicleDescription
        vpc = _find(root, "VehicleComponentParams")
        if vpc is None:
            skipped += 1
            continue
        desc_attr = vpc.get("vehicleDescription", "")
        if not desc_attr.startswith("@"):
            skipped += 1
            continue
        loc_key = desc_attr.lstrip("@")

        base_value = loc.get(loc_key)
        if base_value is None:
            missed += 1
            continue

        # Match ship class to flight controller
        root_tag = root.tag
        ship_class = root_tag.split(".", 1)[1].lower() if "." in root_tag else stem
        controller_root = controller_lookup.get(ship_class)

        try:
            block = stats_ship_dataforge(root, controller_root, loc)
        except Exception as e:
            logger.warning(f"Ship stats failed for {xml_file.name}: {e}")
            continue

        if block:
            # Deduplicate: first match for a given key wins
            if loc_key not in out:
                out[loc_key] = append_stats(base_value, block)
                matched += 1
        else:
            missed += 1

    logger.info(f"Spaceships: {matched} matched, {missed} no stats/key, {skipped} skipped (AI/templates)")
    return out


# ── Ammo lookup builder ───────────────────────────────────────────────────────

def build_ammo_lookup(ammo_dir: Path) -> dict[str, ET.Element]:
    """Parse all ammo XML files and index them by their __ref GUID.

    Falls back to root tag name if __ref is not available.
    """
    lookup: dict[str, ET.Element] = {}
    if not ammo_dir.exists():
        return lookup
    for xml_file in ammo_dir.rglob("*.xml"):
        try:
            root = ET.parse(xml_file).getroot()
            # Primary: use __ref attribute (GUID)
            ref = root.get("__ref")
            if ref:
                lookup[ref] = root
            # Fallback: index by file stem if no __ref (helps with FPS ammo)
            else:
                lookup[xml_file.stem] = root
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
            logger.warning(f"Stats failed for {xml_file.name}: {e}")
            continue

        if stats_block:
            out[key] = append_stats(base_value, stats_block)
            matched += 1
        else:
            missed += 1

    logger.info(f"{entity_dir.name}: {matched} matched, {missed} no stats, {skipped} no loc key")
    return out


# ── Main ──────────────────────────────────────────────────────────────────────

def main(base_ini_path: Path, forge_dir: Path | None = None) -> None:
    import sys as sys_mod
    logger.info("=== SC Stats INI Generator (DataForge edition) ===")
    sys_mod.stdout.flush()
    sys_mod.stderr.flush()

    if forge_dir is None:
        forge_dir = DEFAULT_FORGE_DIR

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Parse base.ini ─────────────────────────────────────────────────────────
    logger.info(f"CHECKPOINT: Parsing base.ini: {base_ini_path}")
    sys_mod.stdout.flush()
    if not base_ini_path.exists():
        raise FileNotFoundError(f"base.ini not found at {base_ini_path}")
    loc = parse_ini(base_ini_path)
    logger.info(f"CHECKPOINT: Loaded {len(loc):,} localization keys")
    sys_mod.stdout.flush()

    # ── Check DataForge cache ─────────────────────────────────────────────────
    logger.info("CHECKPOINT: Checking DataForge cache...")
    sys_mod.stdout.flush()
    records = forge_dir / "libs" / "foundry" / "records"
    if not forge_dir.exists() or not records.exists():
        raise FileNotFoundError(
            f"DataForge cache not found at {forge_dir}\n"
            "Run 'Extract DataForge' in the app first (Enhancements tab)."
        )

    # ── Build ammo lookups ────────────────────────────────────────────────────
    logger.info("CHECKPOINT: Building ammo damage lookups…")
    sys_mod.stdout.flush()
    vehicle_ammo = build_ammo_lookup(records / "ammoparams" / "vehicle")
    fps_ammo     = build_ammo_lookup(records / "ammoparams" / "fps")
    logger.info(f"CHECKPOINT: Vehicle ammo: {len(vehicle_ammo)} records, FPS ammo: {len(fps_ammo)} records")
    sys_mod.stdout.flush()

    # ── Process components ────────────────────────────────────────────────────
    ships_scitem = records / "entities" / "scitem" / "ships"

    logger.info("CHECKPOINT: Processing ship components…")
    sys_mod.stdout.flush()
    out_components: dict[str, str] = {}
    for subdir, fn in [
        ("shieldgenerator", stats_shield),
        ("cooler",          stats_cooler),
        ("powerplant",      stats_powerplant),
        ("quantumdrive",    stats_quantum_drive),
    ]:
        logger.info(f"CHECKPOINT: Processing {subdir}...")
        sys_mod.stdout.flush()
        out_components.update(scan_entity_dir(ships_scitem / subdir, fn, loc=loc))

    # ── Process radar/sensors ─────────────────────────────────────────────────
    logger.info("Processing radar components…")
    scitem_dir = records / "entities" / "scitem"
    ships_scitem = scitem_dir / "ships"
    radar_dir = ships_scitem / "radar"
    if radar_dir.exists():
        logger.info(f"Processing radars from {radar_dir}…")
        out_components.update(scan_entity_dir(radar_dir, stats_radar, loc=loc))

    # ── Process missiles/rockets/bombs ────────────────────────────────────────
    logger.info("Processing missile/rocket/bomb stats…")
    out_missiles: dict[str, str] = {}
    weapons_dir = ships_scitem / "weapons"
    for missile_dir in [
        weapons_dir / "missiles",
        weapons_dir / "rocket_pods",
    ]:
        if missile_dir.exists():
            logger.info(f"Processing from {missile_dir}…")
            out_missiles.update(scan_entity_dir(missile_dir, stats_missile, loc=loc))

    # ── Process ship weapons ──────────────────────────────────────────────────
    logger.info("CHECKPOINT: Processing ship weapons…")
    sys_mod.stdout.flush()
    out_ship_weapons: dict[str, str] = {}
    weapons_dir = ships_scitem / "weapons"
    if weapons_dir.exists():
        out_ship_weapons = scan_entity_dir(
            weapons_dir,
            lambda root: stats_weapon(root, vehicle_ammo, loc),
            loc=loc,
        )
    logger.info(f"CHECKPOINT: Finished ship weapons ({len(out_ship_weapons)} entries)")
    sys_mod.stdout.flush()

    # ── Process FPS weapons ───────────────────────────────────────────────────
    logger.info("CHECKPOINT: Processing FPS weapons…")
    sys_mod.stdout.flush()
    out_fps_weapons: dict[str, str] = {}
    fps_dir = records / "entities" / "scitem" / "weapons" / "fps_weapons"
    if fps_dir.exists():
        out_fps_weapons = scan_entity_dir(
            fps_dir,
            lambda root: stats_weapon(root, fps_ammo, loc),
            loc=loc,
        )
    logger.info(f"CHECKPOINT: Finished FPS weapons ({len(out_fps_weapons)} entries)")
    sys_mod.stdout.flush()

    # ── Process ships (DataForge spaceship entities + flight controllers) ──────
    logger.info("CHECKPOINT: Building flight controller lookup…")
    sys_mod.stdout.flush()
    controller_dir = records / "entities" / "scitem" / "ships" / "controller"
    controller_lookup = build_controller_lookup(controller_dir)
    logger.info(f"CHECKPOINT: Controllers: {len(controller_lookup)} loaded")
    sys_mod.stdout.flush()

    logger.info("CHECKPOINT: Processing ship descriptions…")
    sys_mod.stdout.flush()
    spaceships_dir = records / "entities" / "spaceships"
    out_ships = scan_spaceships(spaceships_dir, controller_lookup, loc)
    logger.info(f"CHECKPOINT: Finished ships ({len(out_ships)} entries)")
    sys_mod.stdout.flush()

    # ── Process missions/contracts ────────────────────────────────────────────
    logger.info("CHECKPOINT: Processing mission/contract rewards…")
    sys_mod.stdout.flush()
    out_missions: dict[str, str] = {}
    for mission_dir in [
        records / "entities" / "missions",
        records / "entities" / "contracts",
        records / "entities" / "jobterminal",
    ]:
        if mission_dir.exists():
            logger.info(f"CHECKPOINT: Processing {mission_dir.name}…")
            sys_mod.stdout.flush()
            out_missions.update(scan_entity_dir(mission_dir, stats_mission, loc=loc))
    logger.info(f"CHECKPOINT: Finished missions ({len(out_missions)} entries)")
    sys_mod.stdout.flush()

    # ── Process crafting recipes and augment commodities ─────────────────────
    logger.info("CHECKPOINT: Processing crafting recipes…")
    sys_mod.stdout.flush()
    out_commodities: dict[str, str] = {}

    # Scan all crafting-related directories for recipes
    commodity_recipes: dict[str, list[str]] = {}
    for recipes_dir in [
        records / "entities" / "crafting",
        records / "entities" / "recipes",
        records / "entities" / "manufacturing",
    ]:
        if recipes_dir.exists():
            logger.info(f"CHECKPOINT: Scanning {recipes_dir.name}…")
            sys_mod.stdout.flush()
            commodity_recipes.update(scan_crafting_recipes(recipes_dir))

    # Augment commodity descriptions with crafting usage information
    if commodity_recipes:
        logger.info(f"CHECKPOINT: Found {len(commodity_recipes)} commodities used in crafting")
        sys_mod.stdout.flush()
        for commodity_key, crafted_items in commodity_recipes.items():
            if commodity_key in loc:
                base_value = loc[commodity_key]
                # Add crafting marker and list of items
                crafted_items_str = ", ".join(crafted_items[:5])  # Limit to first 5
                if len(crafted_items) > 5:
                    crafted_items_str += f" + {len(crafted_items) - 5} more"
                stats_block = f"[CRAFTING] Used in: {crafted_items_str}"
                out_commodities[commodity_key] = append_stats(base_value, stats_block)

    # ── Write output ──────────────────────────────────────────────────────────
    logger.info("CHECKPOINT: Writing output files…")
    sys_mod.stdout.flush()
    write_ini(OUTPUT_DIR / "ships_desc_stats.ini",       out_ships)
    write_ini(OUTPUT_DIR / "components_desc_stats.ini",  out_components)
    write_ini(OUTPUT_DIR / "ship_weapons_desc_stats.ini",out_ship_weapons)
    write_ini(OUTPUT_DIR / "fps_weapons_desc_stats.ini", out_fps_weapons)
    # Always write all files, even if empty, so the startup check doesn't prompt repeatedly
    write_ini(OUTPUT_DIR / "mission_rewards_stats.ini", out_missions)
    write_ini(OUTPUT_DIR / "commodity_crafting_stats.ini", out_commodities)
    write_ini(OUTPUT_DIR / "missile_stats.ini", out_missiles)

    total = (len(out_ships) + len(out_components) + len(out_ship_weapons) +
             len(out_fps_weapons) + len(out_missions) + len(out_commodities) + len(out_missiles))
    logger.info(f"Done — {total:,} total stat entries written to {OUTPUT_DIR}")


if __name__ == "__main__":
    base_ini  = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BASE_INI
    forge_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_FORGE_DIR
    main(base_ini, forge_dir)
