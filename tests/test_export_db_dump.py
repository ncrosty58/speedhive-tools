import json
import pytest
from pathlib import Path
from speedhive.storage import SpeedhiveStorage
from speedhive.exporters.export_db_dump import export_db_dump, main as export_main


def test_export_db_dump(tmp_path):
    db_path = tmp_path / "test_speedhive.db"
    storage = SpeedhiveStorage(db_path)

    org_id = 12345
    events_payload = [
        {"id": 100, "name": "Event 1"},
    ]
    sessions_payload = [
        {"id": 1001, "name": "Session 1"},
    ]
    laps_payload = [
        {"lapNumber": 1, "lapTime": "01:20.500"},
    ]

    with storage.connect() as conn:
        storage.save_events(org_id, events_payload, conn=conn)
        storage.save_event_sessions(100, org_id, sessions_payload, conn=conn)
        storage.save_laps(1001, 100, org_id, laps_payload, conn=conn)

    output_dir = tmp_path / "dump"
    summary = export_db_dump(storage, org_id, output_dir)
    
    assert summary["events_count"] == 1
    assert summary["sessions_count"] == 1
    
    # Check that output files exist
    assert (output_dir / "events.ndjson").exists()
    assert (output_dir / "sessions.ndjson").exists()
    assert (output_dir / "laps.ndjson").exists()
    assert (output_dir / "manifest.json").exists()

    # Verify manifest
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["org_id"] == org_id
    assert manifest["events_count"] == 1

    # Verify CLI main
    output_dir_cli = tmp_path / "dump_cli"
    argv = ["--org", str(org_id), "--db-path", str(db_path), "--output-dir", str(output_dir_cli)]
    assert export_main(argv) == 0
    with open(output_dir_cli / "events.ndjson", "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1
    loaded = json.loads(lines[0])
    assert loaded["event_id"] == 100
    assert "session_id" not in loaded


def test_get_org_status(tmp_path):
    db_path = tmp_path / "test_status.db"
    storage = SpeedhiveStorage(db_path)
    org_id = 9999
    
    status = storage.get_org_status(org_id)
    assert status["org_id"] == org_id
    assert status["events_cached"] == 0
    assert status["last_refresh_at"] is None

    with storage.connect() as conn:
        storage.save_refresh_state(org_id, {
            "events_cached": 10,
            "sessions_cached": 5,
            "last_refresh_at": "2026-06-07T12:00:00Z"
        }, conn=conn)

    status = storage.get_org_status(org_id)
    assert status["events_cached"] == 10
    assert status["sessions_cached"] == 5
    assert status["last_refresh_at"] == "2026-06-07T12:00:00Z"
