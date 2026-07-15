import gzip
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from speedhive.workflows.import_sqlite_dump import ingest_announcements


def make_ndjson_gz(path: Path, lines: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf8") as fh:
        for obj in lines:
            fh.write(json.dumps(obj, ensure_ascii=False))
            fh.write("\n")


def test_extract_announcements_various_shapes(tmp_path: Path):
    in_gz = tmp_path / "ann.ndjson.gz"
    db_path = tmp_path / "test.db"

    lines = [
        # announcements wrapped under 'announcements' -> 'rows'
        {"event_id": 1, "session_id": 10, "announcements": {"rows": [{"text": "a", "timestamp": "t1"}, {"text": "b", "timestamp": "t2"}]}},
        # direct rows
        {"event_id": 2, "session_id": 20, "rows": [{"text": "c", "timestamp": "t3"}]},
        # single announcement field
        {"event_id": 3, "session_id": 30, "announcement": {"text": "d", "timestamp": "t4"}},
    ]

    make_ndjson_gz(in_gz, lines)

    conn = sqlite3.connect(db_path)
    try:
        count = ingest_announcements(in_gz, conn, {}, {})
        conn.commit()
    finally:
        conn.close()

    assert count == 4

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT event_id, session_id, ts, text FROM announcements")
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 4
    assert rows[0] == (1, 10, "t1", "a")
    assert rows[1] == (1, 10, "t2", "b")
    assert rows[2] == (2, 20, "t3", "c")
    assert rows[3] == (3, 30, "t4", "d")
