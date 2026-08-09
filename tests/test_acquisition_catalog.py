"""Tests for the local, user-reviewed item acquisition catalog."""
from __future__ import annotations

import json

import pytest

from src.utils.acquisition_catalog import (
    apply_acquisition_tag, catalog_to_json, empty_catalog, load_catalog_file,
    set_item_status, validate_catalog,
)


def test_tags_only_item_name_keys_and_is_idempotent():
    catalog = set_item_status(empty_catalog(), "item_Name_rifle_behr_p4ar", "keep")
    tagged = apply_acquisition_tag("P4-AR", "item_Name_rifle_behr_p4ar", catalog)
    assert tagged == "P4-AR <EM4>[Keep]</EM4>"
    assert apply_acquisition_tag(tagged, "item_Name_rifle_behr_p4ar", catalog) == tagged
    assert apply_acquisition_tag("P4-AR description", "item_Desc_rifle_behr_p4ar", catalog) == "P4-AR description"


def test_clear_removes_only_acquisition_tag():
    catalog = set_item_status(empty_catalog(), "item_Name_rifle_behr_p4ar", "shop")
    tagged = apply_acquisition_tag("P4-AR <EM4>[Owned]</EM4>", "item_Name_rifle_behr_p4ar", catalog)
    assert tagged == "P4-AR <EM4>[Owned]</EM4> <EM4>[Shop]</EM4>"
    cleared = set_item_status(catalog, "item_Name_rifle_behr_p4ar", None)
    assert apply_acquisition_tag(tagged, "item_Name_rifle_behr_p4ar", cleared) == "P4-AR <EM4>[Owned]</EM4>"


def test_import_rejects_unknown_status_and_non_item_key(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"schema_version": 1, "items": {"item_Desc_bad": {"status": "shop"}}}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_catalog_file(path)
    with pytest.raises(ValueError):
        validate_catalog({"schema_version": 1, "items": {"item_Name_good": {"status": "maybe"}}})


def test_catalog_json_round_trips():
    catalog = set_item_status(empty_catalog(), "item_Name_rifle_behr_p4ar", "limited")
    assert validate_catalog(json.loads(catalog_to_json(catalog))) == catalog


def test_unlisted_requires_catalog_that_declares_complete_shop_coverage():
    catalog = empty_catalog()
    assert apply_acquisition_tag("P4-AR", "item_Name_rifle_behr_p4ar", catalog) == "P4-AR"
    catalog["shop_catalog_complete"] = True
    assert apply_acquisition_tag("P4-AR", "item_Name_rifle_behr_p4ar", catalog) == "P4-AR <EM4>[Unlisted]</EM4>"
    reviewed = set_item_status(catalog, "item_Name_rifle_behr_p4ar", "keep")
    assert apply_acquisition_tag("P4-AR", "item_Name_rifle_behr_p4ar", reviewed) == "P4-AR <EM4>[Keep]</EM4>"


def test_bundled_display_name_record_can_tag_without_guessing_a_key():
    catalog = empty_catalog()
    catalog["names"] = {"p4-ar": {"status": "shop", "source": "Finder"}}
    assert apply_acquisition_tag("P4-AR", "item_Name_rifle_behr_p4ar", catalog) == "P4-AR <EM4>[Shop]</EM4>"
