import json

from speedhive.workflows.track_records import curation
from speedhive.stores import track_records as store
from speedhive.ndjson import dumps_ndjson, load_ndjson, parse_ndjson_lines, save_ndjson


def test_ndjson_roundtrip(tmp_path):
    doc = {"date": "2026-07-15", "records": [{"a": 1}, {"b": 2}]}
    path = tmp_path / "x.ndjson"
    save_ndjson(path, doc, "records")

    lines = path.read_text().strip().splitlines()
    assert json.loads(lines[0]) == {"_meta": {"date": "2026-07-15"}}
    assert len(lines) == 3

    loaded = load_ndjson(path, {"date": None, "records": []}, "records")
    assert loaded == doc


def test_ndjson_no_meta_line_when_no_meta():
    body = dumps_ndjson({"rejected": [{"x": 1}]}, "rejected")
    lines = body.strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {"x": 1}
    assert parse_ndjson_lines(lines, "rejected") == {"rejected": [{"x": 1}]}


def test_ndjson_missing_file_returns_fresh_default(tmp_path):
    default = {"date": None, "records": []}
    loaded = load_ndjson(tmp_path / "missing.ndjson", default, "records")
    loaded["records"].append({"a": 1})
    # the shared default must not be mutated
    assert default["records"] == []


def test_legacy_json_migrates_to_ndjson(tmp_path):
    """Old pretty-printed curated.json files must transparently become NDJSON."""
    legacy_doc = {"date": "2026-03-01", "records": [
        {"classAbbreviation": "FA", "lapTime": "1:01.861", "driverName": "J. Lewis Cooper, Jr", "marque": "Swift", "date": "2009-05-10"},
        {"classAbbreviation": "GT1", "lapTime": "1:05.5", "driverName": "X", "marque": None, "date": "2019-06-01"},
    ]}
    p = curation.paths_for_org(tmp_path, 999)
    p["dir"].mkdir(parents=True)
    (p["dir"] / "curated.json").write_text(json.dumps(legacy_doc))

    loaded = curation.load_curated(p)
    assert loaded["date"] == "2026-03-01"
    assert len(loaded["records"]) == 2

    # ndjson now exists, legacy renamed aside
    assert p["curated"].exists()
    assert not (p["dir"] / "curated.json").exists()
    assert (p["dir"] / "curated.json.migrated").exists()

    # round-trip through save/load preserves everything
    loaded["date"] = "2026-07-15"
    curation.save_curated(p, loaded)
    again = curation.load_curated(p)
    assert again["date"] == "2026-07-15"
    assert again["records"] == loaded["records"]


def test_track_record_store_helpers_round_trip(tmp_path):
    p = store.paths_for_org(tmp_path, 999)
    assert p["curated"].name == "curated.ndjson"
    assert p["rejected"].name == "rejected.ndjson"

    payload = {"enabled": True, "de_duplicate": False}
    config_path = p["dir"] / "config.json"
    store.save_json(config_path, payload)
    assert store.load_json(config_path, {}) == payload


def test_lap_time_to_seconds_is_strict():
    assert curation.lap_time_to_seconds("1:13.325") == 73.325
    assert curation.lap_time_to_seconds("63.004") == 63.004
    assert curation.lap_time_to_seconds("not-a-time") is None
    assert curation.lap_time_to_seconds(None) is None


def test_normalize_classification_aliases_and_review():
    alias_map = {"aliases": {"spec miata": "SM"}, "always_review": ["F5"]}
    assert curation.normalize_classification("Spec Miata", alias_map) == ("ok", "SM")
    assert curation.normalize_classification("f5", alias_map) == ("ambiguous", None)
    assert curation.normalize_classification("IT7", alias_map) == ("ok", "IT7")


def test_delete_curated_record_normalization(tmp_path):
    p = curation.paths_for_org(tmp_path, 999)
    p["dir"].mkdir(parents=True)

    # 1. Populate curated with a record that has None/""/mixed-case driverName
    curated_doc = {
        "date": "2026-07-16",
        "records": [
            {
                "classAbbreviation": "fa",
                "lapTime": "1:01.861",
                "driverName": None,
                "marque": "Swift",
                "date": "2026-07-16",
                "source": "speedhive"
            },
            {
                "classAbbreviation": "SM",
                "lapTime": "1:22.456",
                "driverName": "John Doe",
                "marque": "Mazda",
                "date": "2026-07-16",
                "source": "speedhive"
            }
        ]
    }
    curation.save_curated(p, curated_doc)

    # Delete first record using identity with empty string "" for driverName (how UI form behaves)
    identity_1 = ("FA", "1:01.861", "", "2026-07-16")
    res_1 = curation.delete_curated_record(p, identity_1)
    assert res_1["found"] is True
    assert res_1["permanent"] is False

    # Delete second record with mismatched case for driverName
    identity_2 = ("sm", "1:22.456", "JOHN DOE", "2026-07-16")
    res_2 = curation.delete_curated_record(p, identity_2)
    assert res_2["found"] is True

    # 2. Check rejected contains both
    rejected = curation.load_rejected(p).get("rejected", [])
    assert len(rejected) == 2

    # 3. Verify make_ldc behaves as expected for checks
    rejected_ldc = {
        curation.make_ldc(r.get("classAbbreviation"), r.get("lapTime"), r.get("driverName"))
        for r in rejected
    }
    raw_ldc_1 = curation.make_ldc("FA", "1:01.861", None)
    assert raw_ldc_1 in rejected_ldc

    raw_ldc_2 = curation.make_ldc("SM", "1:22.456", "john doe")
    assert raw_ldc_2 in rejected_ldc

