import re
from dataclasses import dataclass


@dataclass
class StringEntry:
    """Represents a localization string entry."""
    key: str
    source_file: str              # "global" or "vehicles"
    category: str                 # Extracted from key prefix
    original_value: str           # From merged sources (base file + others)
    custom_value: str             # From target_strings.ini (or empty)
    status: str                   # "Modified" | "Unmodified" | "New"

    @property
    def is_modified(self) -> bool:
        """Check if custom value differs from original."""
        return bool(self.custom_value and self.custom_value != self.original_value)

    @staticmethod
    def extract_category(key: str) -> str:
        """Extract category from key prefix.

        Rules:
        - Keys starting with `vehicle_Name` → category "Ships"
        - Keys starting with `item_Name(SHLD|POWR|COOL|QDRV|JUMP)` → category "Ship Items"
        - Mission-related keys (contracts, shubin, blackbox, hockrow, etc.) → "Missions"
        - Everything else → "Other"
        """
        if not key:
            return "Other"

        # Ship/vehicle names and descriptions: vehicle_NameANVL_Carrack, vehicle_DescANVL_Carrack -> Ships
        key_lower = key.lower()
        if key_lower.startswith("vehicle_name") or key_lower.startswith("vehicle_desc"):
            return "Ships"

        # Wikelo ship mods (TheCollector_ShipMod_*_VehicleName, _VehicleDesc,
        # _VehicleNameShort). Checked before mission-prefix fallthrough, which
        # would otherwise route TheCollector_* into "Missions".
        if key_lower.endswith(("_vehiclename", "_vehicledesc", "_vehiclenameshort")):
            return "Ships"

        # item_Name* / item_Desc* keys — resolve in priority order
        fps_weapon_words = ["_rifle_", "_pistol_", "_smg_", "_shotgun_", "_sniper_", "_launcher_", "_lmg_", "_hmg_", "_knife_", "_multi_"]
        if key_lower.startswith("item_name") or key_lower.startswith("item_desc"):
            # Turrets are ship items despite having the item_Name_/item_Desc_ prefix
            if key_lower.startswith("item_name_turret") or key_lower.startswith("item_desc_turret"):
                return "Ship Items"

            # Ship component type codes: SHLD, POWR, COOL, QDRV, JUMP, MISL, BOMB (check BEFORE FPS gear)
            # Handles both: item_NameQDRV_... and item_Name_QDRV_... (with or without underscore)
            # Case-insensitive matching for items with lowercase names
            components = ["SHLD", "POWR", "COOL", "QDRV", "JUMP", "MISL", "GMISL", "BOMB"]
            if any(
                key_lower.startswith(f"item_name{comp.lower()}_") or
                key_lower.startswith(f"item_desc{comp.lower()}_") or
                key_lower.startswith(f"item_name_{comp.lower()}_") or
                key_lower.startswith(f"item_desc_{comp.lower()}_")
                for comp in components
            ):
                return "Ship Items"

            # FPS weapons: check for FPS weapon words (catches GMNI/KSAR uppercase counterexamples)
            if any(w in key_lower for w in fps_weapon_words):
                return "Gear"

            # FPS armor/equipment/accessories
            if any(word in key_lower for word in ["armor", "helmet", "suit", "vest", "glasses", "_optics_", "_barrel_"]):
                return "Gear"

            # Case-based classification: the segment after item_Name/item_Desc reveals domain.
            # Uppercase = ship items (item_NameBEHR_*, item_DescAEGS_*),
            # lowercase = FPS gear (item_Namebehr_*, item_Descgmni_*).
            after = key[9:]  # both "item_Name" and "item_Desc" are 9 chars
            if after and not after.startswith('_'):
                if after[0].isupper():
                    return "Ship Items"
                else:
                    return "Gear"

            # item_Name_ keys: use size designator for ship weapons (_S1, _S02, _XL, etc.)
            if re.search(r'_S\d+|_X{1,2}L(-\d+)?|_[LMS]-\d+', key, re.IGNORECASE):
                return "Ship Items"

            # Remaining item_Name_ / item_Desc_ keys are FPS gear
            if key_lower.startswith("item_name_") or key_lower.startswith("item_desc_"):
                return "Gear"

        # Mining gadgets are FPS/hand-held gear
        if key_lower.startswith("item_mining_gadget_"):
            return "Gear"

        # Mining modules/lasers (item_Mining_* — not item_Name/item_Desc prefix)
        if key_lower.startswith("item_mining_"):
            return "Ship Items"

        # Commodity items
        if key_lower.startswith("items_commodities_"):
            return "Commodities"

        # Journal entries
        if "journal" in key_lower:
            return "Journal"

        # Mission-related keys — prefixes derived from mission_rewards_enhancements.ini,
        # contracts.ini, and DataForge pu_missions entities.
        # Compared case-insensitively.  Prefer bare prefixes (no trailing _)
        # where safe, to catch variant spellings (e.g. bitzeros vs bitzeroes).
        mission_prefixes = {
            "adagio_", "assassin", "basesweep_",
            "bbt_", "bhg_", "bitzero", "blackbox", "blacjac", "blockaderunner",
            "bounty_",
            "cdf_", "cfp", "civilian_", "claimsweep_", "cleanair_",
            "clovis_", "combatassist_", "commarray", "confirmkill_",
            "constantine_", "contract", "covalex", "criminal_",
            "crusader_", "crus_",
            "dataheis", "deadsaints_", "deploypiggyback_", "deployprobe_",
            "destroyblade_", "destroydebris_", "destroyitem_",
            "destroyprobe", "destroystash_", "distraction",
            "dusters_",
            "eckhart", "ecn_", "escort_",
            "fffinale_", "firesale_", "forcedepletion",
            "foxwell_", "fps_bounty", "ftl_",
            "genlocal_", "gobling_", "groupbounty_",
            "hack_", "haulcargo_", "hdactivist_", "headhunters_",
            "hexpenetrator_", "hh_", "highpoint_", "hockcrow_", "hockrow_",
            "hurston_",
            "intersec_",
            "jt_",
            "kaboos_", "kareahsweep_", "killship_",
            "lingfamily_", "localdelivery_", "locationrush_",
            "me_blackbox", "me_bounty", "me_planetcollect",
            "meet_", "mg_", "mgclovus_", "miningclaim",
            "mission", "mtps_", "murderspree_",
            "ninetails_", "northrock_", "ntlockdown_",
            "outpost_repair", "outlawsweep_",
            "p_showdown", "p_protect", "planetcollect_",
            "preventdata_", "prisonerbreak_", "protlife_",
            "rain_", "recovery_", "recoverstash_", "recoverstolen_",
            "redwind_", "repairoxygenkiosk_", "retakelocation_",
            "retrieveconsignment_", "retrievedatapad_",
            "roughready_", "ruto_",
            "scramblerace_", "searchbody", "searchcrew_",
            "sectorsweep_", "securitypatrol_", "servicebeacon_",
            "shubin_", "singleidrisfight_", "spacecargo_",
            "spacecollect", "spacesteal_", "stealevidence_", "stealitem_",
            "tarpits_", "test_title_", "thecollector_",
            "timesensitive_", "tutorial",
            "udm_", "uwc_",
            "vaughn_", "vendingmachine_",
            "wantedlevel", "wstr_", "xenothreat_",
        }
        if any(key_lower.startswith(p) for p in mission_prefixes):
            return "Missions"

        return "Other"


def test_category_extraction():
    """Test category extraction for edge cases."""
    # Ship components with underscore between Name and component code
    assert StringEntry.extract_category("item_Name_QDRV_RSI_S02_Hemera") == "Ship Items"
    assert StringEntry.extract_category("item_Desc_QDRV_RSI_S02_Hemera") == "Ship Items"

    # Ship components with lowercase item_name (from Data.p4k extraction)
    assert StringEntry.extract_category("item_nameQDRV_RSI_S02_Hemera_SCItem") == "Ship Items"
    assert StringEntry.extract_category("item_descqdrv_rsi_s02_hemera_scitem") == "Ship Items"

    # Ship weapons with XL size designator
    assert StringEntry.extract_category("item_Name_XL-1_something") == "Ship Items"
    assert StringEntry.extract_category("item_Name_XXL_something") == "Ship Items"

    # Regular ship components (original patterns)
    assert StringEntry.extract_category("item_NameSHLD_Aspirum") == "Ship Items"
    assert StringEntry.extract_category("item_NamePOWR_TR1") == "Ship Items"
    assert StringEntry.extract_category("item_Name_Turret_S1") == "Ship Items"

    # FPS weapons (should still work)
    assert StringEntry.extract_category("item_Name_rifle") == "Gear"

    print("[PASS] All category extraction tests passed!")
