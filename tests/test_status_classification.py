"""Tests for the status classifier in src.parser.ini_parser.

Status semantics:
- "Modified" — user explicitly set a custom_value
- "Enhanced" — value came from Smart Citizen's enhancements pipeline
- "Unmodified" — value is the stock base.ini text, unchanged
- "New" — key only exists in user / enhancements (not in base merged)

The "Enhanced" bucket is the new one — pre-1.3.0 these entries showed
as "Modified" because the source-origin-based path returned "Modified"
for any non-base, non-user source. Distinguishing them lets users see
at a glance what they changed vs. what the app generated.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Match the existing test_core.py convention — bare imports relying on
# tests/conftest.py putting src/ on pythonpath.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from parser.ini_parser import _determine_status_from_source  # noqa: E402

pytestmark = pytest.mark.unit


class TestDetermineStatusFromSource:
    def test_user_source_is_modified(self):
        assert _determine_status_from_source("user", "global") == "Modified"

    def test_enhancements_source_is_enhanced(self):
        """The new branch — enhancements pipeline output gets its own
        bucket so users can distinguish their own edits from generated
        content in the Status column."""
        assert _determine_status_from_source("enhancements", "global") == "Enhanced"

    def test_base_source_is_unmodified(self):
        assert _determine_status_from_source("global", "global") == "Unmodified"

    def test_base_source_with_custom_base_name(self):
        """``base_source`` is parameterised — confirm the rule is "source
        equals base_source", not "source is literally global"."""
        assert _determine_status_from_source("custom_base", "custom_base") == "Unmodified"

    def test_other_higher_priority_source_is_modified(self):
        """Generic fallback: any non-base, non-user, non-enhancements
        source still returns Modified. Rare post-1.0 (the four URL-based
        sources retired in 0.7.0) but kept as the safe default for any
        future custom source name."""
        assert _determine_status_from_source("contracts", "global") == "Modified"
        assert _determine_status_from_source("ships", "global") == "Modified"

    def test_enhancements_takes_precedence_over_modified_fallback(self):
        """Regression guard: if the function order changes so the generic
        Modified-fallback runs before the enhancements check, this
        catches it."""
        result = _determine_status_from_source("enhancements", "global")
        assert result == "Enhanced", (
            "enhancements check must run before the catch-all 'Modified' "
            "branch, otherwise the new bucket silently empties out"
        )
