import json

import pytest

from speedhive.processing.process_lap_analysis import parse_track_record_text


def test_extract_track_records_cli_outputs_ndjson(tmp_path, monkeypatch):
    """extract-track-records emits NDJSON: a _meta line, then one record per line."""
    from speedhive.processing import process_track_records as ptr

    db = tmp_path / "cache.db"
    db.write_text("")  # only the exists() check touches it once extraction is stubbed
    monkeypatch.setattr(
        ptr,
        "extract_records_from_storage",
        lambda org, db_path, classification=None: [
            {"classification": "IT7", "lap_time": "1:17.870", "driver": "Bob Cross"},
            {"classification": "SM", "lap_time": "1:14.203", "driver": "Jane Doe"},
        ],
    )

    out = tmp_path / "records.ndjson"
    rc = ptr.main(["--org", "30476", "--db-path", str(db), "--output", str(out)])
    assert rc == 0

    lines = out.read_text().strip().splitlines()
    assert len(lines) == 3
    meta = json.loads(lines[0])["_meta"]
    assert meta["org_id"] == 30476
    assert meta["generated_at"]
    assert json.loads(lines[1])["classification"] == "IT7"
    assert json.loads(lines[2])["driver"] == "Jane Doe"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("New Track Record (1:17.870) for IT7 by Bob Cross.",
         {"classification": "IT7", "lap_time": "1:17.870", "driver": "Bob Cross"}),
        ("New Class Record (1:17.129) for IT7 by [2] Kevin Fandozzi in Chevrolet C5 Corvette",
         {"classification": "IT7", "lap_time": "1:17.129", "driver": "Kevin Fandozzi", "marque": "Chevrolet C5 Corvette"}),
        ("This is not relevant text", None),
        ("New Track Record (63.004) for T4 by Jane Doe", {"classification": "T4", "lap_time": "63.004", "driver": "Jane Doe"}),
        ("New Track Record (1:03.004) for P2 by Alejandro Dellatorre in 1984 SRF Enterprises.",
         {"classification": "P2", "lap_time": "1:03.004", "driver": "Alejandro Dellatorre", "marque": "1984 SRF Enterprises"}),
    ],
)
def test_parse_track_record_text(text, expected):
    parsed = parse_track_record_text(text)
    if expected is None:
        assert parsed is None
        return
    assert parsed is not None
    for k, v in expected.items():
        assert parsed.get(k) == v
    # lap_time_seconds should parse to a float
    assert isinstance(parsed.get("lap_time_seconds"), (float, type(None)))
