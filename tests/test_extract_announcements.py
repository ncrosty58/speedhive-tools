import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from examples.processing.extract_announcements_to_csv import extract


def make_ndjson_gz(path: Path, lines: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf8") as fh:
        for obj in lines:
            fh.write(json.dumps(obj, ensure_ascii=False))
            fh.write("\n")


def test_extract_announcements_various_shapes(tmp_path: Path):
    in_gz = tmp_path / "ann.ndjson.gz"
    out_csv = tmp_path / "announcements.csv"

    lines = [
        # announcements wrapped under 'announcements' -> 'rows'
        {"event_id": 1, "session_id": 10, "announcements": {"rows": [{"text": "a", "timestamp": "t1"}, {"text": "b", "timestamp": "t2"}]}},
        # direct rows
        {"event_id": 2, "session_id": 20, "rows": [{"text": "c", "timestamp": "t3"}]},
        # single announcement field
        {"event_id": 3, "session_id": 30, "announcement": {"text": "d", "timestamp": "t4"}},
    ]

    make_ndjson_gz(in_gz, lines)

    count = extract(in_gz, out_csv)
    assert count == 4

    # verify CSV exists and has header + 4 lines
    text = out_csv.read_text(encoding="utf8")
    assert "event_id,session_id,ts,text" in text.splitlines()[0]

    # summary file should be created next to CSV
    summary_path = out_csv.parent / "announcements_summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf8"))
    assert summary.get("total") == 4
    assert summary.get("by_event").get("1") == 2
    assert summary.get("by_event").get("2") == 1
    assert summary.get("by_event").get("3") == 1
