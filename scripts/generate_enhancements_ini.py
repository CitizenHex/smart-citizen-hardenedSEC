"""
generate_enhancements_ini.py
────────────────────────────
Generates enhancement-augmented INI files for use as additional sources in
SC Localization Editor.

All enhancements are sourced directly from the game's DataForge entity XML files
(extracted from Data.p4k via unp4k + unforge).  No external JSON sources.

Output files (written to OUTPUT_DIR / cache):
  ships_desc_enhancements.ini        – vehicle_Desc* entries with flight/specs data
  components_desc_enhancements.ini   – item_Desc* COOL/SHLD/POWR/QDRV with numerical data
  ship_weapons_desc_enhancements.ini – item_Desc* ship weapon data
  fps_weapons_desc_enhancements.ini  – item_Desc* FPS weapon data

Usage:
  python scripts/generate_enhancements_ini.py [base_ini_path [dataforge_cache_dir]]
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


ENHANCEMENT_SEPARATOR = "\\n\\n== Stats ==\\n"


def append_enhancements(existing_value: str, enhancements_block: str) -> str:
    if not enhancements_block:
        return existing_value
    if "== Stats ==" in existing_value:
        existing_value = existing_value[:existing_value.index("\\n\\n== Stats ==")]
    return existing_value + ENHANCEMENT_SEPARATOR + enhancements_block


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


def _loc_name_key(root: ET.Element) -> str | None:
    """Extract the item_Name* localization key from the entity XML."""
    for el in root.iter("Localization"):
        name = el.get("Name", "")
        if name.startswith("@") and "LOC_EMPTY" not in name and "UNINITIALIZED" not in name:
            return name.lstrip("@")
    return None


# Classification abbreviations for component name tags
_CLASS_ABBREV = {
    "Competition": "CMP",
    "Military":    "MIL",
    "Civilian":    "CIV",
    "Industrial":  "IND",
    "Stealth":     "STH",
}


def _component_name_tag(desc_value: str) -> str | None:
    """Extract [CLASS-S{size}-{grade}] tag from a component description string.

    Parses the structured header lines (Size: N, Grade: X, Class: Y) that appear
    at the top of ship component descriptions in the base localization.

    Returns:
        Tag string like "[MIL-S1-A]" or None if parsing fails.
    """
    import re
    size_m = re.search(r"Size:\s*(\d+)", desc_value)
    grade_m = re.search(r"Grade:\s*([A-D])", desc_value)
    class_m = re.search(r"Class:\s*(\w+)", desc_value)
    if not (size_m and grade_m and class_m):
        return None
    abbrev = _CLASS_ABBREV.get(class_m.group(1))
    if not abbrev:
        return None
    return f"[{abbrev}-S{size_m.group(1)}-{grade_m.group(1)}]"


def _mission_loc_key(root: ET.Element) -> str | None:
    """Extract the mission description localization key from MissionBrokerEntry XML.

    Missions store the localization key in the 'description' attribute of the root element.
    """
    desc = root.get("description", "")
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


_FIRE_MODE_LABELS = {
    "rapid": "Auto", "single": "Semi-Auto", "burst": "Burst",
    "charge": "Charge", "shotgun": "Shotgun",
}


def _fire_modes(root: ET.Element, loc: dict | None = None) -> list[str]:
    names = []
    for el in root.iter():
        if "WeaponActionFire" in el.tag:
            # Prefer a clean label from the raw name attribute
            raw_name = (el.get("name") or "").strip()
            label = _FIRE_MODE_LABELS.get(raw_name.lower())
            if not label:
                # Try localized name, stripping brackets
                loc_key = el.get("localisedName", "")
                if loc_key.startswith("@") and loc is not None:
                    label = (loc.get(loc_key[1:]) or raw_name or "").strip("[] ")
                else:
                    label = raw_name or loc_key.strip("[] ")
            if label and label not in names:
                names.append(label)
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
    """Return (total_damage, {label: amount}) for non-zero damage types.

    Only reads the primary <damage> element, not damage drop-off values.
    """
    totals: dict[str, float] = {}
    # Find the primary damage element (direct child of projectile params, not drop-off)
    damage_elem = ammo_root.find(".//damage")
    if damage_elem is not None:
        for info in damage_elem.iter("DamageInfo"):
            for attr in _DAMAGE_TYPES:
                try:
                    v = float(info.get(attr, 0))
                    if v:
                        lbl = _DAMAGE_LABELS[attr]
                        totals[lbl] = totals.get(lbl, 0.0) + v
                except ValueError:
                    pass
    else:
        # Fallback: look for DamageInfo that's NOT inside damageDropParams
        for info in ammo_root.iter("DamageInfo"):
            # Skip DamageInfo elements inside damageDropParams
            parent_tags = set()
            node = info
            while node is not None:
                parent_tags.add(node.tag)
                node = None  # ElementTree doesn't support parent traversal easily
            for attr in _DAMAGE_TYPES:
                try:
                    v = float(info.get(attr, 0))
                    if v:
                        lbl = _DAMAGE_LABELS[attr]
                        totals[lbl] = totals.get(lbl, 0.0) + v
                except ValueError:
                    pass
            break  # Only use the first DamageInfo found
    return sum(totals.values()), totals


# ── Per-type stat generators ──────────────────────────────────────────────────

def enhancements_shield(root: ET.Element) -> str:
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


def enhancements_missile(root: ET.Element) -> str:
    """Extract missile/rocket/bomb enhancements: velocity, guidance, seeker type, lock ranges, tracking range,
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
        blast = _attr(root, "ExplosionParams", "maxRadius")
        if not blast:
            blast = _attr(root, "ExplosionParams", "minRadius")
        if not blast:
            blast = _attr(root, "Warhead", "blastRadius")
        if not blast:
            blast = _attr(root, "DamageInfo", "DamageDropOffEnd")
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


def enhancements_radar(root: ET.Element) -> str:
    """Extract radar/sensor stats.

    Note: Detection range is stored in shared parameter definitions (referenced by UUID)
    which are not included in the extracted XML, so we extract available stats like
    sensitivity and signature detection capabilities instead.
    """
    lines = []

    try:
        # Radar sensitivity for different signature types
        sensitivity_values = []
        for el in root.iter("SCItemRadarSignatureDetection"):
            try:
                sensitivity = el.get("sensitivity")
                if sensitivity:
                    try:
                        sens_val = float(sensitivity)
                        sensitivity_values.append(sens_val)
                    except (ValueError, TypeError):
                        pass
            except Exception:
                pass

        if sensitivity_values:
            avg_sensitivity = sum(sensitivity_values) / len(sensitivity_values)
            lines.append(f"Avg Sensitivity: {avg_sensitivity:.2f}")

        # Piercing capability (ability to detect through interference/jamming)
        piercing_values = []
        for el in root.iter("SCItemRadarSignatureDetection"):
            try:
                piercing = el.get("piercing")
                if piercing:
                    try:
                        pierce_val = float(piercing)
                        piercing_values.append(pierce_val)
                    except (ValueError, TypeError):
                        pass
            except Exception:
                pass

        if piercing_values:
            max_piercing = max(piercing_values)
            lines.append(f"Max Piercing: {max_piercing:.2f}")

        # Passive/Active detection capability
        passive_capable = False
        active_capable = False
        for el in root.iter("SCItemRadarSignatureDetection"):
            if el.get("permitPassiveDetection") == "1":
                passive_capable = True
            if el.get("permitActiveDetection") == "1":
                active_capable = True

        modes = []
        if passive_capable:
            modes.append("Passive")
        if active_capable:
            modes.append("Active")
        if modes:
            lines.append(f"Detection Mode: {' / '.join(modes)}")

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


def enhancements_cooler(root: ET.Element) -> str:
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


def enhancements_powerplant(root: ET.Element) -> str:
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


def enhancements_quantum_drive(root: ET.Element) -> str:
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


def _extract_mission_xp(root: ET.Element, reputation_lookup: dict[str, int] | None = None) -> int:
    """Extract mission success XP from primary reputation scope only.

    Gets the first (success outcome) reputation rewards, but only sums from the PRIMARY faction.
    Ignores bonus reputation for secondary factions/scopes. This matches SCMDB mission XP values
    which show only the primary faction reward, not bonuses.
    """
    reputation_lookup = reputation_lookup or {}
    total_rep_xp = 0

    # Only process the first SReputationAmountListParams (the success outcome)
    rep_lists = root.findall(".//missionResultReputationRewards/SReputationAmountListParams")
    if rep_lists:
        first_outcome = rep_lists[0]
        rep_amounts = first_outcome.findall(".//SReputationAmountParams")

        # Only count the FIRST reputation scope (primary faction)
        # Skip bonus reputation for secondary factions/scopes
        if rep_amounts:
            primary_scope = rep_amounts[0].get("reputationScope")
            for rep_amount in rep_amounts:
                # Only count rewards from the primary reputation scope
                if rep_amount.get("reputationScope") == primary_scope:
                    reward_uuid = rep_amount.get("reward")
                    if reward_uuid and reward_uuid in reputation_lookup:
                        xp_val = reputation_lookup[reward_uuid]
                        total_rep_xp += xp_val

    return total_rep_xp


def enhancements_mission(root: ET.Element, reputation_lookup: dict[str, int] | None = None) -> str:
    """Extract mission/contract reward stats (aUEC + Reputation XP).

    Extracts:
    - aUEC mission reward amount
    - Reputation XP from reward UUID references using the reputation_lookup table
    """
    lines = []
    reputation_lookup = reputation_lookup or {}

    try:
        # Extract aUEC reward
        mission_reward = root.find(".//missionReward")
        if mission_reward is not None:
            reward_attr = mission_reward.get("reward")
            if reward_attr and reward_attr != "0":
                try:
                    reward_val = int(float(reward_attr))
                    if reward_val > 0:
                        lines.append(f"aUEC Reward: {reward_val:,}")
                except (ValueError, TypeError):
                    pass

        # Extract mission success XP (from first/success outcome only, not all outcomes)
        total_rep_xp = _extract_mission_xp(root, reputation_lookup)
        if total_rep_xp > 0:
            lines.append(f"Reputation XP: +{total_rep_xp:,}")

    except Exception:
        pass

    return "\\n".join(lines) if lines else ""


def build_blueprint_pool_lookup(
    pool_dir: Path,
    bp_dir: Path,
    entity_names: dict[str, str],
) -> dict[str, list[str]]:
    """Build mapping of blueprint pool UUID → list of craftable item display names.

    Args:
        pool_dir: Directory containing BlueprintPoolRecord XMLs (blueprintmissionpools)
        bp_dir: Directory containing CraftingBlueprintRecord XMLs (blueprints/crafting)
        entity_names: UUID → display name lookup for resolving crafted item entities

    Returns:
        Dict mapping pool __ref UUID → sorted list of item display names
    """
    if not pool_dir.exists() or not bp_dir.exists():
        return {}

    # Index all blueprint files by __ref UUID → entityClass UUID
    bp_entity: dict[str, str] = {}
    for xml_file in bp_dir.rglob("*.xml"):
        try:
            root = ET.parse(xml_file).getroot()
            ref = root.get("__ref", "")
            if not ref:
                continue
            for elem in root.iter():
                if elem.get("__polymorphicType") == "CraftingProcess_Creation":
                    bp_entity[ref] = elem.get("entityClass", "")
                    break
        except ET.ParseError:
            continue

    # Build pool UUID → item names
    pool_items: dict[str, list[str]] = {}
    for xml_file in pool_dir.rglob("*.xml"):
        try:
            root = ET.parse(xml_file).getroot()
            pool_uuid = root.get("__ref", "")
            if not pool_uuid:
                continue
            names = []
            for elem in root.iter("BlueprintReward"):
                bp_ref = elem.get("blueprintRecord", "")
                if bp_ref and bp_ref in bp_entity:
                    entity_ref = bp_entity[bp_ref]
                    if entity_ref in entity_names:
                        name = entity_names[entity_ref]
                        if name not in names:
                            names.append(name)
            if names:
                pool_items[pool_uuid] = sorted(names)
        except ET.ParseError:
            continue

    logger.info(f"Blueprint pool lookup: {len(pool_items)} pools with items")
    return pool_items


def scan_contract_generators(contractgen_dir: Path, reputation_lookup: dict[str, int] | None = None, blueprint_pools: dict[str, list[str]] | None = None) -> tuple[dict[str, list[tuple[str, int, int, str]]], dict[str, list[str]]]:
    """Scan contract generator XMLs for mission variants with different systems.

    Returns tuple of:
        - missions: dict mapping title_key → [(system_name, success_xp, failure_xp, desc_key), ...]
        - mission_blueprints: dict mapping title_key → list of craftable item display names
    Sorted by system name for consistent output.
    """
    if not contractgen_dir.exists():
        return {}, {}

    reputation_lookup = reputation_lookup or {}
    blueprint_pools = blueprint_pools or {}
    missions: dict[str, list[tuple[str, int, str]]] = {}
    mission_blueprints: dict[str, list[str]] = {}

    try:
        for xml_file in contractgen_dir.rglob("*.xml"):
            try:
                root = ET.parse(xml_file).getroot()
            except ET.ParseError:
                continue

            # Process all ContractGeneratorHandler_Career elements
            for handler in root.findall(".//ContractGeneratorHandler_Career"):
                debug_name = handler.get("debugName", "")

                # Try to extract a system name from debugName for labelling variants
                system_name = debug_name or "Unknown"
                known_systems = {"Stanton", "Pyro", "Nyx", "Desert", "ArcCorp", "Crusader"}
                if debug_name:
                    parts = debug_name.split("_")
                    for part in reversed(parts):
                        if part in known_systems:
                            system_name = part
                            break

                # Find all CareerContract elements
                contracts = handler.findall(".//CareerContract")

                for contract in contracts:
                    try:
                        # Extract title and description keys
                        title_param = contract.find(".//ContractStringParam[@param='Title']")
                        desc_param = contract.find(".//ContractStringParam[@param='Description']")

                        if title_param is None:
                            continue

                        title_key = title_param.get("value", "").lstrip("@")
                        desc_key = desc_param.get("value", "").lstrip("@") if desc_param is not None else ""

                        if not title_key:
                            continue

                        # Extract blueprint pool UUID if present
                        for bp_elem in contract.iter("BlueprintRewards"):
                            pool_uuid = bp_elem.get("blueprintPool", "")
                            null_uuid = "00000000-0000-0000-0000-000000000000"
                            if pool_uuid and pool_uuid != null_uuid and pool_uuid in blueprint_pools:
                                if title_key not in mission_blueprints:
                                    mission_blueprints[title_key] = blueprint_pools[pool_uuid]

                        # Extract XP from ContractResult_LegacyReputation blocks
                        # First block with positive XP = success, first with negative = failure
                        legacy_reps = contract.findall(".//ContractResult_LegacyReputation")
                        success_xp = 0
                        failure_xp = 0

                        for legacy_rep in legacy_reps:
                            rep_amount = legacy_rep.find("contractResultReputationAmounts")
                            if rep_amount is not None:
                                reward_uuid = rep_amount.get("reward")
                                if reward_uuid and reward_uuid in reputation_lookup:
                                    val = reputation_lookup[reward_uuid]
                                    if val > 0 and success_xp == 0:
                                        success_xp = val
                                    elif val < 0 and failure_xp == 0:
                                        failure_xp = val

                        if success_xp > 0:
                            if title_key not in missions:
                                missions[title_key] = []
                            missions[title_key].append((system_name, success_xp, failure_xp, desc_key))
                    except Exception as e:
                        pass

        # Sort variants by system name for consistent output (Stanton first, then others alphabetically)
        for title_key in missions:
            missions[title_key].sort(key=lambda v: (v[0] != "Stanton", v[0]))

    except Exception as e:
        logger.warning(f"Error scanning contract generators: {e}")

    logger.info(f"Contract generators: {len(missions)} missions, {len(mission_blueprints)} with blueprints")
    return missions, mission_blueprints


def _resolve_resource_uuids(bp_dir: Path) -> set[str]:
    """Collect all CraftingCost_Resource UUIDs referenced in blueprint XMLs."""
    uuids: set[str] = set()
    if not bp_dir.exists():
        return uuids
    for xml_file in bp_dir.rglob("*.xml"):
        try:
            root = ET.parse(xml_file).getroot()
            for elem in root.iter():
                if elem.get("__polymorphicType") == "CraftingCost_Resource":
                    r = elem.get("resource", "")
                    if r and r != "00000000-0000-0000-0000-000000000000":
                        uuids.add(r)
        except ET.ParseError:
            pass
    return uuids


def _build_uuid_to_commodity(uuids: set[str], carryables_dir: Path) -> dict[str, str]:
    """Map resource UUIDs to commodity internal names by scanning carryable entity files."""
    uuid_names: dict[str, str] = {}
    if not carryables_dir.exists() or not uuids:
        return uuid_names
    for xml_file in carryables_dir.rglob("*.xml"):
        try:
            content = xml_file.read_text(encoding="utf-8", errors="ignore")
            matched_uuids = [u for u in uuids if u in content]
            if not matched_uuids:
                continue
            fname = xml_file.stem
            m = re.search(r"commodity_(?:metal|mineral|minerals|nonmetal|gas)_(\w+?)(?:_[a-d])?$", fname)
            if m:
                commodity = m.group(1).lower()
                for uid in matched_uuids:
                    uuid_names[uid] = commodity
        except Exception:
            pass
    return uuid_names


def _condense_crafted_items(items_list: list[tuple[str, str]]) -> list[str]:
    """Condense crafted items into readable summary lines, grouped by blueprint category."""
    from collections import defaultdict
    by_cat: dict[str, list[str]] = defaultdict(list)
    for cat, name in items_list:
        by_cat[cat].append(name)
    lines = []
    for cat in sorted(by_cat.keys()):
        names = sorted(set(by_cat[cat]))
        parts = cat.split("/")
        if "ammo" in cat:
            ammo_type = parts[-1].title() if len(parts) > 2 else "Ammo"
            lines.append(f"{ammo_type} Ammo")
            continue
        if "weapons" in cat:
            base_names = set()
            for n in names:
                clean = re.sub(r'\s*"[^"]*"\s*', ' ', n).strip()
                clean = re.sub(r'\s+', ' ', clean)
                base_names.add(clean)
            if len(base_names) <= 3:
                lines.append(", ".join(sorted(base_names)))
            else:
                weapon_type = parts[-1].title()
                lines.append(f"{weapon_type}s ({len(base_names)} types)")
            continue
        if "armour" in cat:
            weight = parts[-1].title() if len(parts) > 2 else ""
            armour_type = parts[-2].title() if len(parts) > 2 else "Armour"
            set_names = set()
            for n in names:
                m2 = re.match(r'^([\w-]+(?:\s[\w-]+)?)\s+(?:Arms|Core|Legs|Helmet|Backpack|Suit|Armor)', n)
                if m2:
                    set_names.add(m2.group(1))
                else:
                    set_names.add(n.split()[0] if n else n)
            if len(set_names) <= 3:
                label = ", ".join(sorted(set_names))
            else:
                label = f"{len(set_names)} sets"
            if weight and armour_type != weight:
                lines.append(f"{label} ({weight} {armour_type})")
            else:
                lines.append(f"{label} ({armour_type})")
            continue
        lines.append(f"{cat}: {len(names)} items")
    return lines


def scan_crafting_blueprints(
    bp_dir: Path,
    carryables_dir: Path,
    entity_names: dict[str, str],
    loc: dict[str, str],
) -> dict[str, str]:
    """Scan crafting blueprints and produce commodity_crafting_stats entries.

    Returns a dict of localization key → augmented value for commodity names and
    descriptions that are used as crafting materials.
    """
    from collections import defaultdict
    import os

    if not bp_dir.exists():
        logger.info("No crafting blueprints directory found")
        return {}

    # Step 1: Collect resource UUIDs from blueprints
    resource_uuids = _resolve_resource_uuids(bp_dir)
    logger.info(f"Found {len(resource_uuids)} unique resource UUIDs in blueprints")

    # Step 2: Resolve UUIDs to commodity names via carryables
    uuid_names = _build_uuid_to_commodity(resource_uuids, carryables_dir)
    logger.info(f"Resolved {len(uuid_names)} resource UUIDs to commodity names")

    # Step 3: Parse blueprints to build commodity → crafted items map
    commodity_items: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for xml_file in sorted(bp_dir.rglob("*.xml")):
        try:
            root = ET.parse(xml_file).getroot()
            rel = xml_file.relative_to(bp_dir)
            category = str(rel.parent).replace(os.sep, "/")
            item_name = xml_file.stem.replace("bp_craft_", "")
            # Try to resolve display name from entity reference
            for elem in root.iter():
                if elem.get("__polymorphicType") == "CraftingProcess_Creation":
                    entity_ref = elem.get("entityClass", "")
                    if entity_ref in entity_names:
                        item_name = entity_names[entity_ref]
                    break
            materials: set[str] = set()
            for elem in root.iter():
                if elem.get("__polymorphicType") == "CraftingCost_Resource":
                    r = elem.get("resource", "")
                    if r in uuid_names:
                        materials.add(uuid_names[r])
            for mat in materials:
                commodity_items[mat].append((category, item_name))
        except ET.ParseError:
            pass

    # Commodity internal name → (name_loc_key, desc_loc_key)
    commodity_loc = {
        "agricium": ("items_commodities_agricium", "items_commodities_agricium_desc"),
        "aluminium": ("items_commodities_aluminum_ore", "items_commodities_aluminum_ore_desc"),
        "aslarite": ("items_commodities_aslarite", "items_commodities_aslarite_desc"),
        "beryl": ("items_commodities_beryl", "items_commodities_beryl_desc"),
        "copper": ("items_commodities_copper", "items_commodities_copper_desc"),
        "corundum": ("items_commodities_corundum", "items_commodities_corundum_desc"),
        "gold": ("items_commodities_gold", "items_commodities_gold_desc"),
        "hephaestanite": ("items_commodities_hephaestanite", "items_commodities_hephaestanite_desc"),
        "iron": ("items_commodities_iron", "items_commodities_iron_desc"),
        "laranite": ("items_commodities_laranite", "items_commodities_laranite_desc"),
        "lindinium": ("items_commodities_lindinium", "items_commodities_lindinium_des"),
        "ouratite": ("items_commodities_ouratite", "items_commodities_ouratite_desc"),
        "quartz": ("items_commodities_quartz", "items_commodities_quartz_desc"),
        "riccite": ("items_commodities_riccite", "items_commodities_riccite_des"),
        "savrilium": ("items_commodities_savrilium", "items_commodities_savrilium_des"),
        "silicon": ("items_commodities_silicon", "items_commodities_silicon_desc"),
        "stileron": ("items_commodities_stileron", "items_commodities_stileron_des"),
        "taranite": ("items_commodities_taranite", "items_commodities_taranite_desc"),
        "tin": ("items_commodities_tin", "items_commodities_tin_desc"),
        "titanium": ("items_commodities_titanium", "items_commodities_titanium_desc"),
        "torite": ("items_commodities_torite", "items_commodities_torite_des"),
        "tungsten": ("items_commodities_tungsten", "items_commodities_tungsten_desc"),
    }

    # Build output
    out: dict[str, str] = {}
    for commodity in sorted(commodity_items.keys()):
        if commodity not in commodity_loc:
            continue
        name_key, desc_key = commodity_loc[commodity]

        base_name = loc.get(name_key, "")
        if base_name:
            out[name_key] = f"{base_name} <EM4>[CF]</EM4>"

        base_desc = loc.get(desc_key, "")
        if base_desc:
            condensed = _condense_crafted_items(commodity_items[commodity])
            bp_block = "\\n".join(f"- {line}" for line in condensed)
            enhancements_block = f"== Blueprint Data ==\\n{bp_block}"
            out[desc_key] = f"{base_desc}\\n\\n{enhancements_block}"

    # ── Augment Mining Compendium journal entry with crafting usage ──────────
    journal_title_key = "Journal_General_Mining_Compendium_Title"
    journal_content_key = "Journal_General_Mining_Compendium_Content"
    base_title = loc.get(journal_title_key, "")
    base_content = loc.get(journal_content_key, "")

    if base_title and base_content:
        # Mark the title as edited by the app
        out[journal_title_key] = f"{base_title} <EM4>[SCLE]</EM4>"

        # Build mineral name → condensed crafting summary (case-insensitive match)
        mineral_crafting: dict[str, str] = {}
        # Map display names to internal names: "Aluminium" in journal vs "aluminium" internal
        # The journal uses the display mineral name as the first word before " - "
        for internal_name, items in commodity_items.items():
            condensed = _condense_crafted_items(items)
            if condensed:
                mineral_crafting[internal_name] = ", ".join(condensed)

        # Parse content lines (separated by \\n\\n) and augment mineral entries
        lines = base_content.split("\\n\\n")
        augmented_lines = []
        for line in lines:
            # Each mineral line: "Agricium - ARC-L3, Cellin, ..."
            dash_idx = line.find(" - ")
            if dash_idx > 0:
                mineral_display = line[:dash_idx].strip()
                mineral_lower = mineral_display.lower()
                if mineral_lower in mineral_crafting:
                    line = f"{line}\\n  >> Crafting: {mineral_crafting[mineral_lower]}"
            augmented_lines.append(line)

        out[journal_content_key] = "\\n\\n".join(augmented_lines)
        logger.info(f"Journal: augmented Mining Compendium with crafting data for {len(mineral_crafting)} minerals")

    logger.info(f"Crafting: {len(out)} entries augmented from {len(commodity_items)} commodities")
    return out


def enhancements_weapon(root: ET.Element, ammo_lookup: dict[str, ET.Element],
                 loc: dict | None = None,
                 magazine_lookup: dict[str, tuple[str, str]] | None = None) -> str:
    """Ship or FPS weapon stats."""
    fr    = _fire_rate(root)
    modes = _fire_modes(root, loc)
    pwr   = _find_resource(root, "Power")

    # Component health / signatures / heat
    comp_hp  = _attr(root, "SHealthComponentParams", "Health")
    em_sig   = _attr(root, "EMSignature", "nominalSignature")
    ir_sig   = _attr(root, "IRSignature", "nominalSignature")
    overheat = _attr(root, "itemResourceParams", "overheatTemperature")

    # Weight (mass from physics controller)
    weight = None
    for elem in root.iter():
        pt = elem.get("__polymorphicType", "")
        if "RigidPhysics" in pt or "StaticPhysics" in pt:
            mass_val = elem.get("Mass")
            if mass_val:
                try:
                    weight = float(mass_val)
                except ValueError:
                    pass
            break

    # Pellet count (shotguns fire multiple pellets per shot)
    pellet_count = 1
    for elem in root.iter():
        if "SProjectileLauncher" in (elem.get("__polymorphicType", "") + elem.tag):
            try:
                pc = int(elem.get("pelletCount", "1"))
                if pc > 1:
                    pellet_count = pc
            except ValueError:
                pass
            break

    # Ammo damage — look up the ammo record by GUID
    ammo_container = _find(root, "SAmmoContainerComponentParams")
    ammo_record_id = ammo_container.get("ammoParamsRecord") if ammo_container is not None else None
    capacity = None

    # Fallback: for FPS weapons without inline ammo container, follow the magazine port chain
    if not ammo_record_id or ammo_record_id == "00000000-0000-0000-0000-000000000000":
        if magazine_lookup:
            for elem in root.iter():
                port_name = elem.get("itemPortName", "")
                entity_class = elem.get("entityClassName", "")
                if "magazine" in port_name.lower() and entity_class:
                    mag_info = magazine_lookup.get(entity_class)
                    if mag_info:
                        ammo_record_id, mag_capacity = mag_info
                        if mag_capacity:
                            capacity = mag_capacity
                    break

    total_dmg = breakdown = proj_speed = proj_lifetime = None
    dps = None
    ammo_root = None
    dmg_drop_min_dist = dmg_drop_per_m = dmg_drop_min = None
    if ammo_record_id and ammo_record_id != "00000000-0000-0000-0000-000000000000":
        ammo_root = ammo_lookup.get(ammo_record_id)
        if ammo_root is not None:
            total_dmg, breakdown = _ammo_damage_breakdown(ammo_root)
            # Multiply by pellet count for shotguns
            if pellet_count > 1 and total_dmg:
                total_dmg *= pellet_count
                breakdown = {k: v * pellet_count for k, v in breakdown.items()}
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

            # Damage drop-off parameters
            for elem in ammo_root.iter():
                tag = elem.tag
                if tag == "damageDropMinDistance":
                    for d in elem:
                        if d.get("__polymorphicType") == "DamageInfo" or "DamageInfo" in d.tag:
                            try:
                                dmg_drop_min_dist = float(d.get("DamagePhysical", 0)) + float(d.get("DamageEnergy", 0))
                            except ValueError:
                                pass
                elif tag == "damageDropPerMeter":
                    for d in elem:
                        if d.get("__polymorphicType") == "DamageInfo" or "DamageInfo" in d.tag:
                            try:
                                dmg_drop_per_m = float(d.get("DamagePhysical", 0)) + float(d.get("DamageEnergy", 0))
                            except ValueError:
                                pass
                elif tag == "damageDropMinDamage":
                    for d in elem:
                        if d.get("__polymorphicType") == "DamageInfo" or "DamageInfo" in d.tag:
                            try:
                                dmg_drop_min = float(d.get("DamagePhysical", 0)) + float(d.get("DamageEnergy", 0))
                            except ValueError:
                                pass

    # Capacity: energy weapons use regen pool; ballistic use fixed container
    regen    = _find(root, "SWeaponRegenConsumerParams")
    regen_rate = regen_cooldown = regen_cost = None
    if regen is not None:
        if not capacity:
            capacity = regen.get("maxAmmoLoad")
        regen_rate    = regen.get("requestedRegenPerSec")
        regen_cooldown = regen.get("regenerationCooldown")
        regen_cost    = regen.get("regenerationCostPerBullet")
    elif ammo_container is not None and not capacity:
        capacity = ammo_container.get("maxAmmoCount")

    lines = []
    if weight is not None and weight > 0:
        lines.append(f"Weight: {weight:.1f} kg")
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
        pellet_str = f" x{pellet_count}" if pellet_count > 1 else ""
        dmg_part = f"Dmg/Shot: {_fmt(total_dmg, '', 1)}{pellet_str}{type_str}"
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
            speed_f = float(proj_speed)
            lifetime_f = float(proj_lifetime)
            rng_m = speed_f * lifetime_f
            if rng_m >= 1000:
                lines.append(f"Velocity: {_fmt(proj_speed, ' m/s')}  |  Range: {rng_m / 1000:,.1f} km")
            else:
                lines.append(f"Velocity: {_fmt(proj_speed, ' m/s')}  |  Range: {rng_m:,.0f} m")
        except (TypeError, ValueError):
            pass

    # Damage drop-off
    if dmg_drop_min_dist is not None and dmg_drop_min_dist > 0:
        drop_parts = [f"Full Dmg to: {dmg_drop_min_dist:.0f} m"]
        if dmg_drop_per_m is not None and dmg_drop_per_m > 0:
            drop_parts.append(f"Drop: -{dmg_drop_per_m:.2f}/m")
        if dmg_drop_min is not None and dmg_drop_min > 0:
            drop_parts.append(f"Min Dmg: {dmg_drop_min:.1f}")
        lines.append("  |  ".join(drop_parts))

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


# ── Ship enhancements (DataForge-based) ──────────────────────────────────────────────

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


def enhancements_ship_dataforge(
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
            block = enhancements_ship_dataforge(root, controller_root, loc)
        except Exception as e:
            logger.warning(f"Ship enhancements failed for {xml_file.name}: {e}")
            continue

        if block:
            # Deduplicate: first match for a given key wins
            if loc_key not in out:
                out[loc_key] = append_enhancements(base_value, block)
                matched += 1
        else:
            missed += 1

    logger.info(f"Spaceships: {matched} matched, {missed} no enhancements/key, {skipped} skipped (AI/templates)")
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


def build_magazine_lookup(scitem_dir: Path) -> dict[str, tuple[str, str]]:
    """Build a lookup from magazine entity class name → (ammoParamsRecord, maxAmmoCount).

    Scans all scitem entities for SAmmoContainerComponentParams to find magazine
    entities that link weapons to their ammo params.
    """
    lookup: dict[str, tuple[str, str]] = {}
    if not scitem_dir.exists():
        return lookup
    for xml_file in scitem_dir.rglob("*.xml"):
        try:
            root = ET.parse(xml_file).getroot()
            for elem in root.iter():
                if elem.get("__polymorphicType") == "SAmmoContainerComponentParams":
                    ammo_ref = elem.get("ammoParamsRecord", "")
                    max_ammo = elem.get("maxAmmoCount", "")
                    # Entity class name is the part after the dot in the root tag
                    entity_name = root.tag.split(".")[-1] if "." in root.tag else xml_file.stem
                    if ammo_ref and ammo_ref != "00000000-0000-0000-0000-000000000000":
                        lookup[entity_name] = (ammo_ref, max_ammo)
                    break
        except ET.ParseError:
            pass
    return lookup


# ── DataForge directory scanner ───────────────────────────────────────────────

def scan_entity_dir(
    entity_dir: Path,
    enhancement_fn,
    ammo_lookup: dict | None = None,
    loc: dict | None = None,
    loc_key_fn = None,
    generate_name_tags: bool = False,
) -> dict[str, str]:
    """
    Scan all XML files in entity_dir, extract localization key + enhancements,
    and return {loc_key: augmented_value} for keys found in `loc`.

    ammo_lookup is passed to enhancement_fn only when it accepts it (weapons).
    loc is the base.ini localization dict for value lookup.
    loc_key_fn is an optional custom function to extract the localization key (defaults to _loc_key).
    generate_name_tags: if True, also generate item_Name* entries with [CLASS-SIZE-GRADE] tags
        derived from the component description text.
    """
    if loc_key_fn is None:
        loc_key_fn = _loc_key

    out: dict[str, str] = {}
    matched = missed = skipped = 0

    for xml_file in entity_dir.rglob("*.xml"):
        try:
            root = ET.parse(xml_file).getroot()
        except ET.ParseError:
            continue

        key = loc_key_fn(root)
        if not key:
            skipped += 1
            continue

        base_value = (loc or {}).get(key)
        if base_value is None:
            missed += 1
            continue

        try:
            if ammo_lookup is not None:
                enhancements_block = enhancement_fn(root, ammo_lookup)
            else:
                enhancements_block = enhancement_fn(root)
        except Exception as e:
            logger.warning(f"Enhancements failed for {xml_file.name}: {e}")
            continue

        if enhancements_block:
            out[key] = append_enhancements(base_value, enhancements_block)
            matched += 1
        else:
            missed += 1

        # Generate item_Name* tag from description metadata (e.g., [MIL-S1-A])
        if generate_name_tags and loc:
            name_key = _loc_name_key(root)
            if name_key:
                name_value = loc.get(name_key)
                if name_value:
                    tag = _component_name_tag(base_value)
                    if tag:
                        out[name_key] = f"{name_value} {tag}"

    logger.info(f"{entity_dir.name}: {matched} matched, {missed} no enhancements, {skipped} no loc key")
    return out


# ── Main ──────────────────────────────────────────────────────────────────────

def main(base_ini_path: Path, forge_dir: Path | None = None,
         categories: set[str] | None = None) -> None:
    import sys as sys_mod
    def _flush():
        if sys_mod.stdout is not None:
            sys_mod.stdout.flush()
        if sys_mod.stderr is not None:
            sys_mod.stderr.flush()

    def _want(cat: str) -> bool:
        """Return True if *cat* should be generated (None means all)."""
        return categories is None or cat in categories

    logger.info("=== SC Enhancements INI Generator (DataForge edition) ===")
    if categories is not None:
        logger.info(f"Selective generation: {', '.join(sorted(categories))}")
    _flush()

    if forge_dir is None:
        forge_dir = DEFAULT_FORGE_DIR

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Parse base.ini ─────────────────────────────────────────────────────────
    logger.info(f"CHECKPOINT: Parsing base.ini: {base_ini_path}")
    _flush()
    if not base_ini_path.exists():
        raise FileNotFoundError(f"base.ini not found at {base_ini_path}")
    loc = parse_ini(base_ini_path)
    logger.info(f"CHECKPOINT: Loaded {len(loc):,} localization keys")
    _flush()

    # ── Check DataForge cache ─────────────────────────────────────────────────
    logger.info("CHECKPOINT: Checking DataForge cache...")
    _flush()
    records = forge_dir / "raw" / "libs" / "foundry" / "records"
    if not forge_dir.exists() or not records.exists():
        raise FileNotFoundError(
            f"DataForge cache not found at {forge_dir}\n"
            "Run 'Extract DataForge' in the app first (Enhancements tab)."
        )

    # ── Build ammo lookups (needed by ship_weapon_descs / fps_weapon_descs) ──
    vehicle_ammo: dict = {}
    fps_ammo: dict = {}
    mag_lookup: dict = {}
    if _want("ship_weapon_descs") or _want("fps_weapon_descs"):
        logger.info("CHECKPOINT: Building ammo damage lookups…")
        _flush()
        vehicle_ammo = build_ammo_lookup(records / "ammoparams" / "vehicle")
        fps_ammo     = build_ammo_lookup(records / "ammoparams" / "fps")
        logger.info(f"CHECKPOINT: Vehicle ammo: {len(vehicle_ammo)} records, FPS ammo: {len(fps_ammo)} records")
        _flush()

        # Build magazine lookup (maps magazine entity names to their ammo params records)
        logger.info("CHECKPOINT: Building magazine lookup…")
        mag_lookup = build_magazine_lookup(records / "entities" / "scitem")
        logger.info(f"CHECKPOINT: Magazine lookup: {len(mag_lookup)} entries")
        _flush()

    # ── Process components ────────────────────────────────────────────────────
    ships_scitem = records / "entities" / "scitem" / "ships"
    out_components: dict[str, str] = {}

    if _want("component_descs"):
        logger.info("CHECKPOINT: Processing ship components…")
        _flush()
        for subdir, fn in [
            ("shieldgenerator", enhancements_shield),
            ("cooler",          enhancements_cooler),
            ("powerplant",      enhancements_powerplant),
            ("quantumdrive",    enhancements_quantum_drive),
        ]:
            logger.info(f"CHECKPOINT: Processing {subdir}...")
            _flush()
            out_components.update(scan_entity_dir(ships_scitem / subdir, fn, loc=loc, generate_name_tags=True))

        # ── Process radar/sensors ─────────────────────────────────────────────
        logger.info("Processing radar components…")
        scitem_dir = records / "entities" / "scitem"
        ships_scitem = scitem_dir / "ships"
        radar_dir = ships_scitem / "radar"

        if radar_dir.exists():
            logger.info(f"Processing radars from {radar_dir}…")
            out_components.update(scan_entity_dir(radar_dir, enhancements_radar, loc=loc))
        else:
            logger.info("No radar directory found in cache")

    # ── Process missiles/rockets/bombs ────────────────────────────────────────
    out_missiles: dict[str, str] = {}
    if _want("missile_enhancements"):
        logger.info("Processing missile/rocket/bomb enhancements…")
        weapons_dir = ships_scitem / "weapons"
        for missile_dir in [
            weapons_dir / "missiles",
            weapons_dir / "rocket_pods",
        ]:
            if missile_dir.exists():
                logger.info(f"Processing from {missile_dir}…")
                out_missiles.update(scan_entity_dir(missile_dir, enhancements_missile, loc=loc))

    # ── Process ship weapons ──────────────────────────────────────────────────
    out_ship_weapons: dict[str, str] = {}
    if _want("ship_weapon_descs"):
        logger.info("CHECKPOINT: Processing ship weapons…")
        _flush()
        weapons_dir = ships_scitem / "weapons"
        if weapons_dir.exists():
            out_ship_weapons = scan_entity_dir(
                weapons_dir,
                lambda root: enhancements_weapon(root, vehicle_ammo, loc),
                loc=loc,
            )
        logger.info(f"CHECKPOINT: Finished ship weapons ({len(out_ship_weapons)} entries)")
        _flush()

    # ── Process FPS weapons ───────────────────────────────────────────────────
    out_fps_weapons: dict[str, str] = {}
    if _want("fps_weapon_descs"):
        logger.info("CHECKPOINT: Processing FPS weapons…")
        _flush()
        fps_dir = records / "entities" / "scitem" / "weapons" / "fps_weapons"
        if fps_dir.exists():
            out_fps_weapons = scan_entity_dir(
                fps_dir,
                lambda root: enhancements_weapon(root, fps_ammo, loc, mag_lookup),
                loc=loc,
            )
        logger.info(f"CHECKPOINT: Finished FPS weapons ({len(out_fps_weapons)} entries)")
        _flush()

    # ── Process ships (DataForge spaceship entities + flight controllers) ──────
    out_ships: dict[str, str] = {}
    if _want("ship_descs"):
        logger.info("CHECKPOINT: Building flight controller lookup…")
        _flush()
        controller_dir = records / "entities" / "scitem" / "ships" / "controller"
        controller_lookup = build_controller_lookup(controller_dir)
        logger.info(f"CHECKPOINT: Controllers: {len(controller_lookup)} loaded")
        _flush()

        logger.info("CHECKPOINT: Processing ship descriptions…")
        _flush()
        spaceships_dir = records / "entities" / "spaceships"
        out_ships = scan_spaceships(spaceships_dir, controller_lookup, loc)
        logger.info(f"CHECKPOINT: Finished ships ({len(out_ships)} entries)")
        _flush()

    # ── Build entity name lookup (needed by mission_rewards AND commodity_crafting) ──
    scitem_dir = records / "entities" / "scitem"
    entity_names: dict[str, str] = {}
    if _want("mission_rewards") or _want("commodity_crafting"):
        logger.info("CHECKPOINT: Building entity name lookup…")
        _flush()
        if scitem_dir.exists():
            for xml_file in scitem_dir.rglob("*.xml"):
                try:
                    root = ET.parse(xml_file).getroot()
                    ref = root.get("__ref", "")
                    if not ref:
                        continue
                    for elem in root.iter():
                        name_attr = elem.get("Name", "")
                        if name_attr and name_attr.startswith("@"):
                            loc_key = name_attr.lstrip("@")
                            display = loc.get(loc_key, loc_key)
                            entity_names[ref] = display
                            break
                except ET.ParseError:
                    pass
        logger.info(f"Entity name lookup: {len(entity_names)} entries")
        _flush()

    # ── Mission/contract processing ──────────────────────────────────────────
    out_missions: dict[str, str] = {}
    if _want("mission_rewards"):
        # ── Build reputation XP lookup ───────────────────────────────────────
        logger.info("CHECKPOINT: Building reputation XP lookup…")
        _flush()
        reputation_lookup: dict[str, int] = {}
        rep_rewards_dir = records / "reputation" / "rewards" / "missionrewards_reputation"

        if rep_rewards_dir.exists():
            for xml_file in rep_rewards_dir.rglob("*.xml"):
                try:
                    root = ET.parse(xml_file).getroot()
                    uuid = root.get("__ref")
                    rep_amount = root.get("reputationAmount")
                    if uuid and rep_amount:
                        try:
                            reputation_lookup[uuid] = int(float(rep_amount))
                        except (ValueError, TypeError):
                            pass
                except ET.ParseError:
                    continue
        logger.info(f"CHECKPOINT: Loaded {len(reputation_lookup)} reputation reward definitions")
        _flush()

        # ── Process missions/contracts ────────────────────────────────────────
        logger.info("CHECKPOINT: Processing mission/contract rewards…")
        _flush()

        # Primary mission directories: missionbroker/pu_missions is the main source (uses _mission_loc_key)
        pu_missions_dir = records / "missionbroker" / "pu_missions"
        if pu_missions_dir.exists():
            logger.info(f"CHECKPOINT: Processing {pu_missions_dir.name}…")
            _flush()
            out_missions.update(scan_entity_dir(
                pu_missions_dir,
                lambda root: enhancements_mission(root, reputation_lookup),
                loc=loc,
                loc_key_fn=_mission_loc_key
            ))

        # Also check entity-based missions (use standard _loc_key)
        for mission_dir in [
            records / "entities" / "missions",
            records / "entities" / "contracts",
            records / "entities" / "jobterminal",
        ]:
            if mission_dir.exists():
                logger.info(f"CHECKPOINT: Processing {mission_dir.name}…")
                _flush()
                out_missions.update(scan_entity_dir(
                    mission_dir,
                    lambda root: enhancements_mission(root, reputation_lookup),
                    loc=loc
                ))

        logger.info(f"CHECKPOINT: Finished missions ({len(out_missions)} entries)")
        _flush()

        # ── Augment mission titles with XP ──────────────────────────────────
        logger.info("CHECKPOINT: Augmenting mission titles with XP…")
        _flush()
        mission_titles_augmented = 0

        # Build blueprint pool lookup for mission rewards
        logger.info("CHECKPOINT: Building blueprint pool lookup…")
        _flush()
        pool_dir = records / "crafting" / "blueprintrewards" / "blueprintmissionpools"
        bp_dir = records / "crafting" / "blueprints" / "crafting"
        blueprint_pools = build_blueprint_pool_lookup(pool_dir, bp_dir, entity_names)
        _flush()

        # Process contract generator missions (can have multiple variants per title key)
        logger.info("CHECKPOINT: Processing contract generator mission variants…")
        _flush()
        contractgen_dir = records / "contracts" / "contractgenerator"
        contractgen_missions, mission_blueprints = scan_contract_generators(
            contractgen_dir, reputation_lookup, blueprint_pools
        )
        logger.info(f"CHECKPOINT: Processed {len(contractgen_missions)} contract generator mission variants, {len(mission_blueprints)} with blueprints")
        _flush()

        known_system_names = {"Stanton", "Pyro", "Nyx", "Desert", "ArcCorp", "Crusader"}

        for title_key, variants in contractgen_missions.items():
            base_title = (loc or {}).get(title_key)
            if not base_title:
                continue

            # Collect unique (success_xp, failure_xp) tiers, preserving order
            seen_tiers: list[tuple[int, int]] = []
            for _, sxp, fxp, _ in variants:
                tier = (sxp, fxp)
                if tier not in seen_tiers:
                    seen_tiers.append(tier)

            unique_xp = sorted(set(sxp for sxp, _ in seen_tiers))

            # Title: append [BP] tag if blueprints exist, then [XP] tag
            has_blueprints = title_key in mission_blueprints
            augmented_title = base_title
            if has_blueprints:
                augmented_title += " <EM4>[BP]</EM4>"
            if len(unique_xp) == 1:
                augmented_title += f" [{unique_xp[0]:,} XP]"
            else:
                augmented_title += f" [{min(unique_xp):,}\u2013{max(unique_xp):,} XP]"
            out_missions[title_key] = augmented_title
            mission_titles_augmented += 1

            # Description: append blueprint list (if any), then XP/reputation data
            desc_key = variants[0][3]
            if desc_key and desc_key in loc:
                base_desc = loc[desc_key]

                # Build XP block
                if len(seen_tiers) == 1:
                    sxp, fxp = seen_tiers[0]
                    xp_block = f"Reputation XP: +{sxp:,}"
                    if fxp < 0:
                        xp_block += f"\\nFailure Penalty: {fxp:,} XP"
                else:
                    xp_lines = []
                    for i, (sxp, fxp) in enumerate(sorted(seen_tiers, key=lambda t: t[0]), 1):
                        line = f"Tier {i}: +{sxp:,} XP"
                        if fxp < 0:
                            line += f" (Failure: {fxp:,})"
                        xp_lines.append(line)
                    xp_block = "\\n".join(xp_lines)

                # Append blueprint list before XP data if available
                if has_blueprints:
                    bp_list = "\\n".join(f"- {name}" for name in mission_blueprints[title_key])
                    base_desc += f"\\n\\n<EM4>Potential Blueprints</EM4>\\n{bp_list}"

                augmented_desc = append_enhancements(base_desc, xp_block)
                out_missions[desc_key] = augmented_desc

        # Process mission titles from the primary mission directory (pu_missions)
        pu_missions_dir = records / "missionbroker" / "pu_missions"
        if pu_missions_dir.exists():
            for xml_file in pu_missions_dir.rglob("*.xml"):
                try:
                    root = ET.parse(xml_file).getroot()

                    # Get both title and description keys
                    title_attr = root.get("title", "")
                    desc_attr = root.get("description", "")

                    if not title_attr.startswith("@") or not desc_attr.startswith("@"):
                        continue

                    title_key = title_attr.lstrip("@")
                    desc_key = desc_attr.lstrip("@")

                    # Skip if already processed by contract generator (check if in contractgen_missions)
                    if title_key in contractgen_missions:
                        continue

                    # Extract XP and augment title
                    total_rep_xp = _extract_mission_xp(root, reputation_lookup)
                    if total_rep_xp > 0:
                        base_title = (loc or {}).get(title_key)
                        if base_title:
                            augmented_title = f"{base_title} [{total_rep_xp:,} XP]"
                            out_missions[title_key] = augmented_title
                            mission_titles_augmented += 1
                except (ET.ParseError, Exception):
                    continue

        logger.info(f"CHECKPOINT: Augmented {mission_titles_augmented} mission titles with XP")
        _flush()

        # ── Mission XP coverage report ────────────────────────────────────────
        # Count title keys that were augmented with XP vs those with descriptions
        # but no XP annotation (i.e. the stats generator found the mission but
        # couldn't extract reputation data)
        titles_with_xp = {k for k in out_missions if re.search(r'\[\d', out_missions[k])}
        desc_keys = {k for k in out_missions if k not in titles_with_xp}
        # Titles we know about (from pu_missions XMLs) but didn't augment
        titles_skipped_no_xp = 0
        titles_skipped_reasons: dict[str, list[str]] = {
            "no_rep_data": [],
            "no_base_title": [],
        }
        if pu_missions_dir.exists():
            for xml_file in pu_missions_dir.rglob("*.xml"):
                try:
                    root = ET.parse(xml_file).getroot()
                    title_attr = root.get("title", "")
                    desc_attr = root.get("description", "")
                    if not title_attr.startswith("@") or not desc_attr.startswith("@"):
                        continue
                    title_key = title_attr.lstrip("@")
                    if title_key in out_missions:
                        continue  # Already augmented
                    if title_key in contractgen_missions:
                        continue  # Handled by contract generator
                    titles_skipped_no_xp += 1
                    if _extract_mission_xp(root, reputation_lookup) <= 0:
                        titles_skipped_reasons["no_rep_data"].append(title_key)
                    elif not (loc or {}).get(title_key):
                        titles_skipped_reasons["no_base_title"].append(title_key)
                except Exception:
                    continue

        logger.info(
            f"Mission XP coverage: {len(titles_with_xp)} titles augmented, "
            f"{len(desc_keys)} descriptions augmented, "
            f"{titles_skipped_no_xp} titles skipped"
        )
        for reason, keys in titles_skipped_reasons.items():
            if keys:
                logger.info(f"  Skipped ({reason}): {len(keys)} — e.g. {', '.join(keys[:5])}")
        _flush()

    # ── Process crafting blueprints and augment commodities ──────────────────
    out_commodities: dict[str, str] = {}
    if _want("commodity_crafting"):
        logger.info("CHECKPOINT: Processing crafting blueprints…")
        _flush()

        bp_dir = records / "crafting" / "blueprints" / "crafting"
        carryables_dir = scitem_dir / "carryables"
        out_commodities = scan_crafting_blueprints(bp_dir, carryables_dir, entity_names, loc)

    # ── Write output ──────────────────────────────────────────────────────────
    logger.info("CHECKPOINT: Writing output files…")
    _flush()
    if _want("ship_descs"):
        write_ini(OUTPUT_DIR / "ships_desc_enhancements.ini",       out_ships)
    if _want("component_descs"):
        write_ini(OUTPUT_DIR / "components_desc_enhancements.ini",  out_components)
    if _want("ship_weapon_descs"):
        write_ini(OUTPUT_DIR / "ship_weapons_desc_enhancements.ini",out_ship_weapons)
    if _want("fps_weapon_descs"):
        write_ini(OUTPUT_DIR / "fps_weapons_desc_enhancements.ini", out_fps_weapons)
    if _want("mission_rewards"):
        write_ini(OUTPUT_DIR / "mission_rewards_enhancements.ini", out_missions)
    if _want("commodity_crafting"):
        write_ini(OUTPUT_DIR / "commodity_crafting_enhancements.ini", out_commodities)
    if _want("missile_enhancements"):
        write_ini(OUTPUT_DIR / "missile_enhancements.ini", out_missiles)

    total = (len(out_ships) + len(out_components) + len(out_ship_weapons) +
             len(out_fps_weapons) + len(out_missions) + len(out_commodities) + len(out_missiles))
    logger.info(f"Done — {total:,} total stat entries written to {OUTPUT_DIR}")


if __name__ == "__main__":
    base_ini  = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BASE_INI
    forge_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_FORGE_DIR
    main(base_ini, forge_dir)
