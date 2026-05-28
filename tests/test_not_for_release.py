"""Unit tests for the notForRelease contract filter in scan_contract_generators.

Contracts (and handlers) with notForRelease="1" must be skipped entirely.
Only contracts with notForRelease="0" or no notForRelease attribute should
appear in the output.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def gen_module():
    """Import generate_enhancements_ini.py as a module."""
    repo_root = Path(__file__).resolve().parent.parent
    script_path = repo_root / "scripts" / "generate_enhancements_ini.py"
    spec = importlib.util.spec_from_file_location(
        "generate_enhancements_ini_nfr_test", script_path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# Minimal contract generator XML with two contracts under a Career handler.
# One has notForRelease="0" (should appear); the other has notForRelease="1"
# (should be skipped).
_CONTRACT_GEN_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<ContractGenerator>
  <ContractGeneratorHandler_Career debugName="Stanton_TestHandler" notForRelease="0">
    <CareerContract debugName="Stanton_Released" notForRelease="0" minStanding="">
      <ContractStringParam param="Title" value="@released_title_key" />
      <ContractStringParam param="Description" value="@released_desc_key" />
    </CareerContract>
    <CareerContract debugName="Stanton_NotReleased" notForRelease="1" minStanding="">
      <ContractStringParam param="Title" value="@unreleased_title_key" />
      <ContractStringParam param="Description" value="@unreleased_desc_key" />
    </CareerContract>
  </ContractGeneratorHandler_Career>
</ContractGenerator>
"""

# Handler-level notForRelease: the entire handler is skipped, so neither
# of its child contracts should appear.
_HANDLER_NFR_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<ContractGenerator>
  <ContractGeneratorHandler_Career debugName="Stanton_SkippedHandler" notForRelease="1">
    <CareerContract debugName="Stanton_ChildA" notForRelease="0" minStanding="">
      <ContractStringParam param="Title" value="@child_a_title" />
      <ContractStringParam param="Description" value="@child_a_desc" />
    </CareerContract>
  </ContractGeneratorHandler_Career>
</ContractGenerator>
"""


class TestNotForReleaseContractFilter:
    def test_released_contract_appears(self, gen_module, tmp_path):
        contractgen_dir = tmp_path / "contractgenerators"
        contractgen_dir.mkdir()
        (contractgen_dir / "test_gen.xml").write_text(_CONTRACT_GEN_XML, encoding="utf-8")

        missions, _, _, _ = gen_module.scan_contract_generators(contractgen_dir)

        assert "released_title_key" in missions, (
            "Contract with notForRelease='0' should appear in missions"
        )

    def test_unreleased_contract_skipped(self, gen_module, tmp_path):
        contractgen_dir = tmp_path / "contractgenerators"
        contractgen_dir.mkdir()
        (contractgen_dir / "test_gen.xml").write_text(_CONTRACT_GEN_XML, encoding="utf-8")

        missions, _, _, _ = gen_module.scan_contract_generators(contractgen_dir)

        assert "unreleased_title_key" not in missions, (
            "Contract with notForRelease='1' should be filtered out"
        )

    def test_handler_level_not_for_release_skips_children(self, gen_module, tmp_path):
        contractgen_dir = tmp_path / "contractgenerators"
        contractgen_dir.mkdir()
        (contractgen_dir / "handler_nfr.xml").write_text(_HANDLER_NFR_XML, encoding="utf-8")

        missions, _, _, _ = gen_module.scan_contract_generators(contractgen_dir)

        assert "child_a_title" not in missions, (
            "Children of a notForRelease='1' handler should be skipped"
        )

    def test_only_released_count(self, gen_module, tmp_path):
        """Exactly one contract should survive filtering."""
        contractgen_dir = tmp_path / "contractgenerators"
        contractgen_dir.mkdir()
        (contractgen_dir / "test_gen.xml").write_text(_CONTRACT_GEN_XML, encoding="utf-8")

        missions, _, _, _ = gen_module.scan_contract_generators(contractgen_dir)

        assert len(missions) == 1
