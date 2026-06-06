from pathlib import Path

from speedhive.processing.process_lap_analysis import normalize_name, parse_time_value
from speedhive.processing.ndjson import open_ndjson


def test_normalize_name():
    assert normalize_name("Nathan Crosty") == "nathan crosty"
    assert normalize_name("  N. Crosty!! ") == "n crosty"


def test_parse_time_value():
    assert parse_time_value("1:23.45") == 83.45
    assert parse_time_value("45.67") == 45.67
    assert parse_time_value(12) == 12.0
    assert parse_time_value(None) is None


def test_open_ndjson_tmpfile(tmp_path: Path):
    p = tmp_path / "test.ndjson"
    p.write_text('{"a": 1}\n{"b": 2}\n', encoding="utf8")
    rows = list(open_ndjson(p))
    assert isinstance(rows, list)
    assert rows[0]["a"] == 1
