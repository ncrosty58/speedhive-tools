import gzip
import json
import tempfile
from pathlib import Path

from speedhive.ndjson import open_ndjson
from speedhive.utils.lap_analysis import compute_laps_and_enriched, parse_track_record_text


def test_open_ndjson_plain():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ndjson") as f:
        f.write('{"a": 1}\n{"a": 2}\n')
        f.flush()
        path = Path(f.name)
    rows = list(open_ndjson(path))
    assert rows == [{"a": 1}, {"a": 2}]
    Path(path).unlink()


def test_open_ndjson_gzipped():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ndjson.gz") as f:
        with gzip.open(f.name, "wt") as gz:
            gz.write('{"x": 10}\n{"x": 20}\n')
        path = Path(f.name)
    rows = list(open_ndjson(path))
    assert rows == [{"x": 10}, {"x": 20}]
    Path(path).unlink()


def test_compute_laps_and_enriched(tmp_path):
    org = 9999
    dump_dir = tmp_path / "output"
    org_dir = dump_dir / str(org)
    org_dir.mkdir(parents=True)

    # Create sessions.ndjson.gz
    sessions = [
        {
            "session_id": 1,
            "raw": {
                "id": 1,
                "results": [{"position": 1, "name": "Driver A"}],
            },
        }
    ]
    with gzip.open(org_dir / "sessions.ndjson.gz", "wt") as f:
        for s in sessions:
            f.write(json.dumps(s) + "\n")

    # Create laps.ndjson.gz – flat format
    laps = [
        {
            "session_id": 1,
            "rows": [
                {"position": 1, "lapTime": "1:17.8"},
                {"position": 1, "lapTime": "1:18.0"},
            ],
        }
    ]
    with gzip.open(org_dir / "laps.ndjson.gz", "wt") as f:
        for lap_entry in laps:
            f.write(json.dumps(lap_entry) + "\n")

    laps_by_driver, enriched = compute_laps_and_enriched(dump_dir, org)
    assert "session1_pos1" in laps_by_driver
    assert len(laps_by_driver["session1_pos1"]) == 2
    assert enriched["session1_pos1"]["name"] == "Driver A"


def test_parse_track_record_text_valid():
    text = "New Track Record (1:17.870) for IT7 by Bob Cross."
    result = parse_track_record_text(text)
    assert result["classification"] == "IT7"
    assert result["lap_time"] == "1:17.870"
    assert result["lap_time_seconds"] == 77.87
    assert result["driver"] == "Bob Cross"


def test_parse_track_record_text_ambiguous():
    text = "New Class Record (1:20.0) for T4 by John (to be confirmed)"
    result = parse_track_record_text(text)
    assert result is None
