from src.utils.acquisition_catalog import apply_acquisition_tag
from src.utils.finder_catalog import parse_finder_search
from src.utils.loot_tag_categories import (
    CATEGORY_ARMOR, CATEGORY_CLOTHING, CATEGORY_FOOD, CATEGORY_MEDICAL,
    CATEGORY_OTHER, default_category_settings, enabled_categories,
)


def test_everyday_loot_groups_are_off_by_default():
    defaults = default_category_settings()
    assert not defaults[CATEGORY_CLOTHING]
    assert not defaults[CATEGORY_FOOD]
    assert not defaults[CATEGORY_MEDICAL]
    assert defaults[CATEGORY_ARMOR]


def test_disabled_group_strips_existing_tag_without_losing_catalog_match():
    catalog = {
        "schema_version": 1, "items": {}, "shop_catalog_complete": False,
        "names": {"simple water": {"status": "shop"}},
    }
    assert apply_acquisition_tag(
        "Simple Water", "item_name_water", catalog, enabled_categories(default_category_settings())
    ) == "Simple Water"
    enabled = set(enabled_categories(default_category_settings()))
    enabled.add(CATEGORY_FOOD)
    assert apply_acquisition_tag("Simple Water", "item_name_water", catalog, enabled) == "Simple Water <EM4>[Shop]</EM4>"


def test_finder_refresh_keeps_manual_tags_and_rejects_ambiguous_name():
    existing = {
        "schema_version": 1,
        "items": {"item_name_special": {"status": "keep"}},
        "names": {},
        "shop_catalog_complete": False,
    }
    catalog, count = parse_finder_search([
        {"name": "Shop Item", "Sold": 1},
        {"name": "Unlisted Item", "Sold": 0},
        {"name": "Ambiguous", "Sold": 0},
        {"name": "Ambiguous", "Sold": 1},
    ], existing)
    assert count == 2
    assert catalog["items"]["item_name_special"]["status"] == "keep"
    assert catalog["names"]["shop item"]["status"] == "shop"
    assert "ambiguous" not in catalog["names"]


def test_finder_refresh_accepts_known_transport_wrappers():
    existing = {"schema_version": 1, "items": {}, "names": {}, "shop_catalog_complete": False}
    rows = [{"name": "Wrapped Shop Item", "Sold": 1}]
    for payload in (
        {"data": rows}, {"items": rows}, {"results": rows}, {"d": rows},
        {"d": '[{"name": "Wrapped Shop Item", "Sold": 1}]'},
        {"aaData": rows}, {"response": rows}, {"unexpected_proxy_key": rows},
        '[{"name": "Wrapped Shop Item", "Sold": 1}]',
    ):
        catalog, count = parse_finder_search(payload, existing)
        assert count == 1
        assert catalog["names"]["wrapped shop item"]["status"] == "shop"
