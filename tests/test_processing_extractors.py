import gzip
import json
import sqlite3
import sys
from pathlib import Path

# Ensure repo root is on sys.path so tests can import `speedhive` package
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))


def _write_gz_lines(path: Path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf8") as f:
        for l in lines:
            f.write(json.dumps(l))
            f.write("\n")


def test_ndjson_to_sqlite_full_ingest(tmp_path):
    org = 30476
    dump_dir = tmp_path / "output"
    org_dir = dump_dir / str(org)
    org_dir.mkdir(parents=True)

    # 1. Mock events.ndjson.gz
    events_sample = {
        "id": 1,
        "name": "Summer Race",
        "date": "2026-06-06",
        "organization": {"id": 12, "name": "Org 12"},
        "location": "Track A",
        "country": "USA",
    }
    _write_gz_lines(org_dir / "events.ndjson.gz", [events_sample])

    # 2. Mock sessions.ndjson.gz
    sessions_sample = {
        "event_id": 1,
        "sessions": [
            {"id": 10, "name": "Qualifying", "startTime": "2026-06-06T10:00:00Z"}
        ],
    }
    _write_gz_lines(org_dir / "sessions.ndjson.gz", [sessions_sample])

    # 3. Mock laps.ndjson.gz
    laps_sample = {
        "event_id": 1,
        "session_id": 10,
        "rows": [
            {"competitorId": "C1", "lapNumber": 1, "lapTime": "00:01:23.456", "position": 1}
        ],
    }
    _write_gz_lines(org_dir / "laps.ndjson.gz", [laps_sample])

    # 4. Mock announcements.ndjson.gz
    ann_sample = {
        "event_id": 1,
        "session_id": 10,
        "rows": [{"text": "Practice starts", "time": "2026-06-06T10:05:00Z"}]
    }
    _write_gz_lines(org_dir / "announcements.ndjson.gz", [ann_sample])

    # 5. Mock results.ndjson.gz
    results_sample = {
        "event_id": 1,
        "session_id": 10,
        "results": [
            {
                "competitor": {"id": "C1", "name": "John Doe"},
                "position": 1,
                "totalTime": "00:15:30.000",
                "laps": 10,
                "bestLapTime": "00:01:23.456",
            }
        ],
    }
    _write_gz_lines(org_dir / "results.ndjson.gz", [results_sample])

    # Run full ingest using main
    from speedhive.workflows.import_sqlite_dump import main as sqlite_main

    argv = ["--org", str(org), "--dump-dir", str(dump_dir), "--db-path", str(tmp_path / f"laps_{org}.db")]
    exit_code = sqlite_main(argv)
    assert exit_code == 0

    db_path = tmp_path / f"laps_{org}.db"
    assert db_path.exists()

    # Query sqlite db to verify tables and data
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Verify events
    cur.execute("SELECT event_id, name, location FROM analytical_events")
    event_row = cur.fetchone()
    assert event_row == (1, "Summer Race", "Track A")

    # Verify sessions
    cur.execute("SELECT session_id, name FROM analytical_sessions")
    sess_row = cur.fetchone()
    assert sess_row == (10, "Qualifying")

    # Verify laps
    cur.execute("SELECT competitor_id, lap_number, lap_time, position FROM laps")
    lap_row = cur.fetchone()
    assert lap_row == ("C1", 1, "00:01:23.456", 1)

    # Verify announcements
    cur.execute("SELECT text, ts FROM announcements")
    ann_row = cur.fetchone()
    assert ann_row == ("Practice starts", "2026-06-06T10:05:00Z")

    # Verify results
    cur.execute("SELECT competitor_id, name, position, total_time, laps, best_lap_time FROM results")
    res_row = cur.fetchone()
    assert res_row == ("C1", "John Doe", 1, "00:15:30.000", 10, "00:01:23.456")

    conn.close()
