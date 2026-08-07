import json

from src.utils.audit_log import AUDIT_FILENAME, audit_path, record


def test_audit_records_are_local_json_lines(tmp_path):
    path = record(tmp_path, "apply_completed", channel="LIVE", count=3)
    assert path == audit_path(tmp_path)
    assert path.name == AUDIT_FILENAME
    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["event"] == "apply_completed"
    assert row["details"] == {"channel": "LIVE", "count": 3}
    assert row["timestamp_utc"].endswith("+00:00")
