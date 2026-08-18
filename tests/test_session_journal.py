from pathlib import Path

from src.utils.session_journal import load_journal_events


def test_extracts_explicit_activity_without_engine_noise(tmp_path):
    log = tmp_path / "game.log"
    log.write_text(
        "<2026-08-17T22:40:04.363Z> [Notice] <EndMission> Ending mission for player. MissionId[abc] Player[TestPilot] CompletionType[Complete]\n"
        "<2026-08-17T22:40:04.363Z> [Notice] <SHUDEvent_OnNotification> Added notification \"Contract Complete: Patrol Duty <EM4>[200 Rep]</EM4>: \"\n"
        "<2026-08-17T22:40:05.315Z> [Notice] <SHUDEvent_OnNotification> Added notification \"Received Blueprint: Testudo Legs <EM4>[Unlisted]</EM4>: \"\n"
        "<2026-08-17T22:40:06.315Z> [Notice] <SHUDEvent_OnNotification> Added notification \"Hangar Request Completed: \"\n"
        "<2026-08-17T22:40:07.315Z> [Notice] <SHUDEvent_OnNotification> Added notification \"You have joined channel 'RSI Perseus : TestPilot'.\n"
        "<2026-08-17T22:40:08.315Z> [Notice] <VehicleListQuery> Fetching vehicle list for player 123 completed. Retrieved 38 entitlements out of 38 vehicules.\n"
        "<2026-08-17T22:40:09.315Z> [Notice] <StatObjLoad> cargo_refinery_asset.cgf\n",
        encoding="utf-8",
    )
    events = load_journal_events(log)
    assert {event["kind"] for event in events} == {"contract_completed", "blueprint_received", "hangar_request", "ship_channel", "vehicle_entitlements"}
    assert all("cargo_refinery" not in event["summary"] for event in events)
