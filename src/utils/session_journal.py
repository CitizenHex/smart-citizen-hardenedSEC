"""Read-only personal activity journal parsed from Star Citizen ``Game.log``.

Only explicit gameplay notifications are retained.  Engine asset loads, cargo
platform internals, and unverified combat/economy strings are deliberately not
treated as player activity.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_TIME = re.compile(r"<(?P<time>[^>]+)>")
_MISSION_END = re.compile(
    r"<EndMission>.*?MissionId\[(?P<id>[^]]+)\] Player\[(?P<player>[^]]+)\].*?CompletionType\[Complete\]"
)
_CONTRACT = re.compile(r"Contract (?P<state>Accepted|Complete):\s*(?P<title>.+?)(?: <EM4>|: \")")
_BLUEPRINT = re.compile(r"Received Blueprint:\s*(?P<name>.+?)(?: <EM4>|: \")")
_JURISDICTION = re.compile(r"(?:Entered|Exited|Entering|Leaving) (?:[\w& -]+(?:Jurisdiction|Space|Property|Zone))(?: - [^:\"]+)?")
_SHIP_CHANNEL = re.compile(r"You have (?P<action>joined|left) (?:the )?channel '(?P<ship>[^']+)'")
_PARTY_INVITE = re.compile(r'Added notification "(?P<player>[^\r\n"]+)\r?\n.*?Party Invite Received')
_PARTY_JOIN = re.compile(r"(?P<player>[^\r\n]+) has joined the channel '(?P<channel>[^']+)'\.")
_VEHICLE_LIST = re.compile(r"VehicleListQuery> Fetching vehicle list for player (?P<player>\d+) completed\. Retrieved (?P<count>\d+) entitlements")


def _event(timestamp: str, kind: str, summary: str, **details: str) -> dict:
    return {"timestamp": timestamp, "kind": kind, "summary": summary, "details": details}


def load_journal_events(log_path: Path) -> list[dict]:
    """Return deduplicated, explicitly evidenced personal activity events."""
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    events: list[dict] = []
    for index, line in enumerate(lines):
        time_match = _TIME.search(line)
        if not time_match:
            continue
        timestamp = time_match["time"]
        # Some HUD messages put their readable text on the following line.
        # One following line is enough and avoids one notification being
        # accidentally attributed to the notification before it.
        nearby = "\n".join(lines[index:index + 2])

        mission = _MISSION_END.search(line)
        if mission:
            title_match = _CONTRACT.search(nearby)
            events.append(_event(timestamp, "contract_completed", title_match["title"].strip() if title_match else "Completed contract", mission_id=mission["id"], player=mission["player"]))
            continue

        if "<SHUDEvent_OnNotification> Added notification" not in line:
            continue

        contract = _CONTRACT.search(nearby)
        if contract:
            state = contract["state"].lower()
            # Completion gets its player and mission ID from the durable
            # EndMission event above; do not add a second, weaker record.
            if state == "complete":
                continue
            events.append(_event(timestamp, f"contract_{state}", f"Contract {state}: {contract['title'].strip()}"))
            continue
        blueprint = _BLUEPRINT.search(nearby)
        if blueprint:
            events.append(_event(timestamp, "blueprint_received", f"Received blueprint: {blueprint['name'].strip()}"))
            continue
        if "Hangar Request Completed" in nearby:
            events.append(_event(timestamp, "hangar_request", "Hangar request completed"))
            continue
        ship_channel = _SHIP_CHANNEL.search(nearby)
        if ship_channel:
            events.append(_event(timestamp, "ship_channel", f"{ship_channel['action'].title()} ship channel: {ship_channel['ship']}", ship=ship_channel["ship"]))
            continue
        party_invite = _PARTY_INVITE.search(nearby)
        if party_invite:
            events.append(_event(timestamp, "party_invite", f"Party invitation observed from: {party_invite['player'].strip()}", player=party_invite["player"].strip()))
            continue
        party_join = _PARTY_JOIN.search(nearby)
        if party_join:
            events.append(_event(timestamp, "party_member_observed", f"Party member observed: {party_join['player'].strip()}", player=party_join["player"].strip(), channel=party_join["channel"]))
            continue
        jurisdiction = _JURISDICTION.search(nearby)
        if jurisdiction:
            events.append(_event(timestamp, "location_state", jurisdiction.group(0)))

    # Vehicle queries are useful state snapshots, but collapse duplicate UI
    # refreshes at the same timestamp to avoid a noisy journal.
    for line in lines:
        match = _VEHICLE_LIST.search(line)
        time_match = _TIME.search(line)
        if match and time_match:
            events.append(_event(time_match["time"], "vehicle_entitlements", f"Vehicle list loaded: {match['count']} entitlements", player_id=match["player"], count=match["count"]))

    unique = {(event["timestamp"], event["kind"], event["summary"]): event for event in events}
    return sorted(unique.values(), key=lambda event: event["timestamp"], reverse=True)


def journal_path(data_dir: Path) -> Path:
    return data_dir / "journal" / "activity.json"


def save_journal_events(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 2, "events": events}, indent=2) + "\n", encoding="utf-8")
