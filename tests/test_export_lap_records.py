import json
import pytest
from pathlib import Path
from speedhive.storage import SpeedhiveStorage
from speedhive.exporters.export_lap_records import get_lap_records, main as export_main


def test_export_lap_records(tmp_path):
    db_path = tmp_path / "test_speedhive.db"
    storage = SpeedhiveStorage(db_path)

    org_id = 12345
    events_payload = [
        {"id": 100, "name": "Event 1"},
        {"id": 200, "name": "Event 2"},
    ]
    sessions_payload_100 = [
        {"id": 1001, "name": "Session 1"},
    ]
    sessions_payload_200 = [
        {"id": 2001, "name": "Session 2"},
    ]
    laps_payload_1001 = [
        {"lapNumber": 1, "lapTime": "01:20.500"},
    ]
    laps_payload_2001 = [
        {"lapNumber": 1, "lapTime": "01:21.300"},
    ]

    with storage.connect() as conn:
        storage.save_events(org_id, events_payload, conn=conn)
        storage.save_event_sessions(100, org_id, sessions_payload_100, conn=conn)
        storage.save_event_sessions(200, org_id, sessions_payload_200, conn=conn)
        storage.save_laps(1001, 100, org_id, laps_payload_1001, conn=conn)
        storage.save_laps(2001, 200, org_id, laps_payload_2001, conn=conn)

    # 1. Test get_lap_records with all events
    records = list(get_lap_records(storage, org_id))
    assert len(records) == 2
    assert records[0]["event_id"] == 100
    assert records[0]["session_id"] == 1001
    assert records[0]["rows_count"] == 1
    assert records[0]["rows"][0]["lapTime"] == "01:20.500"

    assert records[1]["event_id"] == 200
    assert records[1]["session_id"] == 2001
    assert records[1]["rows_count"] == 1
    assert records[1]["rows"][0]["lapTime"] == "01:21.300"

    # 2. Test get_lap_records with limit (max_events=1)
    records_limited = list(get_lap_records(storage, org_id, max_events=1))
    assert len(records_limited) == 1
    assert records_limited[0]["event_id"] == 100

    # 3. Test CLI main function
    output_file = tmp_path / "output.ndjson"
    argv = ["--org", str(org_id), "--db-path", str(db_path), "--output", str(output_file), "--max-events", "1"]
    exit_code = export_main(argv)
    assert exit_code == 0
    assert output_file.exists()

    with open(output_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1
    loaded = json.loads(lines[0])
    assert loaded["event_id"] == 100
    assert loaded["session_id"] == 1001
