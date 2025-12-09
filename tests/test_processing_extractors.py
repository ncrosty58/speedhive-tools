import gzip
import json
import sqlite3
import sys
from pathlib import Path

# Ensure repo root is on sys.path so tests can import `examples` package
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))


def _write_gz_lines(path: Path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf8") as f:
        for l in lines:
            f.write(json.dumps(l))
            f.write("\n")


def test_extract_laps_to_csv(tmp_path):
    # prepare a minimal laps.ndjson.gz
    in_dir = tmp_path / "org"
    in_dir.mkdir()
    laps_path = in_dir / "laps.ndjson.gz"
    sample = {
        "event_id": 1,
        "session_id": 10,
        "rows": [
            {"competitorId": "C1", "lapNumber": 1, "lapTime": "00:01:23.456", "position": 1}
        ],
    }
    _write_gz_lines(laps_path, [sample])

    # import function and run
    from speedhive_tools.processors.extract_laps_to_csv import extract

    out_csv = tmp_path / "out.csv"
    n = extract(laps_path, out_csv)
    assert n == 1
    assert out_csv.exists()
    content = out_csv.read_text(encoding="utf8")
    assert "competitor_id" in content
    assert "C1" in content


def test_extract_sessions_to_csv(tmp_path):
    in_dir = tmp_path / "org"
    in_dir.mkdir()
    sessions_path = in_dir / "sessions.ndjson.gz"
    sample = {"event_id": 1, "sessions": [{"id": 100, "name": "Practice", "startTime": "2025-01-01T10:00:00Z"}]}
    _write_gz_lines(sessions_path, [sample])

    from speedhive_tools.processors.extract_sessions_to_csv import extract

    out_csv = tmp_path / "sessions.csv"
    n = extract(sessions_path, out_csv)
    assert n == 1
    assert out_csv.exists()
    txt = out_csv.read_text(encoding="utf8")
    assert "Practice" in txt


def test_extract_announcements_to_csv_and_sqlite(tmp_path):
    in_dir = tmp_path / "org"
    in_dir.mkdir()
    ann_path = in_dir / "announcements.ndjson.gz"
    sample = {"event_id": 1, "session_id": 10, "rows": [{"text": "Race starts", "time": "2025-01-01T11:00:00Z"}]}
    _write_gz_lines(ann_path, [sample])

    from speedhive_tools.processors.extract_announcements_to_csv import extract
    out_csv = tmp_path / "ann.csv"
    n = extract(ann_path, out_csv)
    assert n == 1
    assert out_csv.exists()
    assert "Race starts" in out_csv.read_text(encoding="utf8")

    # prepare a minimal laps file for sqlite test
    laps_path = in_dir / "laps.ndjson.gz"
    laps_sample = {"event_id": 1, "session_id": 10, "rows": [{"competitorId": "C1", "lapNumber": 1, "lapTime": "00:01:00"}]}
    _write_gz_lines(laps_path, [laps_sample])

    from speedhive_tools.processors.ndjson_to_sqlite import ingest_laps
    db_path = tmp_path / "dump.db"
    inserted = ingest_laps(laps_path, db_path)
    assert inserted == 1
    # check DB
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM laps")
    cnt = cur.fetchone()[0]
    conn.close()
    assert cnt == 1
