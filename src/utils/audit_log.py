"""Local-only, append-only security audit records.

This module deliberately has no network capability.  It records high-value
operations initiated by Smart Citizen so a user can review or export what the
application changed on their own machine.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_FILENAME = "security-audit.jsonl"


def audit_path(logs_dir: Path) -> Path:
    return Path(logs_dir) / AUDIT_FILENAME


def record(logs_dir: Path, event: str, **details: Any) -> Path:
    """Append one JSON Lines record and return the local audit-file path."""
    path = audit_path(logs_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": str(event),
        "details": details,
    }
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return path
