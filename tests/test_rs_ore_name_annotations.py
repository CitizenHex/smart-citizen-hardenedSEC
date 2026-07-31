"""RS ore-name annotation toggle (#331).

Covers the AppSettings round-trip and the generator's ctx-driven gating in
_run_gen_missions. Independent of the "resource_signatures" Mission Detail
Field (the DETAILS-body breakdown) -- see test_mission_detail_fields.py and
test_battaglia_mineable_rs.py for that side. This toggle instead patches the
ore's own mineabletype_primary_<ore> display-name loc key, so it isn't part
of AppSettings.MISSION_FIELD_KEYS / _mdf / _show at all.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from utils.settings import AppSettings  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.regression]


@pytest.fixture(scope="module")
def gen_module():
    repo_root = Path(__file__).resolve().parent.parent
    script_path = repo_root / "scripts" / "generate_enhancements_ini.py"
    spec = importlib.util.spec_from_file_location(
        "generate_enhancements_ini_rs_ore_name_test", script_path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    shared = QSettings(str(tmp_path / "reg.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr(AppSettings, "settings", staticmethod(lambda: shared))


# ── AppSettings contract ─────────────────────────────────────────────────

def test_rs_ore_name_annotations_defaults_off(isolated_settings):
    # Broad-reaching by design (patches the ore's own display name
    # everywhere it's rendered), so it's opt-in like
    # standardize_earnable_ship_names rather than on-by-default like the
    # established MISSION_FIELD_KEYS / MISSION_TITLE_TAG_KEYS toggles.
    assert AppSettings.get_rs_ore_name_annotations() is False


def test_rs_ore_name_annotations_roundtrip(isolated_settings):
    AppSettings.set_rs_ore_name_annotations(True)
    assert AppSettings.get_rs_ore_name_annotations() is True
    AppSettings.set_rs_ore_name_annotations(False)
    assert AppSettings.get_rs_ore_name_annotations() is False


def test_resource_signatures_mission_field_is_independent(isolated_settings):
    """Toggling the ore-name-annotation setting must not affect the
    unrelated "resource_signatures" Mission Detail Field (the DETAILS-body
    breakdown), and vice versa -- they're stored under entirely different
    keys and read by different code paths in the generator."""
    AppSettings.set_rs_ore_name_annotations(True)
    AppSettings.set_mission_detail_field("resource_signatures", False)
    assert AppSettings.get_rs_ore_name_annotations() is True
    assert AppSettings.get_mission_detail_fields()["resource_signatures"] is False


# ── Generator ctx gating ──────────────────────────────────────────────────
#
# _run_gen_missions isn't callable without a large synthetic ctx (see the
# same caveat in test_mission_detail_fields.py), so this replicates its
# exact tail gate line-for-line instead:
#
#     if _rs_ore_name_annotations:
#         out.update(_build_mineable_rs_name_overrides(loc))
#
# where _rs_ore_name_annotations = bool(ctx.get("rs_ore_name_annotations", False)).

def _apply_rs_ore_name_gate(gen_module, out: dict, loc: dict, ctx: dict) -> dict:
    if bool(ctx.get("rs_ore_name_annotations", False)):
        out.update(gen_module._build_mineable_rs_name_overrides(loc))
    return out


def test_ctx_flag_missing_leaves_ore_names_untouched(gen_module):
    loc = {"mineabletype_primary_ice": "Ice"}
    out = _apply_rs_ore_name_gate(gen_module, {"Battaglia_title": "Some Title"}, loc, ctx={})
    assert out == {"Battaglia_title": "Some Title"}


def test_ctx_flag_false_leaves_ore_names_untouched(gen_module):
    loc = {"mineabletype_primary_ice": "Ice"}
    out = _apply_rs_ore_name_gate(gen_module, {}, loc, ctx={"rs_ore_name_annotations": False})
    assert out == {}


def test_ctx_flag_true_applies_the_name_overrides(gen_module):
    loc = {
        "mineabletype_primary_aluminium": "Aluminium",
        "mineabletype_primary_ice": "Ice",
    }
    out = _apply_rs_ore_name_gate(
        gen_module, {"Battaglia_title": "Some Title"}, loc, ctx={"rs_ore_name_annotations": True}
    )
    assert out == {
        "Battaglia_title": "Some Title",
        "mineabletype_primary_aluminium": "Aluminium (RS 4285)",
        "mineabletype_primary_ice": "Ice (RS 4300)",
    }


# ── main()/worker kwarg threading (regression guard against signature drift) ─

def test_main_accepts_rs_ore_name_annotations_kwarg(gen_module):
    """A pure signature-shape check: main() must accept the kwarg by name
    (threaded from AppSettings through EnhancementsGeneratorWorker), so a
    rename on either side fails loudly here instead of silently no-op'ing
    the checkbox in the running app."""
    import inspect
    sig = inspect.signature(gen_module.main)
    assert "rs_ore_name_annotations" in sig.parameters
    assert sig.parameters["rs_ore_name_annotations"].default is False
