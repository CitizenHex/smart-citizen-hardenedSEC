"""Tests for src.models.string_model.is_ship_name_key (#329).

Ship description entries share the "Ships" category with ship name entries,
but only the name entry's custom_value feeds the in-game ASOP favorite-prefix
/ sort-order mechanism (ship_sort_prefix.py) -- a description being marked
"favorite" edits text nothing in-game reads sorted or starred. This locks the
key-pattern distinction the favorite/sort UI (string_table_model.py,
entry_filter.py) relies on to keep description rows out of that mechanism.
"""
import pytest

from src.models.string_model import is_ship_name_key

pytestmark = pytest.mark.unit


def test_bare_vehicle_name_key_is_a_name():
    assert is_ship_name_key("vehicle_NameANVL_Carrack") is True


def test_bare_vehicle_desc_key_is_not_a_name():
    assert is_ship_name_key("vehicle_DescANVL_Carrack") is False


def test_case_insensitive():
    assert is_ship_name_key("VEHICLE_NAMEanvl_carrack") is True
    assert is_ship_name_key("VEHICLE_DESCanvl_carrack") is False


def test_wikelo_vehiclename_suffix_is_a_name():
    assert is_ship_name_key("TheCollector_ShipMod_01_VehicleName") is True


def test_wikelo_vehiclenameshort_suffix_is_a_name():
    assert is_ship_name_key("TheCollector_ShipMod_01_VehicleNameShort") is True


def test_wikelo_vehicledesc_suffix_is_not_a_name():
    assert is_ship_name_key("TheCollector_ShipMod_01_VehicleDesc") is False


def test_unrelated_key_is_not_a_name():
    assert is_ship_name_key("item_NameSHLD_Aspirum") is False
    assert is_ship_name_key("mission_title_001") is False


def test_empty_or_none_key_is_not_a_name():
    assert is_ship_name_key("") is False
    assert is_ship_name_key(None) is False
