"""Security boundary tests for bundled native P4K extraction tools."""
import shutil
from pathlib import Path

import pytest

from src.utils.pak_extractor import _verify_bundled_tools


pytestmark = pytest.mark.unit


def _tool_dir() -> Path:
    return Path(__file__).parents[1] / "assets" / "unp4k"


def test_reviewed_bundled_tools_match_frozen_hashes():
    _verify_bundled_tools(_tool_dir(), include_unforge=True)


def test_modified_native_component_is_rejected(tmp_path):
    copied = tmp_path / "unp4k"
    shutil.copytree(_tool_dir(), copied)
    with (copied / "unp4k.exe").open("ab") as handle:
        handle.write(b"tampered")
    with pytest.raises(RuntimeError, match="was modified"):
        _verify_bundled_tools(copied, include_unforge=True)
