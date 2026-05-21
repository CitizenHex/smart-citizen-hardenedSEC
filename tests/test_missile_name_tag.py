"""Tests for `_missile_name_tag` in scripts/generate_enhancements_ini.

Covers the bomb-detection path added in 1.4.1: bombs author
``AttachDef Type="Bomb"`` (and an ``SCItemBombParams`` element) but
no ``trackingSignalType``. Pre-fix the tagger fell through to empty
ordinance and rendered ``[S3]`` — the size-only output the user
reported as uninformative on the issue thread. Post-fix the tagger
detects the bomb marker, resolves ordinance to ``"Bomb"`` (which the
DEFAULT_MISSILE_ORDINANCE_MAPPING translates to ``B``), and renders
``[B-S3]`` under the default config.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from lxml import etree as ET

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def gen_module():
    repo_root = Path(__file__).resolve().parent.parent
    script_path = repo_root / "scripts" / "generate_enhancements_ini.py"
    spec = importlib.util.spec_from_file_location(
        "generate_enhancements_ini_missile_test", script_path,
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestMissileBombDetection:
    """1.4.1 regression: bombs receive a ``[B-Sx]`` ordinance tag rather
    than the pre-fix bare-size ``[Sx]``."""

    @pytest.mark.regression
    def test_bomb_via_attachdef_type_yields_B_tag(self, gen_module):
        """``AttachDef Type="Bomb"`` is the strongest signal — covers
        every bomb in the live cache (bomb_s03_fski_thunderball etc.).
        Default missile config med-style maps ``Bomb`` → ``B``, with
        sn-style size → ``S3``."""
        bomb_xml = ET.fromstring(
            '<EntityClassDefinition>'
            '  <SAttachableComponentParams>'
            '    <AttachDef Type="Bomb" Size="3"/>'
            '  </SAttachableComponentParams>'
            '  <SCItemBombParams/>'
            '</EntityClassDefinition>'
        )
        desc = "Manufacturer: Firestorm Kinetics\\nSize: 3\\n"
        assert gen_module._missile_name_tag(desc, bomb_xml) == "[B-S3]"

    @pytest.mark.regression
    def test_bomb_via_scitembombparams_alone(self, gen_module):
        """If a future entity ships only the params element (no
        AttachDef Type marker), the detection still fires off the
        params element. Defense in depth against CIG ambiguity."""
        bomb_xml = ET.fromstring(
            '<EntityClassDefinition>'
            '  <Components>'
            '    <SAttachableComponentParams>'
            '      <AttachDef Size="5"/>'
            '    </SAttachableComponentParams>'
            '    <SCItemBombParams/>'
            '  </Components>'
            '</EntityClassDefinition>'
        )
        desc = "Size: 5\\n"
        assert gen_module._missile_name_tag(desc, bomb_xml) == "[B-S5]"

    def test_guided_missile_unchanged(self, gen_module):
        """Regression guard: guided-missile path still picks up
        ``trackingSignalType`` and renders the seeker abbreviation,
        not a bomb tag."""
        ir_xml = ET.fromstring(
            '<EntityClassDefinition>'
            '  <SAttachableComponentParams>'
            '    <AttachDef Type="Missile" Size="1"/>'
            '  </SAttachableComponentParams>'
            '  <targetingParams trackingSignalType="Infrared"/>'
            '</EntityClassDefinition>'
        )
        desc = "Size: 1\\nTracking Signal: Infrared\\n"
        assert gen_module._missile_name_tag(desc, ir_xml) == "[IR-S1]"

    def test_seekerless_missile_still_drops_to_size(self, gen_module):
        """A Type="Missile" entity with no trackingSignalType and no
        bomb marker still renders as ``[Sx]`` — the empty-ordinance
        drop is intact for the residual non-bomb non-guided cases."""
        unknown_xml = ET.fromstring(
            '<EntityClassDefinition>'
            '  <SAttachableComponentParams>'
            '    <AttachDef Type="Missile" Size="2"/>'
            '  </SAttachableComponentParams>'
            '</EntityClassDefinition>'
        )
        desc = "Size: 2\\n"
        assert gen_module._missile_name_tag(desc, unknown_xml) == "[S2]"
